"""
cfs_design — Cold-Formed Steel member design via the RSG CFS API.

ETABS (or any analysis source) supplies member forces; this package runs the
CFS MemberCheck design and feeds results back.  Mirrors the ETABS AISC steel
design workflow: preferences -> per-member params (overwrites) -> demands ->
check / auto-select -> results back.

Layers (import only what you need):
    models        — data contract (no COM)
    engine        — RSG CFS COM wrapper (win32com)
    library       — section name -> .cfss mapping & auto-select order
    design        — source-agnostic workflow (check / auto-select / batch)
    etabs_adapter — ETABS coupling (demands extraction + write-back)

Typical ETABS use:
    from cfs_design import (SectionLibrary, DesignPreferences, CFSSpec,
                            EtabsCFSAdapter)
    lib   = SectionLibrary(mapping={...}, candidates=[...])
    prefs = DesignPreferences(spec=CFSSpec.AISI_2024_USA_ASD)
    adp   = EtabsCFSAdapter(SapModel, lib, prefs, demand_combos=[...])
    res   = adp.design(adp.members_in_group("Purlins_Roof"))
    adp.assign_optimized_sections(res); adp.flag_failures(res)
"""
from .models import (BracedFlange, CFSSectionType, CFSSpec, ComboCheck,
                     DemandCase, DesignParams, DesignPreferences, MemberForces,
                     MemberResult, SectionGeometry, SectionTrial)
from .engine import CFSEngine, CFSError
from .library import SectionLibrary
from .design import (DesignRunner, MemberDesignTask, check_member,
                     design_member)
from .etabs_adapter import AxisMap, EtabsCFSAdapter

__all__ = [
    "BracedFlange", "CFSSectionType", "CFSSpec", "ComboCheck", "DemandCase",
    "DesignParams", "DesignPreferences", "MemberForces", "MemberResult",
    "SectionGeometry", "SectionTrial",
    "CFSEngine", "CFSError", "SectionLibrary", "DesignRunner",
    "MemberDesignTask", "check_member", "design_member",
    "AxisMap", "EtabsCFSAdapter",
]
