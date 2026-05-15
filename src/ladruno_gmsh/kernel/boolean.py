"""OCC boolean operations: fuse, cut, intersect, fragment."""
from __future__ import annotations

from typing import Iterable, Optional

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


# ── Derived / composed boolean operations ───────────────────────────


def imprint(objects: Iterable[DimTagPair],
            tools: Iterable[DimTagPair]
            ) -> tuple[list[DimTagPair], list[list[DimTagPair]]]:
    """Mark shared interfaces between ``objects`` and ``tools`` without
    deleting either side.

    Implemented as ``fragment(..., removeObject=False, removeTool=False)``:
    gmsh creates conformal interfaces (so meshing later produces matching
    faces / nodes across the boundary) but keeps both original entities
    alive. The canonical use case is tie / cohesive contact in FEM, where
    two volumes must share a face without one cutting the other.
    """
    return fragment(objects, tools, remove_object=False, remove_tool=False)


def self_intersect(objects: Iterable[DimTagPair]
                   ) -> tuple[list[DimTagPair], list[list[DimTagPair]]]:
    """Resolve self-intersections inside ``objects``.

    Implemented as ``fragment(objects, [])``: gmsh detects any
    interpenetration inside the input set and re-emits clean,
    non-overlapping pieces. Useful after imports of poorly modeled
    geometry where a single solid auto-intersects.
    """
    return fragment(objects, [], remove_object=True, remove_tool=True)


def xor(objects: Iterable[DimTagPair],
        tools: Iterable[DimTagPair]
        ) -> list[DimTagPair]:
    """Symmetric difference: ``(A ∪ B) \\ (A ∩ B)``.

    Built as three OCC calls, with copies on the inputs so the user-side
    entities survive: union and intersection are computed against copies,
    then ``cut`` removes the intersection from the union. The originals
    are removed at the end so the document only holds the XOR piece.

    Returns the list of dim-tags produced by the final ``cut``.
    """
    session().ensure()
    objs = _norm(objects)
    tls = _norm(tools)
    if not objs or not tls:
        raise BooleanFailed("xor requires non-empty objects and tools")
    try:
        objs_u = gmsh.model.occ.copy(objs)
        tls_u = gmsh.model.occ.copy(tls)
        union, _ = gmsh.model.occ.fuse(
            objs_u, tls_u, removeObject=True, removeTool=True,
        )
        objs_i = gmsh.model.occ.copy(objs)
        tls_i = gmsh.model.occ.copy(tls)
        inter, _ = gmsh.model.occ.intersect(
            objs_i, tls_i, removeObject=True, removeTool=True,
        )
        out, _ = gmsh.model.occ.cut(
            union, inter, removeObject=True, removeTool=True,
        )
        # Now remove the user-side originals so the model only contains
        # the XOR piece.
        if objs or tls:
            gmsh.model.occ.remove(objs + tls, recursive=True)
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise BooleanFailed(f"xor failed: {exc}") from exc
    return _norm(out)


def section(volume_dim_tags: Iterable[DimTagPair],
            *,
            point: tuple[float, float, float],
            normal: tuple[float, float, float],
            extent: Optional[float] = None
            ) -> list[DimTagPair]:
    """Cut a set of volumes with an infinite plane and return the cross
    section as a set of 2D surface dim-tags.

    The plane is materialized as a finite rectangle large enough to cross
    every bounding box (``extent`` overrides the auto size). The
    rectangle is then intersected with the volumes (without consuming
    them) and removed afterwards so only the cut surfaces remain.

    Useful for diagnostics (visualize the interior of a model), CFD
    inlet / outlet construction, and post-processing.
    """
    import numpy as np

    session().ensure()
    vols = _norm(volume_dim_tags)
    if not vols:
        raise BooleanFailed("section requires at least one volume")

    # Auto-size: 4x the largest bbox diagonal of the inputs.
    if extent is None:
        bbox_all = None
        for d, t in vols:
            try:
                xmin, ymin, zmin, xmax, ymax, zmax = (
                    gmsh.model.occ.getBoundingBox(d, t)
                )
            except Exception:
                continue
            if bbox_all is None:
                bbox_all = [xmin, ymin, zmin, xmax, ymax, zmax]
            else:
                bbox_all[0] = min(bbox_all[0], xmin)
                bbox_all[1] = min(bbox_all[1], ymin)
                bbox_all[2] = min(bbox_all[2], zmin)
                bbox_all[3] = max(bbox_all[3], xmax)
                bbox_all[4] = max(bbox_all[4], ymax)
                bbox_all[5] = max(bbox_all[5], zmax)
        if bbox_all is None:
            extent = 1.0
        else:
            diag = float(np.linalg.norm([
                bbox_all[3] - bbox_all[0],
                bbox_all[4] - bbox_all[1],
                bbox_all[5] - bbox_all[2],
            ]))
            extent = max(diag * 4.0, 1.0)

    try:
        # Build the cutting plane: a disk centered at ``point`` with
        # ``normal`` as its axis. ``addDisk`` takes the plane normal as
        # the optional ``zAxis`` argument.
        n = np.array(normal, dtype=float)
        n_norm = np.linalg.norm(n)
        if n_norm <= 0:
            raise BooleanFailed("section normal must be non-zero")
        n = n / n_norm
        disk_tag = gmsh.model.occ.addDisk(
            float(point[0]), float(point[1]), float(point[2]),
            float(extent), float(extent),
            zAxis=(float(n[0]), float(n[1]), float(n[2])),
        )
        gmsh.model.occ.synchronize()

        # Intersect volumes against the disk; keep volumes, consume disk.
        out, _ = gmsh.model.occ.intersect(
            vols, [(2, disk_tag)],
            removeObject=False, removeTool=True,
        )
        gmsh.model.occ.synchronize()
    except Exception as exc:
        raise BooleanFailed(f"section failed: {exc}") from exc
    return _norm(out)


def hollow(volume_dim_tags: Iterable[DimTagPair],
           *,
           thickness: float,
           open_face_dim_tags: Iterable[DimTagPair] = ()
           ) -> list[DimTagPair]:
    """Build a thick-shell version of each input volume.

    Wraps ``model.occ.addThickSolid``: every input volume is replaced by
    a hollow shell of the given ``thickness`` (signed: negative ⇒ inward
    offset, positive ⇒ outward). Faces listed in ``open_face_dim_tags``
    are removed from the resulting shell, leaving openings.

    Strictly a CAD modifier, not a boolean — but users coming from
    SolidWorks / Inventor expect to find it in the boolean menu.
    """
    session().ensure()
    vols = _norm(volume_dim_tags)
    if not vols:
        raise BooleanFailed("hollow requires at least one volume")
    open_faces = _norm(open_face_dim_tags)

    produced: list[DimTagPair] = []
    try:
        for dim, tag in vols:
            if dim != 3:
                raise BooleanFailed(
                    f"hollow only operates on volumes (dim=3), got dim={dim}"
                )
            excluded = [t for d, t in open_faces if d == 2]
            new = gmsh.model.occ.addThickSolid(
                volumeTag=int(tag),
                excludeSurfaceTags=excluded,
                offset=float(thickness),
            )
            # gmsh.addThickSolid changed return type across versions:
            # older builds return a single int tag, newer ones return
            # a list of (dim, tag) pairs. Normalize both shapes.
            if isinstance(new, int):
                produced.append((3, int(new)))
            elif isinstance(new, (list, tuple)):
                for item in new:
                    if (isinstance(item, (list, tuple))
                            and len(item) == 2):
                        produced.append((int(item[0]), int(item[1])))
                    else:
                        produced.append((3, int(item)))
            else:
                raise BooleanFailed(
                    f"unexpected addThickSolid return type: {type(new)}"
                )
        gmsh.model.occ.synchronize()
    except BooleanFailed:
        raise
    except Exception as exc:
        raise BooleanFailed(f"hollow failed: {exc}") from exc
    return produced
