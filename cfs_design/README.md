# cfs_design

Cold-Formed Steel (CFS) member design via the **RSG CFS API**, decoupled from the
analysis source. ETABS (or any app) provides member forces; this package runs the
CFS `MemberCheck` design and feeds results back. It deliberately mirrors the ETABS
AISC steel-design workflow so it slots into existing pipelines.

> ETABS has **no native CFS design**. This module fills that gap the same way the
> ETABS steel designer works: *preferences → per-member overwrites → demands from
> analysis → check / auto-select → results back to the model.*

## Why a package (not the notebook)

The original `CFS_Wall_Stud_Design.ipynb` mixed three concerns: the CFS engine,
*wall-stud-specific* load generation from PSF area loads, and presentation. For a
reusable, analysis-driven module those must be separated. Here the engine consumes
**member forces directly** (which ETABS already computes), and all ETABS coupling
lives in one adapter.

## Layers

| Module | Responsibility | COM? |
|---|---|---|
| `models` | Data contract: `MemberForces`, `DemandCase`, `DesignParams`, `DesignPreferences`, `MemberResult` … | none |
| `engine` | RSG CFS COM wrapper: license, `LoadSection`, `MemberCheck` | win32com (lazy) |
| `library` | `name → .cfss` mapping + auto-select ordering | none |
| `design` | Source-agnostic workflow: `check_member`, `design_member`, `DesignRunner` | none |
| `etabs_adapter` | ETABS demands extraction + write-back | comtypes |

`models`, `library`, and `design` import **no COM**, so the whole workflow is
unit-testable with a stub engine. Only `engine` needs CFS; only `etabs_adapter`
needs ETABS. A different host app (Revit, a REST service, a CSV batch) just
provides `DemandCase`s and reuses everything else.

## Sections: built from geometry (no `.cfss` files)

The CFS COM API can define a section in memory from its dimensions
(`Calculation.DefineSection(SectionData)`), so this project builds each CF
section directly from `Profiles.cfs_profiles_mm` — no `.cfss` catalog needed:

```python
from cfs_design import SectionGeometry, SectionLibrary
geoms = [SectionGeometry.lipped_c_from_mm(name, d, b, t, r, lip, Fy=33, Fu=45)
         for name, d, b, t, r, lip in cfs_profiles_mm]
lib = SectionLibrary.from_geometries(geoms)   # name -> in-memory section
```

`.cfss` files are still supported (`SectionLibrary(mapping={name: path})` or
`SectionLibrary.from_directory(...)`); a library entry can be *either* a path or
a `SectionGeometry`, transparently. Notes for geometry sections:
- Dimensions are CFS-native **inches** (`lipped_c_from_mm` converts from mm).
- CFS requires a **non-zero bend radius**; a stored radius of 0 is replaced by
  the thickness (one-thickness inside bend).
- Lipped channel = `SectionType` *CeeStiffened*; web/lip angles default to 90°
  (the API expresses them in radians internally — leave them alone).

## Conventions (RSG CFS native)

- Units: **kips, kip-inch, inches** (the ETABS adapter extracts in eUnits=3).
- `P`: **compression positive** (ETABS axial is tension-positive → the adapter
  flips the sign via `AxisMap.P_sign = -1`).
- `Mx`: major-axis moment, `My`: minor; `Vy` pairs with `Mx`.
- Default `AxisMap`: `Mx←M3`, `My←M2`, `Vy←V2`, `Vx←V3`. Edit `AxisMap` if a
  member's local axes are oriented differently — never the engine.
- Governing unity check `UC = max(PMxMy1, PMxMy2, MxVy)`; pass if `UC ≤ unity_limit`.

## ETABS usage

```python
from cfs_design import (SectionLibrary, DesignPreferences, CFSSpec,
                        EtabsCFSAdapter, AxisMap)

lib   = SectionLibrary(mapping={"CF10CAL14": r"...\CF10CAL14.cfss", ...},
                       candidates=["CF4CAL14", ..., "CF12CAL12"])  # light→heavy
prefs = DesignPreferences(spec=CFSSpec.AISI_2024_USA_ASD,
                          progid="RSG.CFS15.Calculation")
adp   = EtabsCFSAdapter(SapModel, lib, prefs,
                        demand_combos=["D + L", "SS-02.1", ...])

members = adp.members_in_group("Purlins_Roof")
results = adp.design(members, auto_select=True)   # analysis must be run first

adp.assign_optimized_sections(results)   # write-back: optimised sections
adp.flag_failures(results, "CFS_DC_Fail")# write-back: failures group (UI-visible)
adp.to_csv(results, "cfs_results.csv")
```

`auto_select=False` checks each member's *current* section instead of optimising.
`params_override=lambda member, length: DesignParams.from_length(length, Ly=48, Cbx=1.3)`
sets per-member unbraced lengths / Cb / Cm (the CFS analogue of design overwrites).

## What "results back to ETABS" means

ETABS exposes no CFS results table, so write-back uses the two things an engineer
can act on in the model:
1. **`assign_optimized_sections`** — sets each passing member's frame section to
   the auto-selected one (requires the matching ETABS CF section to exist;
   see `Profiles.define_cold_formed_c_sections`).
2. **`flag_failures`** — drops failing members into an ETABS group so they're
   selectable/visible in the UI.
   Plus a CSV/`as_row()` report for documentation.

## Requirements

- `pywin32` (`win32com`) and a licensed **RSG CFS 14/15** install for design.
- `comtypes` + ETABS for the adapter (already used elsewhere in this project).
- The data/design/library layers need neither — only `pip install`-free stdlib.

## Before first run — you must provide / confirm

- The **demand combos** to design for (the model's ASD strength combos on CF members).
- The **member steel** (`Fy`/`Fu`) per `SectionGeometry` — defaults A653 Gr33
  (Fy=33, Fu=45 ksi).
- Confirm the **`AxisMap`** matches your members' local-axis orientation
  (default `Mx←M3`, `Vy←V2`, `P` sign-flipped).
- Optionally, per-member **unbraced lengths / Cb / Cm** via `params_override`.

Section geometry is taken automatically from `Profiles.cfs_profiles_mm`; `.cfss`
files are *not* required for this project.
