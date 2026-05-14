"""Conversion of gmsh mesh to pyvista.UnstructuredGrid."""
from __future__ import annotations

from typing import Optional

import gmsh
import numpy as np

from ..kernel.session import session


# Map gmsh element type -> VTK cell type. Only linear first order.
# Higher-order types are degraded to their primary cell for display.
_GMSH_TO_VTK = {
    1: (3, 2),       # 2-node line          -> VTK_LINE
    2: (5, 3),       # 3-node triangle      -> VTK_TRIANGLE
    3: (9, 4),       # 4-node quad          -> VTK_QUAD
    4: (10, 4),      # 4-node tetra         -> VTK_TETRA
    5: (12, 8),      # 8-node hex           -> VTK_HEXAHEDRON
    6: (13, 6),      # 6-node prism         -> VTK_WEDGE
    7: (14, 5),      # 5-node pyramid       -> VTK_PYRAMID
    8: (3, 2),       # 3-node line   (order2 visual: ignore mids) -> LINE
    9: (5, 3),       # 6-node triangle      -> TRIANGLE (degraded)
    10: (9, 4),      # 9-node quad          -> QUAD (degraded)
    11: (10, 4),     # 10-node tetra        -> TETRA (degraded)
    12: (12, 8),     # 27-node hex          -> HEX
    13: (13, 6),     # 18-node prism        -> WEDGE
    14: (14, 5),     # 14-node pyramid      -> PYRAMID
    15: (1, 1),      # 1-node point         -> VTK_VERTEX
}


def mesh_to_unstructured_grid(*, with_quality: Optional[str] = None):
    """Build a :class:`pyvista.UnstructuredGrid` from the current mesh
    of the gmsh model.

    If ``with_quality`` is a valid metric (e.g. ``"minSICN"``), it is
    included as ``cell_data["quality"]``.
    """
    import pyvista as pv
    import vtk

    session().ensure()

    node_tags, node_coord, _ = gmsh.model.mesh.getNodes(-1, -1, True, False)
    if len(node_tags) == 0:
        return pv.UnstructuredGrid()

    coords = np.asarray(node_coord, dtype=np.float64).reshape(-1, 3)
    tag_to_index = {int(t): i for i, t in enumerate(node_tags)}

    cells: list[int] = []
    cell_types: list[int] = []
    element_tags_flat: list[int] = []
    element_dims: list[int] = []
    element_types_flat: list[int] = []

    types, e_tags, n_tags = gmsh.model.mesh.getElements()
    for etype, tags, nodes in zip(types, e_tags, n_tags):
        if etype not in _GMSH_TO_VTK or tags.size == 0:
            continue
        vtk_type, n_per_cell_vtk = _GMSH_TO_VTK[etype]
        try:
            props = gmsh.model.mesh.getElementProperties(int(etype))
            n_per_cell_gmsh = int(props[3])
            dim = int(props[1])
        except Exception:
            continue
        node_matrix = np.asarray(nodes, dtype=np.int64).reshape(-1, n_per_cell_gmsh)
        primary = node_matrix[:, :n_per_cell_vtk]
        for row, etag in zip(primary, tags.tolist()):
            cells.append(n_per_cell_vtk)
            for nt in row:
                cells.append(tag_to_index[int(nt)])
            cell_types.append(vtk_type)
            element_tags_flat.append(int(etag))
            element_dims.append(dim)
            element_types_flat.append(int(etype))

    if not cell_types:
        return pv.UnstructuredGrid()

    grid = pv.UnstructuredGrid(
        np.asarray(cells, dtype=np.int64),
        np.asarray(cell_types, dtype=np.uint8),
        coords,
    )
    grid.cell_data["element_tag"] = np.asarray(element_tags_flat,
                                               dtype=np.int64)
    grid.cell_data["dim"] = np.asarray(element_dims, dtype=np.int8)
    grid.cell_data["gmsh_type"] = np.asarray(element_types_flat,
                                             dtype=np.int32)

    if with_quality:
        from ..kernel import quality as _q
        try:
            q = _q.element_qualities(element_tags_flat, metric=with_quality)
            grid.cell_data[f"quality_{with_quality}"] = q
        except Exception:
            pass

    return grid
