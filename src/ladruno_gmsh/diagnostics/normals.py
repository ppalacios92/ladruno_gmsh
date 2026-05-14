"""Orientation consistency of normals and tangents."""
from __future__ import annotations

from dataclasses import dataclass

import gmsh

from ..kernel.session import session


@dataclass(frozen=True)
class NormalsResult:
    inverted_surfaces: tuple[int, ...] = ()
    inspected: int = 0
    note: str = ""

    @property
    def ok(self) -> bool:
        return not self.inverted_surfaces


def check() -> NormalsResult:
    """Identify surfaces likely to be inverted relative to their
    containing volume.

    Practical FEM criterion: if volume ``v``'s boundary, obtained with
    ``getBoundary(..., oriented=True)``, contains a surface with a
    negative tag (opposite orientation), it is reported. This does not
    prove the surface is "wrong" in absolute terms, but signals
    inconsistency against the containing volume.
    """
    session().ensure()
    inverted: list[int] = []
    inspected = 0
    for dv, tv in gmsh.model.getEntities(3):
        try:
            bnd = gmsh.model.getBoundary([(dv, tv)],
                                         combined=True,
                                         oriented=True,
                                         recursive=False)
        except Exception:
            continue
        for d, t in bnd:
            inspected += 1
            if int(t) < 0:
                inverted.append(int(abs(t)))

    if not inspected:
        return NormalsResult(
            note="No volumes; surface orientation is not evaluated."
        )

    return NormalsResult(
        inverted_surfaces=tuple(sorted(set(inverted))),
        inspected=inspected,
    )
