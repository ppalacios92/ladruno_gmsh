"""Two-way picking mapping VTK <-> DimTag/ElementTag."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class PickedEntity:
    entity_uuid: str
    dim: int
    tag: int


@dataclass(frozen=True)
class PickedElement:
    element_tag: int
    gmsh_type: int
    dim: int


def picked_entity_from_polydata(poly, cell_id: int) -> Optional[PickedEntity]:
    """Extract the entity associated with a cell in a tessellated PolyData."""
    if cell_id < 0:
        return None
    try:
        uuid = str(poly.cell_data["entity_uuid"][cell_id])
        dim = int(poly.cell_data["dim"][cell_id])
        tag = int(poly.cell_data["tag"][cell_id])
    except Exception:
        return None
    return PickedEntity(entity_uuid=uuid, dim=dim, tag=tag)


def picked_element_from_grid(grid, cell_id: int) -> Optional[PickedElement]:
    """Extract the mesh element associated with a cell in an
    UnstructuredGrid produced by :mod:`bridge.mesh_adapter`."""
    if cell_id < 0:
        return None
    try:
        etag = int(grid.cell_data["element_tag"][cell_id])
        etype = int(grid.cell_data["gmsh_type"][cell_id])
        dim = int(grid.cell_data["dim"][cell_id])
    except Exception:
        return None
    return PickedElement(element_tag=etag, gmsh_type=etype, dim=dim)
