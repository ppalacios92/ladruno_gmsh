"""MeshSnapshot: immutable view of nodes, elements and metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class MeshSnapshot:
    n_nodes: int = 0
    n_elements: int = 0
    elements_by_type: Mapping[str, int] = field(default_factory=dict)
    max_dim: int = 0
    order: int = 1

    @classmethod
    def empty(cls) -> "MeshSnapshot":
        return cls()

    @property
    def is_empty(self) -> bool:
        return self.n_nodes == 0 and self.n_elements == 0
