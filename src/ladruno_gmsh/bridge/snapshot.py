"""SceneSnapshot: materialized view consumed by the viewer."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class SceneSnapshot:
    """Materialized view ready for rendering.

    - ``geometry`` maps ``entity_uuid -> pv.PolyData`` (one actor per
      surface entity).
    - ``mesh_grid`` holds a ``pv.UnstructuredGrid`` with the full mesh
      when available.
    - ``info`` carries counters and auxiliary flags.
    """

    geometry: Mapping[str, Any] = field(default_factory=dict)
    mesh_grid: Optional[Any] = None
    info: Mapping[str, Any] = field(default_factory=dict)

    @property
    def entity_count(self) -> int:
        return len(self.geometry)

    @property
    def has_mesh(self) -> bool:
        return self.mesh_grid is not None
