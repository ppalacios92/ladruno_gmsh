"""Cut, Fuse, Intersect, Fragment as timeline operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from ..kernel import boolean as _bool
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


DimTagList = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class CutOp(Operation):
    OP_TYPE: ClassVar[str] = "cut"

    objects: DimTagList = ()
    tools: DimTagList = ()
    remove_object: bool = True
    remove_tool: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out, _ovv = _bool.cut(self.objects, self.tools,
                              remove_object=self.remove_object,
                              remove_tool=self.remove_tool)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects),
                                  "tools": list(self.tools),
                                  "remove_object": self.remove_object,
                                  "remove_tool": self.remove_tool},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class FuseOp(Operation):
    OP_TYPE: ClassVar[str] = "fuse"

    objects: DimTagList = ()
    tools: DimTagList = ()
    remove_object: bool = True
    remove_tool: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out, _ovv = _bool.fuse(self.objects, self.tools,
                               remove_object=self.remove_object,
                               remove_tool=self.remove_tool)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects),
                                  "tools": list(self.tools),
                                  "remove_object": self.remove_object,
                                  "remove_tool": self.remove_tool},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class IntersectOp(Operation):
    OP_TYPE: ClassVar[str] = "intersect"

    objects: DimTagList = ()
    tools: DimTagList = ()
    remove_object: bool = True
    remove_tool: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out, _ovv = _bool.intersect(self.objects, self.tools,
                                    remove_object=self.remove_object,
                                    remove_tool=self.remove_tool)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects),
                                  "tools": list(self.tools),
                                  "remove_object": self.remove_object,
                                  "remove_tool": self.remove_tool},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class FragmentOp(Operation):
    OP_TYPE: ClassVar[str] = "fragment"

    objects: DimTagList = ()
    tools: DimTagList = ()
    remove_object: bool = True
    remove_tool: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out, _ovv = _bool.fragment(self.objects, self.tools,
                                   remove_object=self.remove_object,
                                   remove_tool=self.remove_tool)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects),
                                  "tools": list(self.tools),
                                  "remove_object": self.remove_object,
                                  "remove_tool": self.remove_tool},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class FragmentAllOp(Operation):
    """Fragment all entities of the given dimension against each other."""

    OP_TYPE: ClassVar[str] = "fragment_all"

    dim: int = 3

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out = _bool.fragment_all(self.dim)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim": self.dim},
                      produced_dim_tags=out)
