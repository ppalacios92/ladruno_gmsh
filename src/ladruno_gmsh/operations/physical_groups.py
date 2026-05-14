"""Physical group assignment to entities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..kernel import physical_groups as _pg
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


@dataclass(frozen=True)
class AddPhysicalGroupOp(Operation):
    OP_TYPE: ClassVar[str] = "physical_group.add"

    dim: int = 3
    entity_tags: tuple[int, ...] = ()
    name: str = ""
    tag: int = -1

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        new_tag = _pg.add(self.dim, self.entity_tags,
                          tag=self.tag, name=self.name)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim": self.dim,
                                  "entity_tags": list(self.entity_tags),
                                  "name": self.name,
                                  "tag": new_tag},
                      rebuild_geometry=False)


@dataclass(frozen=True)
class RemovePhysicalGroupOp(Operation):
    OP_TYPE: ClassVar[str] = "physical_group.remove"

    dim_tags: tuple[tuple[int, int], ...] = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _pg.remove(self.dim_tags)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim_tags": list(self.dim_tags)},
                      rebuild_geometry=False)
