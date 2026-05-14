"""Geometric queries: entities, boundary, bbox, mass, adjacency."""
from __future__ import annotations

from typing import Optional

import gmsh

from ..utils.numeric import BBox
from .errors import EntityNotFound
from .session import session


_DIM_KIND = {0: "point", 1: "curve", 2: "surface", 3: "volume"}


def list_entities(dim: int = -1) -> list[tuple[int, int]]:
    session().ensure()
    return [(int(d), int(t)) for d, t in gmsh.model.getEntities(dim)]


def entity_name(dim: int, tag: int) -> str:
    session().ensure()
    try:
        return gmsh.model.getEntityName(dim, tag) or ""
    except Exception:
        return ""


def bbox(dim: int, tag: int) -> Optional[BBox]:
    """Return the entity's bbox or ``None`` if no backend produces a
    finite value (open or badly parameterized surfaces). Prefers
    ``model.occ.getBoundingBox`` when available because it respects the
    trim curves of trimmed surfaces."""
    session().ensure()
    candidate: Optional[BBox] = None
    try:
        values = gmsh.model.occ.getBoundingBox(dim, tag)
        candidate = BBox.from_tuple(values)
        if candidate.is_finite:
            return candidate
    except Exception:
        candidate = None
    try:
        values = gmsh.model.getBoundingBox(dim, tag)
    except Exception as exc:
        if candidate is not None:
            return candidate
        raise EntityNotFound(f"Entity ({dim}, {tag}) not found") from exc
    fallback = BBox.from_tuple(values)
    if fallback.is_finite:
        return fallback
    return candidate if (candidate is not None and candidate.is_finite) else None


def global_bbox() -> Optional[BBox]:
    session().ensure()
    entities = list_entities(-1)
    boxes: list[BBox] = []
    for d, t in entities:
        try:
            b = bbox(d, t)
        except EntityNotFound:
            continue
        if b is not None and b.is_finite:
            boxes.append(b)
    return BBox.union(boxes)


def mass(dim: int, tag: int) -> Optional[float]:
    """Return the entity's natural measure.

    In gmsh convention: volume for ``dim=3``, area for ``dim=2``,
    length for ``dim=1``. ``None`` when the query does not apply
    (discrete entities without parametrization, for example).
    """
    if dim not in (1, 2, 3):
        return None
    session().ensure()
    try:
        return float(gmsh.model.occ.getMass(dim, tag))
    except Exception:
        return None


def center_of_mass(dim: int, tag: int) -> Optional[tuple[float, float, float]]:
    if dim not in (1, 2, 3):
        return None
    session().ensure()
    try:
        x, y, z = gmsh.model.occ.getCenterOfMass(dim, tag)
        return (float(x), float(y), float(z))
    except Exception:
        return None


def boundary(dim_tags: list[tuple[int, int]],
             *,
             combined: bool = True,
             oriented: bool = False,
             recursive: bool = False) -> list[tuple[int, int]]:
    session().ensure()
    result = gmsh.model.getBoundary(
        dim_tags, combined=combined, oriented=oriented, recursive=recursive
    )
    return [(int(d), int(t)) for d, t in result]


def adjacencies(dim: int, tag: int) -> tuple[list[int], list[int]]:
    """Return (upward, downward) as tags."""
    session().ensure()
    up, down = gmsh.model.getAdjacencies(dim, tag)
    return [int(t) for t in up], [int(t) for t in down]


def is_orphan(dim: int, tag: int) -> bool:
    session().ensure()
    try:
        return bool(gmsh.model.isEntityOrphan(dim, tag))
    except Exception:
        return False


def kind_for_dim(dim: int) -> str:
    return _DIM_KIND.get(dim, "unknown")


def remove(dim_tags, *, recursive: bool = True) -> None:
    """Remove OCC entities from the active model."""
    session().ensure()
    pairs = [(int(d), int(t)) for d, t in dim_tags]
    if not pairs:
        return
    try:
        gmsh.model.occ.remove(pairs, recursive=recursive)
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise EntityNotFound(f"remove failed: {exc}") from exc
