"""Element and normal reorientation: reverse, setOutwardOrientation."""
from __future__ import annotations

from typing import Iterable, Optional

import gmsh

from .errors import MeshFailed
from .session import session


DimTagPair = tuple[int, int]


def reverse(dim_tags: Iterable[DimTagPair]) -> None:
    """Flip the orientation of 2D or 1D entities (affects normals or
    tangents)."""
    session().ensure()
    pairs = [(int(d), int(t)) for d, t in dim_tags]
    try:
        gmsh.model.mesh.reverse(pairs)
    except Exception as exc:
        raise MeshFailed(f"reverse failed: {exc}") from exc


def reverse_elements(element_tags: Iterable[int]) -> None:
    session().ensure()
    tags = [int(t) for t in element_tags]
    try:
        gmsh.model.mesh.reverseElements(tags)
    except Exception as exc:
        raise MeshFailed(f"reverseElements failed: {exc}") from exc


def set_outward(volume_tag: int) -> None:
    """Force the volume's faces to point outward."""
    session().ensure()
    try:
        gmsh.model.mesh.setOutwardOrientation(int(volume_tag))
    except Exception as exc:
        raise MeshFailed(f"setOutwardOrientation failed: {exc}") from exc


def reclassify_nodes() -> None:
    session().ensure()
    try:
        gmsh.model.mesh.reclassifyNodes()
    except Exception as exc:
        raise MeshFailed(f"reclassifyNodes failed: {exc}") from exc


def relocate_nodes(dim: int = -1, tag: int = -1) -> None:
    session().ensure()
    try:
        gmsh.model.mesh.relocateNodes(int(dim), int(tag))
    except Exception as exc:
        raise MeshFailed(f"relocateNodes failed: {exc}") from exc


def renumber_nodes() -> None:
    session().ensure()
    gmsh.model.mesh.renumberNodes()


def renumber_elements() -> None:
    session().ensure()
    gmsh.model.mesh.renumberElements()


def compute_renumbering(method: str = "RCMK",
                        element_tags: Optional[Iterable[int]] = None
                        ) -> tuple[list[int], list[int]]:
    """``method`` accepts ``"RCMK"``, ``"Hilbert"``, ``"Boundary"``.

    Returns ``(old_tags, new_tags)`` that can be passed to
    :func:`renumber_nodes_explicit` to apply the result.
    """
    session().ensure()
    arg = [] if element_tags is None else [int(t) for t in element_tags]
    old, new = gmsh.model.mesh.computeRenumbering(method, arg)
    return [int(x) for x in old], [int(x) for x in new]
