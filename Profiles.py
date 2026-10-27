import constants
import numpy as np


STEEL_SECTIONS_FILE  =  "AISC15.xml" # "Sections14.pro"

#todos los nacionales y los W21 y W24 de Texas
#"section", d, tw, bf, tf, k [in]
w_profiles = np.array([
['W24X84', 24.1, 0.47, 9.02, 0.77, 1.27], 
['W24X76', 23.9, 0.44, 8.99, 0.68, 1.18], 
['W24X68', 23.7, 0.415, 8.97, 0.585, 1.09], 
['W24X62', 23.7, 0.43, 7.04, 0.59, 1.19], 
['W24X55', 23.6, 0.395, 7.01, 0.505, 1.11],
['W21X93', 21.6, 0.58, 8.42, 0.93, 1.43], 
['W21X83', 21.4, 0.515, 8.36, 0.835, 1.34], 
['W21X73', 21.2, 0.455, 8.3, 0.74, 1.24], 
['W21X68', 21.1, 0.43, 8.27, 0.685, 1.19], 
['W21X62', 21, 0.4, 8.24, 0.615, 1.12], 
['W21X57', 21.1, 0.405, 6.56, 0.65, 1.15], 
['W21X55', 20.8, 0.375, 8.22, 0.522, 1.02], 
['W21X50', 20.8, 0.38, 6.53, 0.535, 1.04], 
['W21X48', 20.6, 0.35, 8.14, 0.43, 0.93], 
['W21X44', 20.7, 0.35, 6.5, 0.45, 0.95], 
['W18X71', 18.5, 0.495, 7.64, 0.81, 1.21], 
['W18X65', 18.4, 0.45, 7.59, 0.75, 1.15], 
['W18X60', 18.2, 0.415, 7.56, 0.695, 1.1], 
['W18X55', 18.1, 0.39, 7.53, 0.63, 1.03], 
['W18X50', 18, 0.355, 7.5, 0.57, 0.972], 
['W18X46', 18.1, 0.36, 6.06, 0.605, 1.01], 
['W18X40', 17.9, 0.315, 6.02, 0.525, 0.927], 
['W18X35', 17.7, 0.3, 6, 0.425, 0.827], 
['W16X57', 16.4, 0.43, 7.12, 0.715, 1.12], 
['W16X50', 16.3, 0.38, 7.07, 0.63, 1.03], 
['W16X45', 16.1, 0.345, 7.04, 0.565, 0.967], 
['W16X40', 16, 0.305, 7, 0.505, 0.907], 
['W16X36', 15.9, 0.295, 6.99, 0.43, 0.832], 
['W16X31', 15.9, 0.275, 5.53, 0.44, 0.842], 
['W16X26', 15.7, 0.25, 5.5, 0.345, 0.747], 
['W14X53', 13.9, 0.37, 8.06, 0.66, 1.25], 
['W14X48', 13.8, 0.34, 8.03, 0.595, 1.19], 
['W14X43', 13.7, 0.305, 8, 0.53, 1.12], 
['W14X38', 14.1, 0.31, 6.77, 0.515, 0.915], 
['W14X34', 14, 0.285, 6.75, 0.455, 0.855], 
['W14X30', 13.8, 0.27, 6.73, 0.385, 0.785], 
['W14X26', 13.9, 0.255, 5.03, 0.42, 0.82], 
['W14X22', 13.7, 0.23, 5, 0.335, 0.735], 
['W12X50', 12.2, 0.37, 8.08, 0.64, 1.14], 
['W12X45', 12.1, 0.335, 8.05, 0.575, 1.08], 
['W12X40', 11.9, 0.295, 8.01, 0.515, 1.02], 
['W12X35', 12.5, 0.3, 6.56, 0.52, 0.82], 
['W12X30', 12.3, 0.26, 6.52, 0.44, 0.74], 
['W12X26', 12.2, 0.23, 6.49, 0.38, 0.68], 
['W12X22', 12.3, 0.26, 4.03, 0.425, 0.725], 
['W12X19', 12.2, 0.235, 4.01, 0.35, 0.65], 
['W12X16', 12, 0.22, 3.99, 0.265, 0.565], 
['W12X14', 11.9, 0.2, 3.97, 0.225, 0.525], 
['W10X30', 10.5, 0.3, 5.81, 0.51, 0.81], 
['W10X26', 10.3, 0.26, 5.77, 0.44, 0.74], 
['W10X22', 10.2, 0.24, 5.75, 0.36, 0.66], 
['W10X19', 10.2, 0.25, 4.02, 0.395, 0.695], 
['W10X17', 10.1, 0.24, 4.01, 0.33, 0.63], 
['W10X15', 9.99, 0.23, 4, 0.27, 0.57], 
['W10X12', 9.87, 0.19, 3.96, 0.21, 0.51], 
['W8X21', 8.28, 0.25, 5.27, 0.4, 0.7], 
['W8X18', 8.14, 0.23, 5.25, 0.33, 0.63], 
['W8X15', 8.11, 0.245, 4.01, 0.315, 0.615], 
['W8X13', 7.99, 0.23, 4, 0.255, 0.555], 
['W8X10', 7.89, 0.17, 3.94, 0.205, 0.505], 
['W6X25', 6.38, 0.32, 6.08, 0.455, 0.754], 
['W6X20', 6.2, 0.26, 6.02, 0.365, 0.664], 
['W6X16', 6.28, 0.26, 4.03, 0.405, 0.655], 
['W6X15', 5.99, 0.23, 5.99, 0.26, 0.559], 
['W6X12', 6.03, 0.23, 4, 0.28, 0.53],
['W6X9', 5.9, 0.17, 3.94, 0.215, 0.465], 
], dtype=object)

#Haunched and nonprismatic frames
#the lists are populated later
nonprismatic_haunched_sections = []
haunched_sections = []

#HSS'S
hss_profiles = [
    'HSS16X16X5/8', 'HSS16X16X1/2', 'HSS16X16X3/8', 'HSS14X14X1/2',
    'HSS14X14X3/8', 'HSS12X12X1/2', 'HSS12X12X3/8', 'HSS12X12X1/4',
    'HSS10X10X1/2', 'HSS10X10X3/8', 'HSS10X10X1/4', 'HSS8X8X1/2',
    'HSS8X8X3/8',   'HSS8X8X1/4',   'HSS6X6X1/2',   'HSS6X6X3/8',
    'HSS6X6X1/4',   'HSS6X6X3/16',  'HSS4X4X1/2',   'HSS4X4X3/8',
    'HSS4X4X1/4',   'HSS4X4X3/16',  'HSS4X4X1/8'
]


#Double angles
double_ang_profiles = ["2L2X2X1/4", "2L2X2X3/8",  "2L3X3X1/4", "2L3X3X3/8", "2L4X4X1/4", "2L4X4X3/8", "2L4X4X1/2", "2L5X5X3/8","2L5X5X1/2", "2L5X5X3/4", "2L6X6X3/8", "2L6X6X1/2", "2L6X6X3/4"]

#Single angles
single_ang_profiles = ["L2X2X1/4", "L2X2X3/8",  "L3X3X1/4", "L3X3X3/8", "L4X4X1/4", "L4X4X3/8", "L4X4X1/2", "L5X5X3/8","L5X5X1/2", "L5X5X3/4", "L6X6X3/8", "L6X6X1/2", "L6X6X3/4"]

#Rods
rod_profiles = [["r3/8", 3/8], ["r1/2", 1/2], ["r5/8", 5/8], ["r3/4", 3/4], ["r7/8", 7/8], ["r1", 1], ["r1-1/4", 1.25], ["r1-1/2", 1.5]]

#ColdFormed Properties
#[name, d, b, thickness, radius, lip depth], mm
cfs_profiles_mm = [
["CF4CAL14", 4*25.4, 50.8, 1.9, 0.0, 15.2],
["CF5CAL14", 5*25.4, 50.8, 1.9, 0.0, 15.2],
["CF6CAL14", 6*25.4, 63.5, 1.9, 0.0, 17.8],
["CF8CAL14", 8*25.4, 76.2, 1.9, 0.0, 17.8],
["CF10CAL14", 10*25.4, 88.9, 1.9, 0.0, 17.8],
["CF12CAL14", 12*25.4, 88.9, 1.9, 0.0, 17.8],
["CF10CAL12", 10*25.4, 88.9, 2.66, 0.0, 17.8],
["CF12CAL12", 12*25.4, 88.9, 2.66, 0.0, 17.8]
]

# ════════════════════════════════════════════════════════════
# HELPER — reusable import + auto-select builder
# ════════════════════════════════════════════════════════════
def _import_section_group(SapModel, profiles, material, auto_name, label, existing):
    """Import a profile list and build an Auto-Select group."""
    successful, failed = [], []

    for sec in profiles:
        try:
            if sec in existing:              # already in model — skip import
                successful.append(sec)
                continue
            ret = SapModel.PropFrame.ImportProp(sec, material, STEEL_SECTIONS_FILE, sec)
            # ETABS may return 1 on success (SAP2000 returns 0).
            # Treat both as success — the section is imported either way.
            successful.append(sec)
            existing.add(sec)
        except Exception as e:
            failed.append(sec)
            print(f"  [ERROR] {sec} — {e}")

    if successful:
        try:
            SapModel.PropFrame.SetAutoSelectSteel(auto_name, len(successful), successful)
        except Exception as e:
            print(f"  [ERROR] SetAutoSelectSteel '{auto_name}' — {e}")
    else:
        print(f"  [WARN]  No {label} imported — auto-select group not created.")

    print(f"  {label}: {len(successful) - len(failed)} imported, "
          f"{len([s for s in successful if s in existing])} existed, "
          f"{len(failed)} failed.")

# ════════════════════════════════════════════════════════════
# UNIT CONSTANTS  (ETABS eUnits integer codes)
# ════════════════════════════════════════════════════════════
# Imperial              Metric
# 1  lb_in_F            5  kN_mm_C
# 2  lb_ft_F            6  kN_m_C
# 3  kip_in_F  ← default 7  kgf_mm_C
# 4  kip_ft_F            8  kgf_m_C
#                        9  N_mm_C
#                       10  N_m_C
#                       11  Ton_mm_C  ...


# ════════════════════════════════════════════════════════════
# DEFINE COLD FORMED C SECTIONS  via Database Table
# No SetColdC API exists in ETABS 18 v1 — this is the solution
# ════════════════════════════════════════════════════════════


_CF_TABLE = "Frame Section Property Definitions - Cold Formed C"

# Default values for the 12 non-geometry columns ETABS requires in every row.
# (Mirror flag, the 8 stiffness/mass modifiers, color, GUID, notes.)
# GUID is left blank so ETABS generates one.  Column identifiers below are the
# table's DISPLAY names — NOT the API key names (t3/t2/tw…), which the
# interactive-import engine does not recognise.
_CF_DEFAULTS = {
    "Mirror About 2-axis": "No",
    "Area Modifier": "1", "As2 Modifier": "1", "As3 Modifier": "1",
    "J Modifier": "1", "I22 Modifier": "1", "I33 Modifier": "1",
    "Mass Modifier": "1", "Weight Modifier": "1",
    "Color": "Gray8Dark", "GUID": "", "Notes": "",
}


def define_cold_formed_c_sections(SapModel, profiles, material, units=3):
    """
    Define cold-formed C sections in ETABS via the DatabaseTables API.

    No SetColdC API exists in ETABS 18 v1, so sections are added by editing the
    "Frame Section Property Definitions - Cold Formed C" table directly.

    Note: ETABS does not allow cold-formed sections in a steel auto-select list
    (SetAutoSelectSteel returns retcode 1 for them), so no auto-select group is
    built — assign CF sections to frames directly (e.g. "CF10CAL14").

    Notes on the ETABS 18.1.1 interactive-table quirks (all verified against a
    live model — get these wrong and the import silently no-ops):
      * Material `material` must already exist, or Apply succeeds with 0 rows.
      * Columns must be the table's DISPLAY names (Web Depth / Flange Width /
        Thickness / Lip Depth), not API keys (t3/t2/tw/LipDepth).
      * Every row must carry all of the table's columns — see _CF_DEFAULTS.
      * SetTableForEditingArray returns retcode 1 even on success; the real
        result is ApplyEditedTables' fatal-error count (+ import log).
      * All new rows are batched into ONE Set→Apply (Apply rewrites the table).

    Parameters
    ----------
    SapModel  : ETABS SapModel COM object
    profiles  : list of [name, depth, flange_width, thickness, corner_radius, lip_depth]
                Geometry in `units`.
    material  : str — ETABS material name (must already exist)
    units     : int — eUnits code (default: 3 = kip_in_F)
                      1=lb_in 2=lb_ft 3=kip_in 4=kip_ft
                      5=kN_mm 6=kN_m  7=kgf_mm_C 8=kgf_m_C 9=N_mm  10=N_m ...
    """
    db = SapModel.DatabaseTables

    # ── Switch to requested units (geometry is read in the active units when
    #    ApplyEditedTables runs); always restored via finally ──
    original_units = SapModel.GetPresentUnits()
    SapModel.SetPresentUnits(units)

    successful, failed = [], []
    added = []

    try:
        # ── Read the table (works with 0 existing rows once the table exists) ──
        # comtypes return layout: (rc, FieldNames[], NumRecords, TableData[], Version)
        g = db.GetTableForEditingArray(_CF_TABLE, "All", 0, [], 0, [])
        col_names = list(g[1])
        num_cols  = len(col_names)
        cur_data  = list(g[3])
        version   = g[4]
        num_rows  = len(cur_data) // num_cols if num_cols else 0
        idx = {name: i for i, name in enumerate(col_names)}

        existing = {cur_data[i * num_cols + idx["Name"]] for i in range(num_rows)}

        # ── Build all new rows (full-width, display-name columns) ──
        new_rows = []
        for sec in profiles:
            name, d, b, t, r, lip = sec
            if name in existing:
                successful.append(name)
                continue
            row = [""] * num_cols
            for col, val in _CF_DEFAULTS.items():
                if col in idx:
                    row[idx[col]] = val
            row[idx["Name"]]         = name
            row[idx["Material"]]     = material
            row[idx["Web Depth"]]    = str(d)
            row[idx["Flange Width"]] = str(b)
            row[idx["Thickness"]]    = str(t)
            row[idx["Radius"]]       = str(r)
            row[idx["Lip Depth"]]    = str(lip)
            new_rows.extend(row)
            added.append(name)

        # ── Single Set → Apply for the whole batch ──
        if added:
            full_data  = cur_data + new_rows
            total_rows = num_rows + len(added)
            db.SetTableForEditingArray(_CF_TABLE, version, col_names,
                                       total_rows, full_data)  # retcode 1 is benign
            ret_app   = db.ApplyEditedTables(True, 0, 0, 0, 0, "")
            num_fatal = ret_app[1]
            if num_fatal == 0:
                successful.extend(added)
            else:
                failed.extend(added)
                log = next((x for x in ret_app if isinstance(x, str)), "")
                print(f"  [FAIL]  Cold-Formed C import — {num_fatal} fatal error(s)")
                print(f"          {log[:400]}")
    except Exception as e:
        print(f"  [ERROR] Cold-Formed C table edit — {e}")
        failed.extend(p[0] for p in profiles if p[0] not in successful)
    finally:
        SapModel.SetPresentUnits(original_units)

    imported = len(set(added) & set(successful))
    already  = len(successful) - imported
    print(f"  Cold Formed C: {imported} imported, "
          f"{already} already existed, {len(failed)} failed.")
    return successful, failed

# ════════════════════════════════════════════════════════════
# MAIN FUNCTION
# ════════════════════════════════════════════════════════════
def set_initial_sections_type_1(SapModel,
    vertical_bracing_double_angles=True,
    purlin_section_roof="CF10CAL14",
    purlin_section_lateral="CF10CAL14",
    purlin_section_end="CF10CAL14",
    horizontal_bracing_section="Auto-rods"):

    model_units = SapModel.GetPresentUnits()

    # ── Materials ──────────────────────────────────────────
    print("Defining materials...")
    SapModel.PropMaterial.AddMaterial("A36",        1, "United States", "ASTM A36",   "Grade 36")
    SapModel.PropMaterial.AddMaterial("A53GrB",     1, "United States", "ASTM A53",   "Grade B")
    SapModel.PropMaterial.AddMaterial("A500GrB46",  1, "United States", "ASTM A500",  "Grade B, Fy 46 (HSS Rect.)")
    SapModel.PropMaterial.AddMaterial("A500GrC",    1, "United States", "ASTM A500",  "Grade C")
    SapModel.PropMaterial.AddMaterial("A572Gr50",   1, "United States", "ASTM A572",  "Grade 50")
    SapModel.PropMaterial.AddMaterial("A653SQGr33", 5, "United States", "ASTM A653",  "SQ Grade 33")
    SapModel.PropMaterial.AddMaterial("A653SQGr50", 5, "United States", "ASTM A653",  "SQ Grade 50")

    # ── Get existing sections once (shared cache for all imports) ──
    try:
        ret = SapModel.PropFrame.GetNameList(0, [])
        existing = set(list(ret[2])) if ret[2] else set()
    except Exception as e:
        print(f"[WARN] Could not fetch existing sections: {e}")
        existing = set()

    # ── W Sections ────────────────────────────────────────
    print("Importing W sections...")
    _import_section_group(SapModel, list(w_profiles[:, 0]),
                          "A992Fy50", "Auto-Ws", "W sections", existing)

    # ── Double Angles ─────────────────────────────────────
    print("Importing double angle sections...")
    _import_section_group(SapModel, double_ang_profiles,
                          "A36", "Auto-2L", "Double angles", existing)

    # ── Single Angles ─────────────────────────────────────
    print("Importing single angle sections...")
    _import_section_group(SapModel, single_ang_profiles,
                          "A36", "Auto-L", "Single angles", existing)

    # ── HSS ───────────────────────────────────────────────
    print("Importing HSS sections...")
    _import_section_group(SapModel, hss_profiles,
                          "A500GrB46", "Auto-HSS", "HSS", existing)
    
    # ── Rods (circular) ───────────────────────────────────
    SapModel.SetPresentUnits(1)  # inches
    for name, dia in rod_profiles:
        try:
            SapModel.PropFrame.SetCircle(name, "A36", dia)
        except Exception as e:
            print(f"  [ERROR] Rod {name} — {e}")
    SapModel.SetPresentUnits(model_units)
    SapModel.PropFrame.SetAutoSelectSteel("Auto-rods", len(rod_profiles),
                                          [r[0] for r in rod_profiles])

    """ # ── Cold-Formed C sections ─────────────────────────────
    # ETABS does not have SetColdC. Use SetChannel as closest approximation.
    # SetChannel(Name, MatProp, T3=depth, T2=flange_width, Tf=flange_t, Tw=web_t)
    # The lip is not modeled but the channel shape captures the primary behavior.
    SapModel.SetPresentUnits(7)  # mm
    for sec in cfs_profiles:
        name, d, b, t, r, lip = sec
        try:
            try:
                SapModel.PropFrame.SetColdC(name, "A653SQGr33", d, b, t, r, lip)
            except AttributeError:
                # ETABS fallback: use channel shape
                ret = SapModel.PropFrame.SetChannel(name, "A653SQGr33", d, b, t, t)
                if ret != 0:
                    print(f"  [WARN] SetChannel for {name} returned {ret}")
            SapModel.PropFrame.SetTube("2-" + name, "A653SQGr33", d, b * 2, t, t)
        except Exception as e:
            print(f"  [ERROR] CFS {name} — {e}")
    SapModel.SetPresentUnits(model_units)"""

    # Millimetres (units=9 = N_mm_C). Profiles assigned to frames directly;
    # ETABS disallows cold-formed sections in an auto-select list.
    define_cold_formed_c_sections(SapModel, cfs_profiles_mm, "A653SQGr33", units=9)

    # ── Haunched & Nonprismatic sections ──────────────────
    # BUG FIX #3: np.vectorize() rejected numpy.str_/float64 by COM API
    # Use a plain loop with explicit str()/float() casts instead
    SapModel.SetPresentUnits(1)
    for row in w_profiles:
        name    = str(row[0])
        d, tw   = float(row[1]), float(row[2])
        bf, tf  = float(row[3]), float(row[4])
        k       = float(row[5])
        haunch_d = d * 2 - k - 0.125  # 2d - k - 1/8"

        try:
            SapModel.PropFrame.SetISection(
                "HAUNCHED-" + name, "A992Fy50",
                haunch_d, bf, tf, tw, bf, tf
            )
            SapModel.PropFrame.SetNonPrismatic(
                "NP-" + name, 1,
                ["HAUNCHED-" + name], [name],
                [1], [1], [1], [1]
            )
            haunched_sections.append("HAUNCHED-" + name)
            nonprismatic_haunched_sections.append("NP-" + name)
        except Exception as e:
            print(f"  [ERROR] Haunched {name} — {e}")

    if haunched_sections:
        SapModel.PropFrame.SetAutoSelectSteel("Auto-haunched",
                                              len(haunched_sections), haunched_sections)
    SapModel.SetPresentUnits(model_units)

    # ── Frame group assignments ────────────────────────────
    print("Assigning sections to groups...")
    assignments = [
        ("Main_Columns",              "Auto-Ws"),
        ("Haunched_Columns",          "Auto-haunched"),
        ("Main_Beams",                "Auto-Ws"),
        ("Haunched_Beams",            "Auto-haunched"),
        ("Haunched_Beams_Central",    "Auto-Ws"),
        ("Wind_Columns",              "Auto-Ws"),
        ("Main_Columns_end",          "Auto-Ws"),
        ("Haunched_Columns_end",      "Auto-Ws"),
        ("Main_Beams_end",            "Auto-Ws"),
        ("Haunched_Beams_end",        "Auto-haunched"),
        ("Haunched_Beams_Central_end","Auto-Ws"),
        ("Wind_Columns_end",          "Auto-Ws"),
        ("Interior_Columns",          "Auto-Ws"),
        ("Purlins_Roof",              purlin_section_roof),
        ("Purlins_Lateral",           purlin_section_lateral),
        ("Purlins_end",               purlin_section_end),
        ("Bracing_Vertical",          "Auto-2L" if vertical_bracing_double_angles else "Auto-L"),
        ("Bracing_Vertical_compression", "Auto-HSS"),
        ("Bracing_Horizontal",        horizontal_bracing_section),
    ]
    for group, section in assignments:
        try:
            SapModel.FrameObj.SetSection(group, section, 1)
        except Exception as e:
            print(f"  [ERROR] SetSection '{group}' → '{section}' — {e}")




"""
class Profiles:
    def __init__(self, SapModel, buildng_type = 1):
        #Main frames
        self.SapModel = SapModel
        self.model_units = SapModel.GetPresentUnits()
        self.type = buildng_type


        #Steel
        ret = SapModel.PropMaterial.AddMaterial("A36", 1, "United States", "ASTM A36", "Grade 36")
        ret = SapModel.PropMaterial.AddMaterial("A53GrB", 1, "United States", "ASTM A53", "Grade B")
        ret = SapModel.PropMaterial.AddMaterial("A500GrB46", 1, "United States", "ASTM A500", "Grade B, Fy 46 (HSS Rect.)")
        ret = SapModel.PropMaterial.AddMaterial("A500GrC", 1, "United States", "ASTM A500", "Grade C")
        ret = SapModel.PropMaterial.AddMaterial("A572Gr50", 1, "United States", "ASTM A572", "Grade 50")
        #Cold Formed
        ret = SapModel.PropMaterial.AddMaterial("A653SQGr33", 5, "United States", "ASTM A653", "SQ Grade 33")
        ret = SapModel.PropMaterial.AddMaterial("A653SQGr50", 5, "United States", "ASTM A653", "SQ Grade 50")
        #Concrete(TODO)




        #import w sections
        vfunc = np.vectorize(SapModel.PropFrame.ImportProp)(w_profiles[:,0], "A992Fy50", "STEEL_SECTIONS_FILE", w_profiles[:, 0])
        #Add to auto section
        w_names = (w_profiles[:, 0]).tolist()
        ret = SapModel.PropFrame.SetAutoSelectSteel("Auto-Ws", len(w_names), w_names)


        #Import double angle sections
        for i in double_ang_profiles:
            ret = SapModel.PropFrame.ImportProp(i, "A36", "STEEL_SECTIONS_FILE", i)
        #Add to auto section
        ret = SapModel.PropFrame.SetAutoSelectSteel("Auto-2L", len(double_ang_profiles), double_ang_profiles)
        
        #HSS'S


        SapModel.SetPresentUnits(1)
        for i in rod_profiles:
            SapModel.PropFrame.SetCircle(i[0], "A36", i[1])
        SapModel.SetPresentUnits(self.model_units)
        #Add to auto section
        ret = SapModel.PropFrame.SetAutoSelectSteel("Auto-rods", len(rod_profiles), [row[0] for row in rod_profiles])




       

        SapModel.SetPresentUnits(7)
        for i in cfs_profiles:
            ret = SapModel.PropFrame.SetColdC(i[0], "A653SQGr33", i[1], i[2], i[3], i[4], i[5])
            ret = SapModel.PropFrame.SetTube("2-" + i[0], "A653SQGr33", i[1], i[2]*2, i[3], i[3])

        SapModel.SetPresentUnits(self.model_units)

        if self.type == 1:
            #Define haunched and nonprismatic sections
            SapModel.SetPresentUnits(1)
            #Define haunched sections
            ret = np.vectorize(SapModel.PropFrame.SetISection)("HAUNCHED-" + w_profiles[:,0], "A992Fy50", w_profiles[:,1] * 2 - w_profiles[:,5] - 0.125, # 2*d - k - 1/8
            w_profiles[:,3], w_profiles[:,4], w_profiles[:,2], w_profiles[:,3], w_profiles[:,4])
            #Define nonprismatic sections
            for i in w_profiles:
                name = i[0]
                ret = SapModel.PropFrame.SetNonPrismatic("NP-" + name, 1, ["HAUNCHED-" + name], [name], [1], [1], [1], [1])
                haunched_sections.append("HAUNCHED-" + name) 
                nonprismatic_haunched_sections.append("NP-" + name)            
            ret = SapModel.PropFrame.SetAutoSelectSteel("Auto-haunched", len(haunched_sections), haunched_sections)

            SapModel.SetPresentUnits(self.model_units)


            #Old method: As SD section  
            
            SapModel.SetPresentUnits(1)
            ret = np.vectorize(SapModel.PropFrame.SetSDSection)("HAUNCHED-" + w_profiles[:,0], "A992Fy50", 1)
            for i in w_profiles:
                name = i[0]
                dt = i[1] - i[5] - 0.25
                ret = SapModel.PropFrame.SDShape.SetISection("HAUNCHED-" + name, name, "A992Fy50", name, 0, 0, 0)
                ret = SapModel.PropFrame.SDShape.SetTee("HAUNCHED-" + name, name + "-HAUNCH", "A992Fy50", "", 0, -(i[1] + dt)/2 , 180, -1, dt, i[3], i[4], i[2])
                ret = SapModel.PropFrame.SetNonPrismatic("NP-" + name, 1, ["HAUNCHED-" + name], [name], [1], [1], [1], [1])
                haunched_sections.append("HAUNCHED-" + name) 
                nonprismatic_haunched_sections.append("NP-" + name)            
            ret = SapModel.PropFrame.SetAutoSelectSteel("Auto-haunched", len(haunched_sections), haunched_sections)

            SapModel.SetPresentUnits(self.model_units)
            
            #Assign to groups
            print("assign")
            ret = SapModel.FrameObj.SetSection("Main_Columns", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Haunched_Columns", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Main_Beams", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Haunched_Beams", "Auto-haunched", 1)
            ret = SapModel.FrameObj.SetSection("Haunched_Beams_Central", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Wind_Columns", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Main_Columns_end", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Haunched_Columns_end", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Main_Beams_end", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Haunched_Beams_end", "Auto-haunched", 1)
            ret = SapModel.FrameObj.SetSection("Haunched_Beams_Central_end", "Auto-Ws", 1)
            ret = SapModel.FrameObj.SetSection("Wind_Columns_end", "Auto-Ws", 1)

            #Purlins
            ret = SapModel.FrameObj.SetSection("Purlins_Roof", "CF10CAL14", 1)
            ret = SapModel.FrameObj.SetSection("Purlins_Lateral", "CF10CAL14", 1)
            ret = SapModel.FrameObj.SetSection("Purlins_end", "CF10CAL14", 1)

            #Bracing vertical
            ret = SapModel.FrameObj.SetSection("Bracing_Vertical", "Auto-2L", 1)

            #Bracing Horizontal
            ret = SapModel.FrameObj.SetSection("Bracing_Horizontal", "Auto-rods", 1)

"""







