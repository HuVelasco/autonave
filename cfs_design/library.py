"""
Section library: maps a logical section name (e.g. an ETABS frame-section name
like "CF10CAL14") to a CFS *section token* — either a ``.cfss`` file path or an
in-memory ``SectionGeometry`` — and provides ordered candidate lists for
auto-select optimisation.

The design engine never touches the filesystem directly; it asks a
``SectionLibrary`` for the token(s) to check.  This keeps the engine portable and
lets each application supply sections however it likes (parametric geometry,
``.cfss`` files, a directory scan, a database, …).
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional, Sequence, Tuple, Union

from .models import SectionGeometry

SectionToken = Union[str, SectionGeometry]


class SectionLibrary:
    """
    Holds a ``name -> token`` mapping and an ordered ``candidates`` list
    (lightest → heaviest) for auto-select. A direct check needs only the
    mapping; auto-select needs the ordered candidates.
    """

    def __init__(self,
                 mapping: Optional[Dict[str, SectionToken]] = None,
                 candidates: Optional[Sequence[str]] = None):
        self._map: Dict[str, SectionToken] = dict(mapping or {})
        self._candidates: List[str] = list(candidates or [])
        self._validate()

    # ── construction helpers ───────────────────────────────
    @classmethod
    def from_geometries(cls, geometries: Sequence[SectionGeometry],
                        candidates: Optional[Sequence[str]] = None
                        ) -> "SectionLibrary":
        """Build a library from parametric sections (no .cfss files).
        Candidate order defaults to the given sequence order."""
        mapping = {g.name: g for g in geometries}
        if candidates is None:
            candidates = [g.name for g in geometries]
        return cls(mapping=mapping, candidates=candidates)

    @classmethod
    def from_directory(cls, directory: str,
                       ordered_names: Optional[Sequence[str]] = None
                       ) -> "SectionLibrary":
        """Scan a folder of ``.cfss`` files. ``name`` = filename without ext.
        Supply ``ordered_names`` for a real (by-weight) auto-select order."""
        mapping: Dict[str, SectionToken] = {}
        for fn in os.listdir(directory):
            if fn.lower().endswith(".cfss"):
                mapping[os.path.splitext(fn)[0]] = os.path.join(directory, fn)
        if ordered_names is None:
            ordered_names = sorted(mapping)
        return cls(mapping=mapping, candidates=ordered_names)

    # ── lookups ────────────────────────────────────────────
    def token(self, name: str) -> SectionToken:
        """Section token (.cfss path or SectionGeometry) for a name."""
        try:
            return self._map[name]
        except KeyError:
            raise KeyError(f"No section mapped for '{name}'. "
                           f"Known: {sorted(self._map)}")

    def has(self, name: str) -> bool:
        return name in self._map

    def candidate_pairs(self, subset: Optional[Sequence[str]] = None
                        ) -> List[Tuple[str, SectionToken]]:
        """Ordered ``(name, token)`` list for auto-select. ``subset`` limits to
        (and preserves library order of) the given names."""
        names = self._candidates or list(self._map)
        if subset is not None:
            allow = set(subset)
            names = [n for n in names if n in allow]
        return [(n, self._map[n]) for n in names]

    # ── validation ─────────────────────────────────────────
    def _validate(self):
        missing = [n for n, tok in self._map.items()
                   if isinstance(tok, str) and not os.path.isfile(tok)]
        if missing:
            raise FileNotFoundError(
                "Missing .cfss files for: "
                + ", ".join(f"{n} -> {self._map[n]}" for n in missing))
        unknown = [n for n in self._candidates if n not in self._map]
        if unknown:
            raise KeyError(f"Candidate names not in mapping: {unknown}")
