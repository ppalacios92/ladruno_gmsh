"""Detection of duplicate nodes and elements."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from scipy.spatial import cKDTree

from ..kernel import connectivity as _conn


@dataclass(frozen=True)
class DuplicatesResult:
    duplicate_node_tags_gmsh: tuple[int, ...] = ()
    coincident_pairs: tuple[tuple[int, int], ...] = ()
    tolerance: float = 0.0

    @property
    def ok(self) -> bool:
        return (not self.duplicate_node_tags_gmsh
                and not self.coincident_pairs)


def check(*, tolerance: Optional[float] = None) -> DuplicatesResult:
    """Combine ``getDuplicateNodes`` with a KDTree search within
    ``tolerance`` to detect coincident nodes that gmsh has not yet
    marked."""
    gmsh_dups = tuple(_conn.get_duplicate_nodes())

    coincident: tuple[tuple[int, int], ...] = ()
    if tolerance is not None and tolerance > 0:
        try:
            bundle = _conn.get_nodes()
        except Exception:
            bundle = None
        if bundle is not None and bundle.count > 1:
            tree = cKDTree(bundle.coords)
            pairs = tree.query_pairs(r=float(tolerance), output_type="ndarray")
            tags = bundle.tags
            coincident = tuple(
                (int(tags[i]), int(tags[j])) for i, j in pairs.tolist()
            )

    return DuplicatesResult(
        duplicate_node_tags_gmsh=gmsh_dups,
        coincident_pairs=coincident,
        tolerance=float(tolerance or 0.0),
    )
