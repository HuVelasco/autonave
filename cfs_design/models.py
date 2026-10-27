"""
Data contract for cold-formed-steel (CFS) member design.

These dataclasses are the *only* thing callers (ETABS adapter, a wall-stud app,
a REST service, …) need to speak.  Nothing here imports win32com or comtypes,
so the contract is portable and unit-testable without any COM server present.

Conventions (RSG CFS native units & signs):
    forces : kips, kip-inch
    P      : compression POSITIVE  (note: ETABS axial is tension-positive;
             the ETABS adapter flips the sign)
    Mx     : moment about the section x-axis  (major axis of a C/Z stud)
    My     : moment about the section y-axis  (minor axis)
    Vy     : shear associated with Mx (major-axis shear)
    Vx     : shear associated with My
    lengths: inches
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum
from typing import List, Optional


class CFSSpec(IntEnum):
    """RSG CFS design-spec enum values (subset; pass a raw int for others)."""
    AISI_2016_USA_ASD = 27
    AISI_2022_USA_ASD = 37
    AISI_2024_USA_ASD = 42


class BracedFlange(IntEnum):
    NONE = 0
    TOP = 1
    BOTTOM = 2
    BOTH = 3


class CFSSectionType(IntEnum):
    """RSG CFS SectionType enum (subset)."""
    CEE = 1               # plain channel
    CEE_STIFFENED = 2     # lipped channel  (the CFxCALyy profiles)
    ZEE = 3
    ZEE_STIFFENED = 4
    ANGLE = 9
    ANGLE_STIFFENED = 10
    HAT = 11


_MM_PER_IN = 25.4


@dataclass
class SectionGeometry:
    """A CFS section defined parametrically (CFS-native units: inches, ksi).

    Lets the design run with NO .cfss files — the engine builds the section in
    memory via DefineSection.  CFS requires a non-zero bend radius, so callers
    that have radius=0 should substitute the thickness (see ``lipped_c_from_mm``).
    """
    name: str
    section_type: int
    depth_in: float
    flange_in: float
    thickness_in: float
    radius_in: float
    lip_in: float = 0.0
    Fy: float = 33.0   # ksi
    Fu: float = 45.0   # ksi

    @classmethod
    def lipped_c_from_mm(cls, name: str, depth_mm: float, flange_mm: float,
                         thickness_mm: float, radius_mm: float, lip_mm: float,
                         Fy: float = 33.0, Fu: float = 45.0) -> "SectionGeometry":
        """Build a lipped-channel (CeeStiffened) section from mm geometry.
        radius_mm <= 0 is replaced by the thickness (CFS needs radius > 0)."""
        r = radius_mm if radius_mm > 0 else thickness_mm
        return cls(
            name=name, section_type=CFSSectionType.CEE_STIFFENED,
            depth_in=depth_mm / _MM_PER_IN, flange_in=flange_mm / _MM_PER_IN,
            thickness_in=thickness_mm / _MM_PER_IN, radius_in=r / _MM_PER_IN,
            lip_in=lip_mm / _MM_PER_IN, Fy=Fy, Fu=Fu)


@dataclass
class MemberForces:
    """One demand set in CFS conventions.  Dx/Dy are deflection demands (in);
    leave 0 to skip the deflection check."""
    P: float = 0.0
    Mx: float = 0.0
    My: float = 0.0
    Vx: float = 0.0
    Vy: float = 0.0
    Dx: float = 0.0
    Dy: float = 0.0


@dataclass
class DemandCase:
    """A named demand (one load combination, optionally at one station)."""
    combo: str
    forces: MemberForces
    label: str = ""
    station: Optional[float] = None  # relative position 0..1 along member, if known


@dataclass
class DesignParams:
    """Per-member design parameters — the CFS analogue of ETABS design
    overwrites.  Unbraced lengths default to the member length (set by the
    caller); everything else defaults to the common K=1 / Cb=1 / Cm=1 case."""
    Lx: float
    Ly: float
    Lt: float
    Lm: float
    Kx: float = 1.0
    Ky: float = 1.0
    Kt: float = 1.0
    Cbx: float = 1.0
    Cby: float = 1.0
    Cmx: float = 1.0
    Cmy: float = 1.0
    braced_flange: int = BracedFlange.NONE
    R: float = 0.0          # bearing/rotation restraint factor
    Kf: float = 0.0         # flexural warping factor
    pdelta: bool = False

    @classmethod
    def from_length(cls, length_in: float, **overrides) -> "DesignParams":
        """Convenience: all four unbraced lengths = full member length."""
        base = dict(Lx=length_in, Ly=length_in, Lt=length_in, Lm=length_in)
        base.update(overrides)
        return cls(**base)


@dataclass
class DesignPreferences:
    """Project-wide settings — the CFS analogue of ETABS design preferences."""
    spec: int = CFSSpec.AISI_2024_USA_ASD
    progid: str = "RSG.CFS15.Calculation"   # 'RSG.CFS14.Calculation' for CFS14
    unity_limit: float = 1.0                # D/C ratio considered passing


@dataclass
class ComboCheck:
    """Result of one demand case against one section."""
    combo: str
    label: str
    forces: MemberForces
    PMxMy1: float
    PMxMy2: float
    MxVy: float
    UC: float
    status: str  # 'PASS' | 'FAIL'


@dataclass
class SectionTrial:
    """Summary of one section evaluated for a member (used in auto-select log)."""
    section: str
    governing_UC: float
    governing_combo: Optional[str]
    passed: bool


@dataclass
class MemberResult:
    """Everything the design produced for one member."""
    member_id: str
    section: Optional[str]
    passed: bool
    governing_UC: Optional[float] = None
    governing_combo: Optional[str] = None
    governing_label: Optional[str] = None
    governing_forces: Optional[MemberForces] = None
    combo_checks: List[ComboCheck] = field(default_factory=list)
    sections_tried: List[SectionTrial] = field(default_factory=list)
    message: str = ""

    def as_row(self) -> dict:
        """Flat dict for tabular export (CSV / DataFrame / JSON)."""
        f = self.governing_forces
        return {
            "member": self.member_id,
            "section": self.section,
            "status": "PASS" if self.passed else "FAIL",
            "UC": self.governing_UC,
            "combo": self.governing_combo,
            "P_k": f.P if f else None,
            "Mx_kin": f.Mx if f else None,
            "My_kin": f.My if f else None,
            "Vy_k": f.Vy if f else None,
            "message": self.message,
        }
