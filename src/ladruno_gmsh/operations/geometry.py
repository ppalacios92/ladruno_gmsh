"""Direct OCC entity manipulation operations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

import gmsh

from ..kernel import geometry as _geom
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


DimTagList = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class RemoveEntitiesOp(Operation):
    """Remove entities from the model (with their dependencies)."""

    OP_TYPE: ClassVar[str] = "remove_entities"

    dim_tags: DimTagList = ()
    recursive: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _geom.remove(self.dim_tags, recursive=self.recursive)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim_tags": list(self.dim_tags),
                                  "recursive": self.recursive})


@dataclass(frozen=True)
class MergeToSolidOp(Operation):
    """Sew loose surfaces and create closed volumes.

    Inverse operation of :class:`ExplodeOp`: take faces that live in
    isolation (typical after an explode or an import without solid)
    and rebuild them into one or more volumes. Under the hood it calls
    ``occ.healShapes`` with ``sewFaces=True, makeSolids=True`` but
    **without** the full heal fixes (small edges/faces, degenerated)
    so the user's geometry is not altered.
    """

    OP_TYPE: ClassVar[str] = "merge_to_solid"

    tolerance: Optional[float] = None
    dim_tags: DimTagList = ()  # empty = every surface

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        from ..kernel import healing as _heal
        tol = self.tolerance
        if tol is None:
            tol = max(document.bbox_diagonal() * 1e-6, 1e-9)
        out = _heal.heal(
            tolerance=float(tol),
            dim_tags=self.dim_tags or None,
            fix_degenerated=False,
            fix_small_edges=False,
            fix_small_faces=False,
            sew_faces=True,
            make_solids=True,
        )
        return record(document, op_type=self.OP_TYPE,
                      parameters={"tolerance": tol,
                                  "dim_tags": list(self.dim_tags)},
                      produced_dim_tags=out)


@dataclass(frozen=True)
class ExplodeOp(Operation):
    """Break entities while keeping their boundary entities (dim-1) alive.

    Implementation: ``occ.remove(dim_tags, recursive=False)``. The
    boundary (faces of a volume, edges of a face, etc.) are OCC
    entities of their own and stay in the model when the parent is
    removed without propagation.
    """

    OP_TYPE: ClassVar[str] = "explode"

    dim_tags: DimTagList = ()

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        if self.dim_tags:
            _geom.remove(self.dim_tags, recursive=False)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim_tags": list(self.dim_tags)})


@dataclass(frozen=True)
class UnifyAllOp(Operation):
    """Fuse every volume (or surface) into a single entity.

    Useful when one wants to export a single-solid STEP to CAD after
    fragmenting for FEM.
    """

    OP_TYPE: ClassVar[str] = "unify_all"

    dim: int = 3

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        ents = [(int(d), int(t))
                for d, t in gmsh.model.getEntities(self.dim)]
        produced: list[tuple[int, int]] = []
        if len(ents) >= 2:
            try:
                out, _ovv = gmsh.model.occ.fuse(
                    [ents[0]], list(ents[1:]),
                    removeObject=True, removeTool=True,
                )
                gmsh.model.occ.synchronize()
                produced = [(int(d), int(t)) for d, t in out]
            except Exception:
                # On models with disconnected pieces fuse may fail.
                # Let it pass and surface it through diagnostics.
                pass
        return record(document, op_type=self.OP_TYPE,
                      parameters={"dim": self.dim},
                      produced_dim_tags=produced or None)
