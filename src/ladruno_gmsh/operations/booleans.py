"""Boolean operations as timeline operations.

The four primitives wrap directly the matching gmsh OCC calls: ``cut``,
``fuse``, ``intersect``, ``fragment``. ``fragment_all`` is the shortcut
that runs ``fragment`` over every entity of a given dimension.

The other six ``Op`` classes are derived from the same primitives — they
introduce no new geometric algorithm, only specific parameter or
composition patterns commonly expected from a CAD boolean menu:

- ``ImprintOp`` runs ``fragment`` with both ``removeObject`` and
  ``removeTool`` set to ``False``, so the conformal interfaces appear
  but the original entities survive.
- ``SplitOp`` runs ``fragment`` keeping both sides; the user removes
  pieces afterwards.
- ``SelfIntersectOp`` runs ``fragment`` with an empty ``tools`` list to
  resolve auto-intersections.
- ``XorOp`` orchestrates three OCC calls (fuse, intersect, cut) and
  records them as a single timeline step.
- ``SectionOp`` builds a finite disk through the requested point /
  normal and intersects every input volume against it.
- ``HollowOp`` wraps ``model.occ.addThickSolid`` (a CAD modifier; lives
  here because UIs surface it next to the other "boolean" actions).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Optional

from ..kernel import boolean as _bool
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


DimTagList = tuple[tuple[int, int], ...]
Point3D = tuple[float, float, float]


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


@dataclass(frozen=True)
class ImprintOp(Operation):
    """Imprint shared interfaces between two entity sets without
    consuming either side.

    Wraps ``kernel.boolean.imprint`` (``fragment`` with both
    ``remove_object`` and ``remove_tool`` set to ``False``). Use for
    tie / cohesive contact in FEM when two volumes must share a face
    but neither should be cut.
    """

    OP_TYPE: ClassVar[str] = "imprint"

    objects: DimTagList = ()
    tools: DimTagList = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out, _ovv = _bool.imprint(self.objects, self.tools)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects),
                                  "tools": list(self.tools)},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class SplitOp(Operation):
    """Cut ``objects`` with ``tools`` and keep every resulting piece.

    Equivalent to ``fragment`` with ``remove_object=False`` and
    ``remove_tool=False`` but conceptually distinct: the user wants the
    split pieces as new entities and will decide which to delete later.
    """

    OP_TYPE: ClassVar[str] = "split"

    objects: DimTagList = ()
    tools: DimTagList = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out, _ovv = _bool.fragment(self.objects, self.tools,
                                   remove_object=False, remove_tool=False)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects),
                                  "tools": list(self.tools)},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class SelfIntersectOp(Operation):
    """Resolve auto-intersections inside a set of entities.

    Wraps ``kernel.boolean.self_intersect`` (``fragment(objects, [])``).
    Common after importing badly modeled geometry where a single solid
    overlaps itself.
    """

    OP_TYPE: ClassVar[str] = "self_intersect"

    objects: DimTagList = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out, _ovv = _bool.self_intersect(self.objects)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects)},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class XorOp(Operation):
    """Symmetric difference: ``(A ∪ B) \\ (A ∩ B)``.

    Composes three OCC calls (``fuse``, ``intersect``, ``cut``) on
    copies of the inputs and records the whole sequence as a single
    timeline node.
    """

    OP_TYPE: ClassVar[str] = "xor"

    objects: DimTagList = ()
    tools: DimTagList = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out = _bool.xor(self.objects, self.tools)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"objects": list(self.objects),
                                  "tools": list(self.tools)},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class SectionOp(Operation):
    """Slice a set of volumes with an infinite plane.

    The plane is materialized as a finite disk centered at ``point``
    with axis ``normal`` and a radius large enough to cross every
    input bounding box (``extent`` overrides the auto size). The
    result is a set of 2D surfaces — the cross sections — left inside
    the volumes (volumes are NOT consumed).
    """

    OP_TYPE: ClassVar[str] = "section"

    volume_dim_tags: DimTagList = ()
    point: Point3D = (0.0, 0.0, 0.0)
    normal: Point3D = (0.0, 0.0, 1.0)
    extent: Optional[float] = None

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out = _bool.section(
            self.volume_dim_tags,
            point=self.point,
            normal=self.normal,
            extent=self.extent,
        )
        return record(document, op_type=self.OP_TYPE,
                      parameters={"volume_dim_tags": list(self.volume_dim_tags),
                                  "point": list(self.point),
                                  "normal": list(self.normal),
                                  "extent": self.extent},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class HollowOp(Operation):
    """Build a hollow shell from a set of volumes.

    Wraps ``model.occ.addThickSolid``. ``thickness`` is signed:
    negative offsets carve inward, positive offsets bulge outward.
    ``open_face_dim_tags`` lists faces that should be removed from the
    resulting shell (the "open" sides of a hollow part — e.g. the
    rim of a cup).
    """

    OP_TYPE: ClassVar[str] = "hollow"

    volume_dim_tags: DimTagList = ()
    thickness: float = -1.0
    open_face_dim_tags: DimTagList = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        out = _bool.hollow(
            self.volume_dim_tags,
            thickness=self.thickness,
            open_face_dim_tags=self.open_face_dim_tags,
        )
        return record(document, op_type=self.OP_TYPE,
                      parameters={"volume_dim_tags": list(self.volume_dim_tags),
                                  "thickness": self.thickness,
                                  "open_face_dim_tags": list(self.open_face_dim_tags)},
                      produced_dim_tags=out)
