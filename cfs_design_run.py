"""
Standalone CFS design runner + visualization — pulls everything from the ACTIVE
ETABS model (sections, geometry, material, analysis demands) and shows the
end-to-end design D/C of every cold-formed member present.

Run with ETABS open and the model analysed:
    python cfs_design_run.py

Detection is by section SHAPE ("Cold Formed C"), not by name. Section geometry
and Fy/Fu are read from the model. Demands come from the selected combos.
"""
import sys

import comtypes.client

from cfs_design import (AxisMap, CFSSpec, DesignPreferences, EtabsCFSAdapter)
from cfs_design.etabs_adapter import SHAPE_COLD_FORMED_C

# ───────────────────────── configuration ─────────────────────────
SPEC          = CFSSpec.AISI_2024_USA_ASD   # design spec (your choice)
PROGID        = "RSG.CFS15.Calculation"
COMBO_PREFIX  = "SS"        # strength combos (Model.py uses SS-* for strength)
AUTO_SELECT   = False       # False = check the as-modelled section (D/C of model)
STATION_MODE  = "envelope"  # 'envelope' (fast, 1 demand/member) or 'all'
CF_SHAPES     = (SHAPE_COLD_FORMED_C,)
FAIL_GROUP    = "CFS_DC_Fail"
CSV_PATH      = "cfs_design_results.csv"
PNG_PATH      = "cfs_design_results.png"


def attach_etabs():
    helper = comtypes.client.CreateObject("ETABSv1.Helper")
    return helper.GetObject("CSI.ETABS.API.ETABSObject").SapModel


def pick_combos(SapModel):
    rc = SapModel.RespCombo.GetNameList()
    names = list(rc[1]) if rc[1] else []
    sel = [c for c in names if c.startswith(COMBO_PREFIX)]
    return sel or names   # fall back to all combos if none match the prefix


def visualize(results, png_path):
    try:
        import matplotlib
        import matplotlib.pyplot as plt
    except Exception as e:
        print(f"[viz] matplotlib unavailable ({e}); skipping chart.")
        return
    rows = [r for r in results if r.governing_UC is not None]
    rows.sort(key=lambda r: r.governing_UC, reverse=True)
    ucs = [r.governing_UC for r in rows]
    colors = ["#cc3333" if r.governing_UC > 1.0 else "#2e8b57" for r in rows]

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(14, 6), gridspec_kw={"width_ratios": [3, 1]})

    ax1.bar(range(len(ucs)), ucs, color=colors, width=1.0)
    ax1.axhline(1.0, color="black", lw=1.2, ls="--", label="D/C = 1.0")
    n_fail = sum(u > 1.0 for u in ucs)
    sec = rows[0].section if rows else "-"
    ax1.set_title(f"CFS member D/C — {len(ucs)} members, {n_fail} fail "
                  f"(max {max(ucs):.2f})")
    ax1.set_xlabel("members (sorted by D/C)")
    ax1.set_ylabel("governing D/C ratio")
    ax1.legend(loc="upper right")
    ax1.margins(x=0.01)

    ax2.hist(ucs, bins=20, color="#4477aa", edgecolor="white")
    ax2.axvline(1.0, color="black", lw=1.2, ls="--")
    ax2.set_title("D/C distribution")
    ax2.set_xlabel("D/C ratio")
    ax2.set_ylabel("count")

    fig.tight_layout()
    fig.savefig(png_path, dpi=120)
    print(f"[viz] wrote {png_path}")
    plt.show()


def main():
    SapModel = attach_etabs()
    print("Model:", SapModel.GetModelFilename())
    if not SapModel.GetModelIsLocked():
        print("WARNING: model is not locked — analysis results may be absent. "
              "Run the analysis in ETABS first.")

    prefs = DesignPreferences(spec=SPEC, progid=PROGID)
    # Library is filled from the model after units are set (inside design()),
    # so build the adapter first, then read geometry within the kip-in context.
    adapter = EtabsCFSAdapter(SapModel, library=None, prefs=prefs,
                              demand_combos=pick_combos(SapModel),
                              axis_map=AxisMap(), station_mode=STATION_MODE)

    # Build the section library from the model (CF geometry + material Fy/Fu).
    from cfs_design import SectionLibrary
    _orig_units = SapModel.GetPresentUnits()
    SapModel.SetPresentUnits(3)  # kip-in so geometry/material read correctly
    try:
        geoms = adapter.section_geometries_from_model(CF_SHAPES)
    finally:
        SapModel.SetPresentUnits(_orig_units)
    adapter.lib = SectionLibrary.from_geometries(geoms)
    print(f"Cold-formed sections in model: {[g.name for g in geoms]}")
    for g in geoms:
        print(f"   {g.name}: d={g.depth_in:.3f} b={g.flange_in:.3f} "
              f"t={g.thickness_in:.4f} lip={g.lip_in:.3f} in  "
              f"Fy={g.Fy} Fu={g.Fu} ksi")

    members = adapter.cf_members(CF_SHAPES)
    print(f"\nCFS members detected (by shape): {len(members)}")
    if not members:
        print("No cold-formed members found. Nothing to design.")
        return

    print(f"Designing with {len(adapter.combos)} combos "
          f"(prefix '{COMBO_PREFIX}'), spec={SPEC.name}, "
          f"{'auto-select' if AUTO_SELECT else 'as-modelled section'}...")
    results = adapter.design(members, auto_select=AUTO_SELECT)

    # ── console summary ──
    results_sorted = sorted(
        results, key=lambda r: (r.governing_UC or 0), reverse=True)
    n_fail = sum(1 for r in results if not r.passed)
    print(f"\n{'member':>10} {'section':>10} {'D/C':>7}  {'combo':>10}  status")
    for r in results_sorted[:20]:
        print(f"{r.member_id:>10} {str(r.section):>10} "
              f"{(r.governing_UC if r.governing_UC is not None else 0):7.3f}  "
              f"{str(r.governing_combo):>10}  {'PASS' if r.passed else 'FAIL'}")
    if len(results_sorted) > 20:
        print(f"   ... {len(results_sorted) - 20} more")
    print(f"\nSummary: {len(results)} members, {n_fail} FAIL, "
          f"max D/C = {max((r.governing_UC or 0) for r in results):.3f}")

    # ── write-back + outputs ──
    adapter.to_csv(results, CSV_PATH)
    print(f"Wrote {CSV_PATH}")
    failed = adapter.flag_failures(results, FAIL_GROUP)
    if failed:
        print(f"Flagged {len(failed)} failing members into group '{FAIL_GROUP}'.")
    if AUTO_SELECT:
        n = adapter.assign_optimized_sections(results)
        print(f"Assigned optimised section to {n} members.")

    visualize(results, PNG_PATH)


if __name__ == "__main__":
    sys.exit(main())
