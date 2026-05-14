"""Bridge between the domain model and PyVista/VTK."""
from .mesh_adapter import mesh_to_unstructured_grid
from .picker import (
    PickedElement,
    PickedEntity,
    picked_element_from_grid,
    picked_entity_from_polydata,
)
from .snapshot import SceneSnapshot
from .tessellator import TessellationParameters, stitch, tessellate

__all__ = [
    "TessellationParameters",
    "tessellate",
    "stitch",
    "mesh_to_unstructured_grid",
    "PickedEntity",
    "PickedElement",
    "picked_entity_from_polydata",
    "picked_element_from_grid",
    "SceneSnapshot",
]
