"""
Example: design the cold-formed purlins of an open ETABS model with cfs_design.

Run AFTER the model is built and analysed (ETABS open, analysis complete).
Mirrors the ETABS AISC flow: pick combos -> design -> write results back.

EDIT the two marked blocks (CFS version/spec and the section library) for your
machine, then run:  python -m cfs_design.example_etabs_cfs_design
"""
import comtypes.client

from cfs_design import (AxisMap, CFSSpec, DesignPreferences, EtabsCFSAdapter,
                        SectionGeometry, SectionLibrary)

# The project's CF profiles, in mm: [name, depth, flange, thickness, radius, lip]
from Profiles import cfs_profiles_mm


def attach_etabs():
    helper = comtypes.client.CreateObject("ETABSv1.Helper")
    app = helper.GetObject("CSI.ETABS.API.ETABSObject")
    return app.SapModel


def build_library() -> SectionLibrary:
    """In-memory CFS sections from the ETABS CF geometry — no .cfss files.
    Names match the ETABS frame-section names so write-back can re-assign them.
    A653 SQ Grade 33: Fy=33 ksi, Fu=45 ksi. Order = lightest -> heaviest."""
    geoms = [SectionGeometry.lipped_c_from_mm(name, d, b, t, r, lip,
                                              Fy=33.0, Fu=45.0)
             for name, d, b, t, r, lip in cfs_profiles_mm]
    return SectionLibrary.from_geometries(geoms)


def main():
    SapModel = attach_etabs()

    # ── 1. Preferences (CFS version + design spec) ─────────  EDIT
    prefs = DesignPreferences(
        spec=CFSSpec.AISI_2024_USA_ASD,      # ASD spec enum
        progid="RSG.CFS15.Calculation",      # 'RSG.CFS14.Calculation' for CFS14
        unity_limit=1.0,
    )

    # ── 2. Section library: built in-memory from CF geometry (no .cfss) ──
    lib = build_library()

    # ── 3. Demand combinations (the CFS design combos) ─────  EDIT
    # Use the model's ASD strength combos that act on the purlins.
    demand_combos = ["D + L", "SS-02.1", "SS-03.1"]   # example subset

    # ── 4. Adapter + design run ────────────────────────────
    adapter = EtabsCFSAdapter(
        SapModel, lib, prefs,
        demand_combos=demand_combos,
        axis_map=AxisMap(),          # default: Mx=M3, Vy=V2, P sign-flipped
        station_mode="all",          # check every output station
    )

    members = adapter.members_in_group("Purlins_Roof")
    print(f"Designing {len(members)} purlins...")

    results = adapter.design(members, auto_select=True)

    # ── 5. Report + write-back to ETABS ────────────────────
    for r in results:
        print(f"  {r.member_id:>10}  {('PASS' if r.passed else 'FAIL'):4}  "
              f"UC={r.governing_UC}  sec={r.section}  combo={r.governing_combo}")

    n_assigned = adapter.assign_optimized_sections(results)
    failed = adapter.flag_failures(results, group="CFS_DC_Fail")
    adapter.to_csv(results, "cfs_design_results.csv")

    print(f"\nAssigned optimised section to {n_assigned} members.")
    print(f"{len(failed)} members failed -> group 'CFS_DC_Fail'.")
    print("Wrote cfs_design_results.csv")


if __name__ == "__main__":
    main()
