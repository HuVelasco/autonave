"""
Thin wrapper around the RSG CFS COM server (win32com).

This is the ONLY module that talks to CFS.  It owns the license, caches the
currently-loaded section, and converts our dataclasses to/from the COM objects.
It knows nothing about ETABS or load combinations.
"""
from __future__ import annotations

from typing import Optional, Union

from .models import DesignParams, MemberForces, SectionGeometry

# A section to check is either a .cfss file path or a parametric geometry.
SectionToken = Union[str, SectionGeometry]


class CFSError(RuntimeError):
    pass


def _val(x) -> float:
    """CFS returns None for checks that don't apply; treat as 0."""
    return float(x) if x is not None else 0.0


class CFSEngine:
    """
    Manages a single CFS Calculation COM object.

    Use as a context manager so the network license is always released:

        with CFSEngine(prefs) as eng:
            chk = eng.member_check(path, params, forces)
    """

    def __init__(self, progid: str = "RSG.CFS15.Calculation", spec: int = 42):
        self.progid = progid
        self.spec = spec
        self._calc = None
        self._loaded_section: Optional[str] = None
        self._win32com = None  # lazy import so models/design stay COM-free

    # ── lifecycle ──────────────────────────────────────────
    @property
    def calc(self):
        if self._calc is None:
            import win32com.client  # local import: only needed when actually running
            self._win32com = win32com.client
            self._calc = self._win32com.Dispatch(self.progid)
            if not self._calc.HasLicense:
                raise CFSError("CFS license not available")
        return self._calc

    def release(self):
        if self._calc is not None:
            try:
                self._calc.ReleaseLicense()
            except Exception:
                pass
            self._calc = None
            self._loaded_section = None

    def __enter__(self) -> "CFSEngine":
        return self

    def __exit__(self, *exc):
        self.release()

    # ── COM object builders ────────────────────────────────
    def _dispatch(self, suffix: str):
        _ = self.calc  # ensure connected so self._win32com is set
        return self._win32com.Dispatch(self.progid.replace("Calculation", suffix))

    def load_section(self, path: str):
        """Load a .cfss section file (cached — repeated loads are no-ops)."""
        key = ("file", path)
        if key != self._loaded_section:
            self.calc.LoadSection(path)   # touch .calc first so _win32com is set
            self._loaded_section = key

    def define_section(self, geom: SectionGeometry):
        """Build a section in-memory from geometry (no .cfss file).
        Cached by section name. CFS angle fields are radians — leave defaults."""
        key = ("geom", geom.name)
        if key == self._loaded_section:
            return
        sd = self._dispatch("SectionData")          # touches .calc -> _win32com set
        sd.SectionType = int(geom.section_type)
        sd.Depth = geom.depth_in
        sd.Flange = geom.flange_in
        sd.Lip = geom.lip_in
        sd.Thickness = geom.thickness_in
        sd.Radius = geom.radius_in
        sd.Fy = geom.Fy
        sd.Fu = geom.Fu
        self.calc.DefineSection(sd)
        self._loaded_section = key

    def _activate(self, section: "SectionToken"):
        if isinstance(section, SectionGeometry):
            self.define_section(section)
        else:
            self.load_section(section)

    def _member_params(self, p: DesignParams, spec: int):
        mp = self._dispatch("MemberParams")
        mp.Spec = spec
        mp.Lx, mp.Ly, mp.Lt, mp.Lm = p.Lx, p.Ly, p.Lt, p.Lm
        mp.Kx, mp.Ky, mp.Kt = p.Kx, p.Ky, p.Kt
        mp.Cbx, mp.Cby = p.Cbx, p.Cby
        mp.Cmx, mp.Cmy = p.Cmx, p.Cmy
        mp.BracedFlange = int(p.braced_flange)
        mp.R, mp.Kf, mp.Pdelta = p.R, p.Kf, bool(p.pdelta)
        return mp

    def _forces(self, f: MemberForces):
        sf = self._dispatch("SectionForces")
        sf.P, sf.Mx, sf.My = f.P, f.Mx, f.My
        sf.Vx, sf.Vy = f.Vx, f.Vy
        sf.Dx, sf.Dy = f.Dx, f.Dy
        return sf

    # ── the one real operation ─────────────────────────────
    def member_check(self, section: "SectionToken", params: DesignParams,
                     forces: MemberForces, spec: Optional[int] = None):
        """Run one CFS MemberCheck. ``section`` is a .cfss path or a
        SectionGeometry. Returns (UC, PMxMy1, PMxMy2, MxVy)."""
        self._activate(section)
        mp = self._member_params(params, spec if spec is not None else self.spec)
        sf = self._forces(forces)
        chk = self.calc.MemberCheck(mp, sf)
        pmxmy1, pmxmy2, mxvy = _val(chk.PMxMy1), _val(chk.PMxMy2), _val(chk.MxVy)
        uc = max(pmxmy1, pmxmy2, mxvy)
        return uc, pmxmy1, pmxmy2, mxvy
