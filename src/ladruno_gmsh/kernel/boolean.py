"""OCC boolean operations: fuse, cut, intersect, fragment."""
from __future__ import annotations

from typing import Iterable

import gmsh

from .errors import BooleanFailed
from .session import session


DimTagPair = tuple[int, int]


def _norm(pairs: Iterable[DimTagPair]) -> list[DimTagPair]:
    return [(int(d), int(t)) for d, t in pairs]


def fuse(objects: Iterable[DimTagPair],
         tools: Iterable[DimTagPair],
         *,
         tag: int = -1,
         remove_object: bool = True,
         remove_tool: bool = True) -> tuple[list[DimTagPair], list[list[DimTagPair]]]:
    session().ensure()
    try:
        out, ovv = gmsh.model.occ.fuse(
            _norm(objects), _norm(tools),
            tag=tag, removeObject=remove_object, removeTool=remove_tool,
        )
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise BooleanFailed(f"fuse failed: {exc}") from exc
    return _norm(out), [_norm(group) for group in ovv]


def cut(objects: Iterable[DimTagPair],
        tools: Iterable[DimTagPair],
        *,
        tag: int = -1,
        remove_object: bool = True,
        remove_tool: bool = True) -> tuple[list[DimTagPair], list[list[DimTagPair]]]:
    session().ensure()
    try:
        out, ovv = gmsh.model.occ.cut(
            _norm(objects), _norm(tools),
            tag=tag, removeObject=remove_object, removeTool=remove_tool,
        )
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise BooleanFailed(f"cut failed: {exc}") from exc
    return _norm(out), [_norm(group) for group in ovv]


def intersect(objects: Iterable[DimTagPair],
              tools: Iterable[DimTagPair],
              *,
              tag: int = -1,
              remove_object: bool = True,
              remove_tool: bool = True) -> tuple[list[DimTagPair], list[list[DimTagPair]]]:
    session().ensure()
    try:
        out, ovv = gmsh.model.occ.intersect(
            _norm(objects), _norm(tools),
            tag=tag, removeObject=remove_object, removeTool=remove_tool,
        )
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise BooleanFailed(f"intersect failed: {exc}") from exc
    return _norm(out), [_norm(group) for group in ovv]


def fragment(objects: Iterable[DimTagPair],
             tools: Iterable[DimTagPair],
             *,
             tag: int = -1,
             remove_object: bool = True,
             remove_tool: bool = True) -> tuple[list[DimTagPair], list[list[DimTagPair]]]:
    """``fragment`` splits every entity into pieces with conformal
    interfaces. Key operation for preparing FEM meshing when several
    volumes touch each other."""
    session().ensure()
    objects_n = _norm(objects)
    tools_n = _norm(tools)
    if not objects_n:
        raise BooleanFailed("fragment requires at least one object entity")
    try:
        out, ovv = gmsh.model.occ.fragment(
            objects_n, tools_n,
            tag=tag, removeObject=remove_object, removeTool=remove_tool,
        )
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise BooleanFailed(f"fragment failed: {exc}") from exc
    return _norm(out), [_norm(group) for group in ovv]


def fragment_all(dim: int = 3) -> list[DimTagPair]:
    """Fragment every entity of the requested dimension against each other.

    With a single volume it does nothing. With two or more, any
    interpenetration or contact yields conformal interfaces. If
    ``dim=3`` does not have enough volumes, try ``dim=2``.
    """
    session().ensure()
    entities = [(int(d), int(t)) for d, t in gmsh.model.getEntities(dim)]
    if len(entities) < 2:
        return entities
    out, _ovv = fragment(entities[:1], entities[1:])
    return out
