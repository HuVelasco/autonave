"""
ETABS <-> CFS adapter.

The only module coupled to ETABS (comtypes ``SapModel``).  It:
  1. pulls member demands from analysis results and maps ETABS axes/signs to
     CFS conventions,
  2. builds DesignParams (default: unbraced length = member length),
  3. assembles MemberDesignTasks for the source-agnostic DesignRunner,
  4. writes results back: re-assign optimised sections, flag failing members
     into an ETABS group, and export a tabular report.

ETABS has no native CFS design table, so "results back to ETABS" means the two
things an engineer can act on in the model: the *assigned section* (the
optimisation outcome) and a *failures group* (visible in the UI).

Force/units handling: extraction runs in kip-in units (eUnits=3) so forces are
kips & kip-inch and member length is inches — CFS-native, no conversion.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .design import MemberDesignTask
from .library import SectionLibrary
from .models import (DemandCase, DesignParams, DesignPreferences, MemberForces,
                     MemberResult, SectionGeometry)

_KIP_IN_F = 3  # ETABS eUnits

# ETABS "Shape" strings (Frame Section Property Definitions - Summary table)
SHAPE_COLD_FORMED_C = "Cold Formed C"
SHAPE_COLD_FORMED_Z = "Cold Formed Z"
SHAPE_COLD_FORMED_HAT = "Cold Formed Hat"


@dataclass
class AxisMap:
    """ETABS frame local forces -> CFS SectionForces, with sign factors.

    ETABS local: P (tension +), V2, V3, T, M2, M3.
    CFS:         P (compression +), Mx (major), My (minor), Vx, Vy.

    Defaults assume the C/Z stud's web lies in the ETABS 1-3 plane, so major-axis
    bending = M3 and its companion shear = V2.  Flip a member's orientation by
    editing this map rather than the engine.
    """
    P_sign: float = -1.0     # ETABS tension+ -> CFS compression+
    Mx_from: str = "M3"
    My_from: str = "M2"
    Vy_from: str = "V2"
    Vx_from: str = "V3"
    Mx_sign: float = 1.0
    My_sign: float = 1.0
    Vy_sign: float = 1.0
    Vx_sign: float = 1.0


class EtabsCFSAdapter:
    def __init__(self, SapModel, library: SectionLibrary,
                 prefs: DesignPreferences, demand_combos: Sequence[str],
                 axis_map: Optional[AxisMap] = None,
                 station_mode: str = "all"):
        """
        demand_combos : load-combination names to design for (the CFS design
                        combos — the analogue of ETABS' selected design combos).
        station_mode  : 'all'      -> one demand case per output station
                        'envelope' -> single worst-of-each-component case
        """
        self.sm = SapModel
        self.lib = library
        self.prefs = prefs
        self.combos = list(demand_combos)
        self.ax = axis_map or AxisMap()
        if station_mode not in ("all", "envelope"):
            raise ValueError("station_mode must be 'all' or 'envelope'")
        self.station_mode = station_mode
        self._mat_cache: Dict[str, Tuple[float, float]] = {}

    # ── selection helpers ──────────────────────────────────
    # NOTE: comtypes returns these CSI getters as (out-params…, rc) — the return
    # code is LAST, the out-params come first.  Index accordingly.
    def members_in_group(self, group: str) -> List[str]:
        ret = self.sm.GroupDef.GetAssignments(group, 0, [], [])
        # ret: (NumberItems, ObjectType[], ObjectName[], rc)
        count, types, names = ret[0], list(ret[1]), list(ret[2])
        return [n for tp, n in zip(types, names) if tp == 2]  # 2 = frame object

    def member_section(self, member: str) -> str:
        ret = self.sm.FrameObj.GetSection(member, "", "")
        return ret[0]  # (PropName, SAuto, rc) -> section name at [0]

    # ── type-based CFS detection (no name convention) ──────
    def _display_table(self, table_key: str):
        """Read a DatabaseTables display table robustly across comtypes index
        layouts. Returns (col_names, rows) where rows are lists of str."""
        db = self.sm.DatabaseTables
        ret = db.GetTableForDisplayArray(table_key, [], "All", 0, [], 0, [])
        seqs = [list(x) for x in ret if isinstance(x, (list, tuple))]
        # The column-name list is the one carrying the literal "Name" header.
        cols = next((s for s in seqs if "Name" in s), [])
        others = [s for s in seqs if s is not cols]
        data = max(others, key=len) if others else []
        n = len(cols)
        rows = [data[i * n:(i + 1) * n] for i in range(len(data) // n)] if n else []
        return cols, rows

    def cold_formed_section_names(self, shapes=(SHAPE_COLD_FORMED_C,)):
        """Names of sections whose ETABS Shape is cold-formed — by TYPE, not
        name. Reads 'Frame Section Property Definitions - Summary'."""
        cols, rows = self._display_table(
            "Frame Section Property Definitions - Summary")
        idx = {c: i for i, c in enumerate(cols)}
        if "Shape" not in idx or "Name" not in idx:
            return set()
        want = set(shapes)
        return {r[idx["Name"]] for r in rows if r[idx["Shape"]] in want}

    def cf_members(self, shapes=(SHAPE_COLD_FORMED_C,)) -> List[str]:
        """All frame objects whose assigned section is a cold-formed shape."""
        cf_secs = self.cold_formed_section_names(shapes)
        frames = list(self.sm.FrameObj.GetNameList(0, [])[1])
        return [f for f in frames if self.member_section(f) in cf_secs]

    def material_fy_fu(self, material: str,
                       default=(33.0, 45.0)) -> Tuple[float, float]:
        """(Fy, Fu) in ksi for a material, read from the model. Requires kip-in
        units (design() sets them). Falls back to ``default`` if unavailable."""
        if material in self._mat_cache:
            return self._mat_cache[material]
        fy_fu = default
        for getter in ("GetOSteel_1", "GetOSteel"):
            try:
                r = getattr(self.sm.PropMaterial, getter)(material)
                fy, fu = float(r[0]), float(r[1])  # comtypes: out-params first
                if fy > 0 and fu > 0:
                    fy_fu = (fy, fu)
                    break
            except Exception:
                continue
        self._mat_cache[material] = fy_fu
        return fy_fu

    def section_geometries_from_model(self, shapes=(SHAPE_COLD_FORMED_C,)
                                      ) -> List[SectionGeometry]:
        """Build SectionGeometry list straight from the model's Cold-Formed-C
        table (read in inches), with Fy/Fu taken from each section's assigned
        material — so the library needs no external data.  Caller must be in
        kip-in units (design() handles that).

        NOTE: this reads the lipped-channel table only.  Built-up shapes that
        represent cold-formed studs (e.g. a square tube = two C's face-to-face)
        live in other tables and map to other CFS SectionTypes (Box=7 /
        DoubleCeeStiffened=6); add a reader per shape via ``_SHAPE_TO_CFS``."""
        cols, rows = self._display_table(
            "Frame Section Property Definitions - Cold Formed C")
        idx = {c: i for i, c in enumerate(cols)}
        # GetTableForDisplayArray returns FIELD-KEY names: t3=Web Depth,
        # t2=Flange Width, tw=Thickness, LipDepth=Lip Depth.
        need = ["Name", "t3", "t2", "tw", "Radius", "LipDepth"]
        if any(k not in idx for k in need):
            raise KeyError(f"Cold-Formed-C table missing columns; have {cols}")
        has_mat = "Material" in idx
        out = []
        for r in rows:
            MM = 25.4  # table read in inches -> mm for the helper
            d = float(r[idx["t3"]]) * MM
            b = float(r[idx["t2"]]) * MM
            t = float(r[idx["tw"]]) * MM
            rad = float(r[idx["Radius"]]) * MM
            lip = float(r[idx["LipDepth"]]) * MM
            fy, fu = (self.material_fy_fu(r[idx["Material"]])
                      if has_mat else (33.0, 45.0))
            out.append(SectionGeometry.lipped_c_from_mm(
                r[idx["Name"]], d, b, t, rad, lip, Fy=fy, Fu=fu))
        return out

    def member_length_in(self, member: str) -> float:
        """Member length in inches (units already set to kip-in by caller)."""
        pts = self.sm.FrameObj.GetPoints(member, "", "")   # (Point1, Point2, rc)
        p1, p2 = pts[0], pts[1]
        c1 = self.sm.PointObj.GetCoordCartesian(p1, 0.0, 0.0, 0.0)  # (X,Y,Z,rc)
        c2 = self.sm.PointObj.GetCoordCartesian(p2, 0.0, 0.0, 0.0)
        (x1, y1, z1), (x2, y2, z2) = c1[0:3], c2[0:3]
        return ((x2 - x1) ** 2 + (y2 - y1) ** 2 + (z2 - z1) ** 2) ** 0.5

    # ── results setup ──────────────────────────────────────
    def _select_combos_for_output(self):
        setup = self.sm.Results.Setup
        setup.DeselectAllCasesAndCombosForOutput()
        for c in self.combos:
            setup.SetComboSelectedForOutput(c)

    def _map_forces(self, comp: Dict[str, float]) -> MemberForces:
        a = self.ax
        return MemberForces(
            P=a.P_sign * comp["P"],
            Mx=a.Mx_sign * comp[a.Mx_from],
            My=a.My_sign * comp[a.My_from],
            Vy=a.Vy_sign * comp[a.Vy_from],
            Vx=a.Vx_sign * comp[a.Vx_from],
        )

    def extract_demands(self, member: str) -> List[DemandCase]:
        """Read FrameForce for the selected combos and map to CFS demands."""
        r = self.sm.Results.FrameForce(member, 0, 0, [], [], [], [], [], [], [],
                                       [], [], [], [], [])
        # comtypes layout (rc LAST):
        # r[0]=NumberResults r[1]=Obj r[2]=ObjSta r[3]=Elm r[4]=ElmSta
        # r[5]=LoadCase r[6]=StepType r[7]=StepNum
        # r[8]=P r[9]=V2 r[10]=V3 r[11]=T r[12]=M2 r[13]=M3 r[14]=rc
        n = r[0]
        if not n:
            return []
        obj_sta, combo = r[2], r[5]
        P, V2, V3, T, M2, M3 = r[8], r[9], r[10], r[11], r[12], r[13]

        if self.station_mode == "all":
            out = []
            for i in range(n):
                comp = {"P": P[i], "V2": V2[i], "V3": V3[i],
                        "M2": M2[i], "M3": M3[i]}
                out.append(DemandCase(combo=combo[i],
                                      forces=self._map_forces(comp),
                                      label=combo[i], station=obj_sta[i]))
            return out

        # envelope: worst magnitude of each component across all stations/combos
        comp = {k: max((abs(arr[i]) for i in range(n)), default=0.0)
                for k, arr in {"P": P, "V2": V2, "V3": V3,
                               "M2": M2, "M3": M3}.items()}
        return [DemandCase(combo="ENVELOPE",
                           forces=self._map_forces(comp), label="envelope")]

    # ── task assembly ──────────────────────────────────────
    def build_tasks(self, members: Sequence[str], *,
                    auto_select: bool = True,
                    candidate_subset: Optional[Sequence[str]] = None,
                    params_override: Optional[Callable[[str, float], DesignParams]] = None
                    ) -> List[MemberDesignTask]:
        """
        members          : frame object names to design.
        auto_select      : True  -> optimise over the library's candidate list.
                           False -> just check each member's current section.
        candidate_subset : restrict auto-select to these section names.
        params_override  : callback (member, length_in) -> DesignParams to set
                           unbraced lengths / Cb / Cm per member.  Default:
                           DesignParams.from_length(length).
        """
        tasks: List[MemberDesignTask] = []
        candidates = self.lib.candidate_pairs(candidate_subset) if auto_select else None

        for m in members:
            length = self.member_length_in(m)
            params = (params_override(m, length) if params_override
                      else DesignParams.from_length(length))
            demands = self.extract_demands(m)
            if auto_select:
                tasks.append(MemberDesignTask(m, demands, params,
                                              candidates=candidates))
            else:
                sec = self.member_section(m)
                tasks.append(MemberDesignTask(
                    m, demands, params, fixed_section=(sec, self.lib.token(sec))))
        return tasks

    def design(self, members: Sequence[str], **kw) -> List[MemberResult]:
        """Convenience: set units, select combos, build tasks, run the design."""
        from .design import DesignRunner
        orig_units = self.sm.GetPresentUnits()
        self.sm.SetPresentUnits(_KIP_IN_F)
        try:
            self._select_combos_for_output()
            tasks = self.build_tasks(members, **kw)
        finally:
            self.sm.SetPresentUnits(orig_units)
        return DesignRunner(self.prefs).run(tasks)

    # ── write-back ─────────────────────────────────────────
    def assign_optimized_sections(self, results: Sequence[MemberResult]) -> int:
        """Set each passing member's frame section to the selected section.
        Returns the number of members updated. Requires the model unlocked."""
        self.sm.SetModelIsLocked(False)
        n = 0
        for r in results:
            if r.passed and r.section:
                ret = self.sm.FrameObj.SetSection(r.member_id, r.section, 0)
                rc = ret[-1] if isinstance(ret, (list, tuple)) else ret
                if rc == 0:
                    n += 1
                else:
                    print(f"  [WARN] could not assign {r.section} to "
                          f"{r.member_id} (rc={rc})")
        return n

    def flag_failures(self, results: Sequence[MemberResult],
                      group: str = "CFS_DC_Fail") -> List[str]:
        """Put failing members into an ETABS group (created if needed) so they
        are visible in the UI. Returns the failing member names."""
        self.sm.GroupDef.SetGroup(group)
        failed = [r.member_id for r in results if not r.passed]
        for m in failed:
            self.sm.FrameObj.SetGroupAssign(m, group, False, 0)
        return failed

    @staticmethod
    def to_rows(results: Sequence[MemberResult]) -> List[dict]:
        return [r.as_row() for r in results]

    @classmethod
    def to_csv(cls, results: Sequence[MemberResult], path: str):
        import csv
        rows = cls.to_rows(results)
        if not rows:
            return
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
