"""Internal free edges and non-manifold configurations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from ..kernel import connectivity as _conn


@dataclass(frozen=True)
class ManifoldnessResult:
    free_edges_count: int = 0
    free_edges: tuple[tuple[int, int], ...] = ()
    non_manifold_edges_count: int = 0
    non_manifold_edges: tuple[tuple[int, int], ...] = ()
    inspected_element_types: tuple[int, ...] = ()

    @property
    def ok(self) -> bool:
        return self.free_edges_count == 0 and self.non_manifold_edges_count == 0


def _normalize_edge(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def check(*, surface_dim: int = 2,
          element_types: Iterable[int] | None = None,
          max_report: int = 1000) -> ManifoldnessResult:
    """Detect edges with a single adjacent element (free) and edges
    with more than two (non-manifold), evaluated over the model's
    surface elements.

    A closed, conformal mesh over a volume's boundary has zero free
    edges and zero non-manifold ones.
    """
    elements = _conn.get_elements(dim=surface_dim)
    target_types = (set(int(t) for t in element_types)
                    if element_types is not None
                    else set(elements.types))

    edge_count: dict[tuple[int, int], int] = {}
    inspected: list[int] = []
    for etype, node_array in zip(elements.types, elements.node_tags):
        if etype not in target_types or node_array.size == 0:
            continue
        try:
            props = _conn.get_element_properties(int(etype))
        except Exception:
            continue
        nn = int(props["num_primary_nodes"])
        if nn < 3 or props["dim"] != 2:
            continue
        inspected.append(int(etype))
        nodes = node_array.reshape(-1, props["num_nodes"])
        primary = nodes[:, :nn]
        for face in primary:
            for k in range(nn):
                a = int(face[k])
                b = int(face[(k + 1) % nn])
                key = _normalize_edge(a, b)
                edge_count[key] = edge_count.get(key, 0) + 1

    free: list[tuple[int, int]] = []
    nonmf: list[tuple[int, int]] = []
    for edge, n in edge_count.items():
        if n == 1:
            free.append(edge)
        elif n > 2:
            nonmf.append(edge)

    return ManifoldnessResult(
        free_edges_count=len(free),
        free_edges=tuple(free[:max_report]),
        non_manifold_edges_count=len(nonmf),
        non_manifold_edges=tuple(nonmf[:max_report]),
        inspected_element_types=tuple(inspected),
    )
