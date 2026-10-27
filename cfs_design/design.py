"""
The design workflow — source-agnostic.

Given demands (already in CFS conventions), per-member design params, a section
library and preferences, this runs CFS MemberCheck and produces MemberResults.
It mirrors the ETABS steel-design flow:

    check_member   -> D/C for one member on one fixed section (all combos)
    design_member  -> auto-select: lightest candidate that passes
    DesignRunner   -> batch over many members, with one shared CFS license

No ETABS, no win32com here beyond the injected CFSEngine.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .engine import CFSEngine
from .models import (ComboCheck, DemandCase, DesignParams, DesignPreferences,
                     MemberForces, MemberResult, SectionTrial)


def _check_one_section(engine: CFSEngine, section_token,
                       demands: Sequence[DemandCase], params: DesignParams,
                       prefs: DesignPreferences
                       ) -> Tuple[float, Optional[ComboCheck], List[ComboCheck]]:
    """Run every demand case against one section. ``section_token`` is a .cfss
    path or a SectionGeometry. Returns (governing_UC, governing_ComboCheck,
    all ComboChecks)."""
    checks: List[ComboCheck] = []
    gov_uc = 0.0
    gov: Optional[ComboCheck] = None
    limit = prefs.unity_limit

    for d in demands:
        uc, p1, p2, mxvy = engine.member_check(section_token, params,
                                               d.forces, prefs.spec)
        cc = ComboCheck(
            combo=d.combo, label=d.label, forces=d.forces,
            PMxMy1=round(p1, 4), PMxMy2=round(p2, 4), MxVy=round(mxvy, 4),
            UC=round(uc, 4), status="PASS" if uc <= limit else "FAIL",
        )
        checks.append(cc)
        if uc > gov_uc:
            gov_uc, gov = uc, cc
    return gov_uc, gov, checks


def check_member(engine: CFSEngine, member_id: str, section_name: str,
                 section_token, demands: Sequence[DemandCase],
                 params: DesignParams, prefs: DesignPreferences) -> MemberResult:
    """Check ONE member on ONE given section (no auto-select).
    ``section_token`` is a .cfss path or a SectionGeometry."""
    if not demands:
        return MemberResult(member_id, section_name, passed=True,
                            message="No demands supplied.")
    gov_uc, gov, checks = _check_one_section(
        engine, section_token, demands, params, prefs)
    passed = gov_uc <= prefs.unity_limit
    return MemberResult(
        member_id=member_id, section=section_name, passed=passed,
        governing_UC=round(gov_uc, 4),
        governing_combo=gov.combo if gov else None,
        governing_label=gov.label if gov else None,
        governing_forces=gov.forces if gov else None,
        combo_checks=checks,
        sections_tried=[SectionTrial(section_name, round(gov_uc, 4),
                                     gov.combo if gov else None, passed)],
    )


def design_member(engine: CFSEngine, member_id: str,
                  candidates: Sequence[Tuple[str, str]],
                  demands: Sequence[DemandCase], params: DesignParams,
                  prefs: DesignPreferences) -> MemberResult:
    """Auto-select: try candidates (lightest→heaviest), return first that passes.
    ``candidates`` = ordered list of (section_name, .cfss path)."""
    if not candidates:
        return MemberResult(member_id, None, passed=False,
                            message="No candidate sections supplied.")
    if not demands:
        return MemberResult(member_id, candidates[0][0], passed=True,
                            message="No demands supplied.")

    tried: List[SectionTrial] = []
    last_checks: List[ComboCheck] = []
    for name, token in candidates:
        gov_uc, gov, checks = _check_one_section(
            engine, token, demands, params, prefs)
        passed = gov_uc <= prefs.unity_limit
        tried.append(SectionTrial(name, round(gov_uc, 4),
                                  gov.combo if gov else None, passed))
        last_checks = checks
        if passed:
            return MemberResult(
                member_id=member_id, section=name, passed=True,
                governing_UC=round(gov_uc, 4),
                governing_combo=gov.combo, governing_label=gov.label,
                governing_forces=gov.forces, combo_checks=checks,
                sections_tried=tried,
            )

    # Nothing passed — report the heaviest (last) attempt's detail.
    worst = tried[-1]
    return MemberResult(
        member_id=member_id, section=None, passed=False,
        governing_UC=worst.governing_UC, governing_combo=worst.governing_combo,
        combo_checks=last_checks, sections_tried=tried,
        message="No candidate section passes; increase size or reduce loads.",
    )


class MemberDesignTask:
    """One unit of work for the batch runner."""
    __slots__ = ("member_id", "demands", "params", "candidates", "fixed_section")

    def __init__(self, member_id: str, demands: Sequence[DemandCase],
                 params: DesignParams,
                 candidates: Optional[Sequence[Tuple[str, str]]] = None,
                 fixed_section: Optional[Tuple[str, str]] = None):
        """Provide EITHER ``candidates`` (auto-select) OR ``fixed_section``
        (name, path) for a straight check."""
        if not candidates and not fixed_section:
            raise ValueError("Give candidates or fixed_section.")
        self.member_id = member_id
        self.demands = demands
        self.params = params
        self.candidates = candidates
        self.fixed_section = fixed_section


class DesignRunner:
    """Batch driver — opens one CFS license for the whole run."""

    def __init__(self, prefs: DesignPreferences):
        self.prefs = prefs

    def run(self, tasks: Sequence[MemberDesignTask]) -> List[MemberResult]:
        results: List[MemberResult] = []
        with CFSEngine(self.prefs.progid, self.prefs.spec) as engine:
            for t in tasks:
                if t.candidates:
                    r = design_member(engine, t.member_id, t.candidates,
                                      t.demands, t.params, self.prefs)
                else:
                    name, path = t.fixed_section
                    r = check_member(engine, t.member_id, name, path,
                                    t.demands, t.params, self.prefs)
                results.append(r)
        return results
