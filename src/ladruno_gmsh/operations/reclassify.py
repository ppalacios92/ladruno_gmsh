"""Surface reclassification and topological reconstruction."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from ..kernel import reclassify as _rec
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


@dataclass(frozen=True)
class ClassifySurfacesOp(Operation):
    OP_TYPE: ClassVar[str] = "reclassify.classify_surfaces"

    angle_deg: float = 40.0
    boundary: bool = True
    for_reparametrization: bool = True
    curve_angle_deg: float = 180.0
    export_discrete: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _rec.classify_surfaces(
            angle_deg=self.angle_deg,
            boundary=self.boundary,
            for_reparametrization=self.for_reparametrization,
            curve_angle_deg=self.curve_angle_deg,
            export_discrete=self.export_discrete,
        )
        return record(document, op_type=self.OP_TYPE,
                      parameters={"angle_deg": self.angle_deg,
                                  "boundary": self.boundary,
                                  "for_reparametrization": self.for_reparametrization,
                                  "curve_angle_deg": self.curve_angle_deg,
                                  "export_discrete": self.export_discrete})


@dataclass(frozen=True)
class CreateGeometryOp(Operation):
    OP_TYPE: ClassVar[str] = "reclassify.create_geometry"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _rec.create_geometry()
        return record(document, op_type=self.OP_TYPE, parameters={})


@dataclass(frozen=True)
class CreateTopologyOp(Operation):
    OP_TYPE: ClassVar[str] = "reclassify.create_topology"

    make_simply_connected: bool = True
    export_discrete: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _rec.create_topology(
            make_simply_connected=self.make_simply_connected,
            export_discrete=self.export_discrete,
        )
        return record(document, op_type=self.OP_TYPE,
                      parameters={"make_simply_connected": self.make_simply_connected,
                                  "export_discrete": self.export_discrete})
