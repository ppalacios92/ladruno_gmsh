"""B-Rep healing: healShapes, removeAllDuplicates, sewing."""
from __future__ import annotations

from typing import Iterable, Optional

import gmsh

from .errors import HealingIncomplete
from .session import session


DimTagPair = tuple[int, int]


def heal(*,
         tolerance: float,
         dim_tags: Optional[Iterable[DimTagPair]] = None,
         fix_degenerated: bool = True,
         fix_small_edges: bool = True,
         fix_small_faces: bool = True,
         sew_faces: bool = True,
         make_solids: bool = True) -> list[DimTagPair]:
    """Wrapper around ``model.occ.healShapes``.

    Returns the resulting dim_tags after healing.
    """
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    try:
        out = gmsh.model.occ.healShapes(
            dimTags=arg,
            tolerance=float(tolerance),
            fixDegenerated=fix_degenerated,
            fixSmallEdges=fix_small_edges,
            fixSmallFaces=fix_small_faces,
            sewFaces=sew_faces,
            makeSolids=make_solids,
        )
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise HealingIncomplete(f"healShapes failed: {exc}") from exc
    return [(int(d), int(t)) for d, t in out]


def remove_all_duplicates() -> None:
    """Consolidate geometrically duplicated entities after fragmenting
    volumes (shared interfaces)."""
    session().ensure()
    try:
        gmsh.model.occ.removeAllDuplicates()
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise HealingIncomplete(f"removeAllDuplicates failed: {exc}") from exc


def convert_to_nurbs(dim_tags: Iterable[DimTagPair]) -> None:
    session().ensure()
    pairs = [(int(d), int(t)) for d, t in dim_tags]
    try:
        gmsh.model.occ.convertToNURBS(pairs)
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise HealingIncomplete(f"convertToNURBS failed: {exc}") from exc
