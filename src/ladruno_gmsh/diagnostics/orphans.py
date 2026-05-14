"""Orphan nodes and isolated entities."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..kernel import connectivity as _conn
from ..kernel import geometry as _geom


@dataclass(frozen=True)
class OrphansResult:
    orphan_entities: tuple[tuple[int, int], ...] = ()
    orphan_node_tags: tuple[int, ...] = ()
    isolated_node_count: int = 0
    total_node_count: int = 0

    @property
    def ok(self) -> bool:
        return (not self.orphan_entities
                and self.isolated_node_count == 0)


def check() -> OrphansResult:
    """Detect orphan entities (with no associated boundary) and
    orphan nodes (not referenced by any element)."""
    orphan_entities: list[tuple[int, int]] = []
    for d, t in _geom.list_entities(-1):
        if _geom.is_orphan(d, t):
            orphan_entities.append((d, t))

    try:
        nodes = _conn.get_nodes()
        elements = _conn.get_elements()
    except Exception:
        return OrphansResult(orphan_entities=tuple(orphan_entities))

    if nodes.count == 0:
        return OrphansResult(orphan_entities=tuple(orphan_entities),
                             total_node_count=0)

    used: set[int] = set()
    for nt_array in elements.node_tags:
        if nt_array.size:
            used.update(int(x) for x in nt_array.tolist())

    all_tags = set(int(t) for t in nodes.tags.tolist())
    orphan_nodes = sorted(all_tags - used)
    return OrphansResult(
        orphan_entities=tuple(orphan_entities),
        orphan_node_tags=tuple(orphan_nodes),
        isolated_node_count=len(orphan_nodes),
        total_node_count=nodes.count,
    )
