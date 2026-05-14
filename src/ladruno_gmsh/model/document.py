"""GeometryDocument: complete model state (entities, mesh, history)."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from ..utils.numeric import BBox
from .entity import Entity
from .history import OperationGraph
from .mesh_snapshot import MeshSnapshot
from .units import Units


@dataclass(frozen=True)
class GeometryDocument:
    entities: tuple[Entity, ...]
    units: Units
    source_files: tuple[Path, ...]
    history: OperationGraph = field(default_factory=OperationGraph)
    mesh: MeshSnapshot = field(default_factory=MeshSnapshot.empty)

    @property
    def volumes(self) -> tuple[Entity, ...]:
        return tuple(e for e in self.entities if e.dim == 3)

    @property
    def surfaces(self) -> tuple[Entity, ...]:
        return tuple(e for e in self.entities if e.dim == 2)

    @property
    def curves(self) -> tuple[Entity, ...]:
        return tuple(e for e in self.entities if e.dim == 1)

    @property
    def points(self) -> tuple[Entity, ...]:
        return tuple(e for e in self.entities if e.dim == 0)

    def find_by_uuid(self, uuid: str) -> Optional[Entity]:
        for e in self.entities:
            if e.uuid == uuid:
                return e
        return None

    def find_by_dim_tag(self, dim: int, tag: int) -> Optional[Entity]:
        for e in self.entities:
            if e.dim == dim and e.tag == tag:
                return e
        return None

    def global_bbox(self) -> Optional[BBox]:
        return BBox.union(
            e.bbox for e in self.entities
            if e.bbox is not None and e.bbox.is_finite
        )

    def bbox_diagonal(self) -> float:
        b = self.global_bbox()
        return b.diagonal if b is not None else 0.0

    def with_entities(self, entities: tuple[Entity, ...]) -> "GeometryDocument":
        return GeometryDocument(
            entities=entities,
            units=self.units,
            source_files=self.source_files,
            history=self.history,
            mesh=self.mesh,
        )

    def with_history(self, history: OperationGraph) -> "GeometryDocument":
        return GeometryDocument(
            entities=self.entities,
            units=self.units,
            source_files=self.source_files,
            history=history,
            mesh=self.mesh,
        )

    def with_mesh(self, mesh: MeshSnapshot) -> "GeometryDocument":
        return GeometryDocument(
            entities=self.entities,
            units=self.units,
            source_files=self.source_files,
            history=self.history,
            mesh=mesh,
        )
