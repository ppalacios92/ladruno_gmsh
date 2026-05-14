"""Triangulation of OCC entities to PyVista PolyData with preserved tags."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import gmsh
import numpy as np

from ..kernel.session import session
from ..model.document import GeometryDocument
from ..model.entity import Entity


@dataclass(frozen=True)
class TessellationParameters:
    """Visual tessellator parameters.

    Values are passed to gmsh via options (``Mesh.MeshSize*``).
    """
    target_size: Optional[float] = None        # absolute target size
    size_factor: float = 1.0                   # factor over Mesh.MeshSize
    elements_per_2pi: int = 12                  # curvature
    deflection: Optional[float] = None          # sagging
    quad: bool = False                          # recombine to quads


def _has_2d_mesh() -> bool:
    """``True`` if gmsh has 2D elements registered on any surface of
    the active model."""
    try:
        for d, t in gmsh.model.getEntities(2):
            try:
                types, etags, _ = gmsh.model.mesh.getElements(d, t)
            except Exception:
                continue
            for tag_arr in etags:
                if len(tag_arr) > 0:
                    return True
        return False
    except Exception:
        return False


def tessellate(document: GeometryDocument,
               params: Optional[TessellationParameters] = None,
               *,
               force: bool = False,
               respect_user_mesh: bool = False) -> dict[str, object]:
    """Triangulate every ``dim=2`` entity of the active model.

    Returns a mapping ``entity_uuid -> pv.PolyData`` with
    ``cell_data["entity_uuid"]``, ``cell_data["dim"]``, ``cell_data["tag"]``.

    Key behavior:

    - If gmsh already has a 2D mesh registered (because the user ran a
      previous ``mesh.*`` operation), **those elements are reused**.
      This avoids destroying the FEM mesh when refreshing the scene.
    - If no mesh exists, a coarse-visual ``generate(2)`` controlled by
      :class:`TessellationParameters` is executed.
    - ``force=True`` forces ``generate(2)`` even when a previous mesh
      exists (useful for a deliberately coarse view).
    - ``respect_user_mesh=True`` **forbids** generating 2D even when
      no triangles exist. Used by the viewer after an explicit
      ``mesh.*`` (e.g. ``mesh(dim=1)``) to avoid contaminating the
      user's FEM mesh. In that case an empty dict is returned when
      there is no 2D mesh to reuse.
    """
    import pyvista as pv

    s = session()
    s.ensure()
    p = params or TessellationParameters()

    has_2d = _has_2d_mesh()
    if respect_user_mesh and not has_2d:
        return {}
    must_generate = force or (not respect_user_mesh and not has_2d)

    if must_generate:
        # Bound to the bbox so that a large model with curvature does
        # not produce an unaffordable preview mesh.
        diag = document.bbox_diagonal()
        if diag > 0:
            tmin = diag / 800.0
            tmax = diag / 20.0
            if p.target_size is not None:
                tmin = max(min(float(p.target_size), tmax), tmin)
                tmax = max(tmin, tmax)
            gmsh.option.setNumber("Mesh.MeshSizeMin", float(tmin))
            gmsh.option.setNumber("Mesh.MeshSizeMax", float(tmax))
        elif p.target_size is not None:
            gmsh.option.setNumber("Mesh.MeshSizeMin", float(p.target_size))
            gmsh.option.setNumber("Mesh.MeshSizeMax", float(p.target_size))
        gmsh.option.setNumber("Mesh.MeshSizeFactor", float(p.size_factor))
        gmsh.option.setNumber(
            "Mesh.MeshSizeFromCurvature",
            int(min(p.elements_per_2pi, 8)),
        )
        if p.deflection is not None:
            gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap",
                                  float(p.deflection))
        try:
            gmsh.model.mesh.generate(2)
        except Exception:
            return {}
        if p.quad:
            try:
                gmsh.model.mesh.recombine()
            except Exception:
                pass

    # Global node index (one call only). After a ``refine`` the
    # elements of a surface may reference nodes created on neighboring
    # entities; a global index covers that.
    try:
        global_tags, global_coords, _ = gmsh.model.mesh.getNodes()
    except Exception:
        return {}
    if len(global_tags) == 0:
        return {}
    coords_global = np.asarray(global_coords, dtype=np.float64).reshape(-1, 3)
    tag_to_global = {int(t): i for i, t in enumerate(global_tags)}

    out: dict[str, object] = {}
    entities_by_tag = {(e.dim, e.tag): e for e in document.entities}
    for d, t in gmsh.model.getEntities(2):
        ent = entities_by_tag.get((d, t))
        if ent is None:
            continue
        poly = _entity_to_polydata(d, t, ent, pv,
                                   coords_global, tag_to_global)
        if poly is not None:
            out[ent.uuid] = poly
    return out


def _entity_to_polydata(dim: int, tag: int, ent: Entity, pv,
                        coords_global, tag_to_global):
    try:
        types, _etags, ntags = gmsh.model.mesh.getElements(dim, tag)
    except Exception:
        return None
    if len(types) == 0:
        return None

    # Collect tags of nodes referenced by this entity's 2D elements.
    # They may come from any entity (refine crosses boundaries).
    used: set[int] = set()
    for element_type, node_list in zip(types, ntags):
        et = int(element_type)
        if et in (2, 3) and len(node_list) > 0:
            used.update(int(n) for n in node_list)
    if not used:
        return None

    sorted_used = sorted(used)
    local_idx: dict[int, int] = {}
    local_pts = np.empty((len(sorted_used), 3), dtype=np.float64)
    valid = 0
    for nt in sorted_used:
        g = tag_to_global.get(nt)
        if g is None:
            continue
        local_idx[nt] = valid
        local_pts[valid] = coords_global[g]
        valid += 1
    if valid == 0:
        return None
    local_pts = local_pts[:valid]

    faces: list[int] = []
    cell_count = 0
    for element_type, node_list in zip(types, ntags):
        et = int(element_type)
        if et == 2:                                     # 3-node triangle
            tris = np.asarray(node_list, dtype=np.int64).reshape(-1, 3)
            for tri in tris:
                a = local_idx.get(int(tri[0]))
                b = local_idx.get(int(tri[1]))
                c = local_idx.get(int(tri[2]))
                if a is None or b is None or c is None:
                    continue
                faces.extend([3, a, b, c])
                cell_count += 1
        elif et == 3:                                   # 4-node quad
            quads = np.asarray(node_list, dtype=np.int64).reshape(-1, 4)
            for q in quads:
                idx = [local_idx.get(int(qi)) for qi in q]
                if any(i is None for i in idx):
                    continue
                faces.extend([4, idx[0], idx[1], idx[2], idx[3]])
                cell_count += 1

    if cell_count == 0:
        return None

    poly = pv.PolyData(local_pts, faces=np.asarray(faces, dtype=np.int64))
    uuid_arr = np.full(cell_count, ent.uuid, dtype=object)
    poly.cell_data["entity_uuid"] = uuid_arr
    poly.cell_data["dim"] = np.full(cell_count, dim, dtype=np.int32)
    poly.cell_data["tag"] = np.full(cell_count, tag, dtype=np.int32)
    return poly


def stitch(tess: dict[str, object]):
    """Merge every PolyData in the mapping into one, preserving metadata."""
    import pyvista as pv
    if not tess:
        return pv.PolyData()
    merged = pv.PolyData()
    for poly in tess.values():
        merged = merged.merge(poly, merge_points=False)
    return merged
