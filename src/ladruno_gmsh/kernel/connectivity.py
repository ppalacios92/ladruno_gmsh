"""Nodal and element connectivity: nodes, edges, faces, duplicates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import gmsh
import numpy as np

from .errors import MeshFailed
from .session import session


DimTagPair = tuple[int, int]


@dataclass(frozen=True)
class NodeBundle:
    """Set of nodes returned by ``getNodes``."""
    tags: np.ndarray              # int64 (N,)
    coords: np.ndarray            # float64 (N, 3)

    @property
    def count(self) -> int:
        return int(self.tags.size)


@dataclass(frozen=True)
class ElementBundle:
    """Elements grouped by type, flat layout for analytic use."""
    types: tuple[int, ...]
    tags: tuple[np.ndarray, ...]              # per type
    node_tags: tuple[np.ndarray, ...]         # per type, flattened

    @property
    def total_count(self) -> int:
        return int(sum(t.size for t in self.tags))


def get_nodes(dim: int = -1, tag: int = -1,
              include_boundary: bool = False) -> NodeBundle:
    session().ensure()
    try:
        node_tags, coords, _params = gmsh.model.mesh.getNodes(
            int(dim), int(tag), include_boundary, False,
        )
    except Exception as exc:
        raise MeshFailed(f"getNodes failed: {exc}") from exc
    tags_arr = np.asarray(node_tags, dtype=np.int64)
    coords_arr = np.asarray(coords, dtype=np.float64).reshape(-1, 3)
    return NodeBundle(tags=tags_arr, coords=coords_arr)


def get_elements(dim: int = -1, tag: int = -1) -> ElementBundle:
    session().ensure()
    try:
        types, tags, node_tags = gmsh.model.mesh.getElements(int(dim), int(tag))
    except Exception as exc:
        raise MeshFailed(f"getElements failed: {exc}") from exc
    return ElementBundle(
        types=tuple(int(t) for t in types),
        tags=tuple(np.asarray(t, dtype=np.int64) for t in tags),
        node_tags=tuple(np.asarray(n, dtype=np.int64) for n in node_tags),
    )


def get_element_properties(element_type: int) -> dict:
    session().ensure()
    name, dim, order, num_nodes, local_coords, num_prim_nodes = (
        gmsh.model.mesh.getElementProperties(int(element_type))
    )
    return {
        "name": name,
        "dim": int(dim),
        "order": int(order),
        "num_nodes": int(num_nodes),
        "num_primary_nodes": int(num_prim_nodes),
    }


def get_duplicate_nodes(dim_tags: Optional[Iterable[DimTagPair]] = None
                        ) -> list[int]:
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    try:
        out = gmsh.model.mesh.getDuplicateNodes(arg)
    except Exception:
        return []
    return [int(n) for n in out]


def remove_duplicate_nodes(dim_tags: Optional[Iterable[DimTagPair]] = None
                           ) -> None:
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    gmsh.model.mesh.removeDuplicateNodes(arg)


def remove_duplicate_elements(dim_tags: Optional[Iterable[DimTagPair]] = None
                              ) -> None:
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    gmsh.model.mesh.removeDuplicateElements(arg)


def rebuild_caches() -> None:
    session().ensure()
    gmsh.model.mesh.rebuildNodeCache(False)
    gmsh.model.mesh.rebuildElementCache(False)


def get_element_face_nodes(element_type: int, face_type: int = 3
                           ) -> np.ndarray:
    """Return the per-face nodes of each element of the given type.

    ``face_type`` is ``3`` for triangles, ``4`` for quadrangles.
    """
    session().ensure()
    raw = gmsh.model.mesh.getElementFaceNodes(int(element_type),
                                              int(face_type))
    return np.asarray(raw, dtype=np.int64).reshape(-1, int(face_type))


def get_element_edge_nodes(element_type: int) -> np.ndarray:
    session().ensure()
    raw = gmsh.model.mesh.getElementEdgeNodes(int(element_type))
    return np.asarray(raw, dtype=np.int64).reshape(-1, 2)
