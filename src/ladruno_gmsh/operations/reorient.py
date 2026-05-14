"""Normal reorientation and element reversal as operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from ..kernel import reorient as _reo
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


DimTagList = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class ReverseOp(Operation):
    OP_TYPE: ClassVar[str] = "reorient.reverse"

    dim_tags: DimTagList = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _reo.reverse(self.dim_tags)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim_tags": list(self.dim_tags)},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class ReverseElementsOp(Operation):
    OP_TYPE: ClassVar[str] = "reorient.reverse_elements"

    element_tags: tuple[int, ...] = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _reo.reverse_elements(self.element_tags)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"element_tags": list(self.element_tags)},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class SetOutwardOp(Operation):
    OP_TYPE: ClassVar[str] = "reorient.set_outward"

    volume_tag: int = 0

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _reo.set_outward(self.volume_tag)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"volume_tag": self.volume_tag},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class SetAllOutwardOp(Operation):
    """Force outward orientation on every volume."""

    OP_TYPE: ClassVar[str] = "reorient.set_all_outward"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        import gmsh
        n_fixed = 0
        for d, t in gmsh.model.getEntities(3):
            try:
                _reo.set_outward(int(t))
                n_fixed += 1
            except Exception:
                continue
        return record(document, op_type=self.OP_TYPE,
                      parameters={"volumes": n_fixed},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class ReclassifyNodesOp(Operation):
    OP_TYPE: ClassVar[str] = "reorient.reclassify_nodes"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _reo.reclassify_nodes()
        return record(document, op_type=self.OP_TYPE, parameters={},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class RelocateNodesOp(Operation):
    OP_TYPE: ClassVar[str] = "reorient.relocate_nodes"

    dim: int = -1
    tag: int = -1

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _reo.relocate_nodes(self.dim, self.tag)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim": self.dim, "tag": self.tag},
                      rebuild_geometry=False, rebuild_mesh=True)
