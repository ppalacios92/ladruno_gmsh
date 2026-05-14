"""Generation, refinement, recombination and order as operations."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar, Optional

from ..kernel import mesh as _mesh
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


@dataclass(frozen=True)
class GenerateMeshOp(Operation):
    OP_TYPE: ClassVar[str] = "mesh.generate"

    dim: int = 3
    size_min: Optional[float] = None
    size_max: Optional[float] = None
    algorithm_2d: Optional[str] = None
    algorithm_3d: Optional[str] = None

    # Safety limits to avoid impossible requests (memory).
    # 1/200 = ~8 million tets in 3D as a practical bound. Above that
    # a size change usually ends in out-of-memory.
    _SAFE_MIN_RATIO: ClassVar[float] = 5.0e-3  # size >= bbox / 200
    _SAFE_MAX_RATIO: ClassVar[float] = 1.0     # size <= bbox

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        if self.algorithm_2d is not None:
            _mesh.set_algorithm_2d(self.algorithm_2d)
        if self.algorithm_3d is not None:
            _mesh.set_algorithm_3d(self.algorithm_3d)

        size_min, size_max, note = self._validate_sizes(document)

        # Reset overrides the tessellator may have left active.
        _mesh.reset_size_options()

        if size_min is not None or size_max is not None:
            _mesh.set_size_global(size_min, size_max)

        # clear_first=True ensures the new size is applied even when a
        # mesh already existed.
        _mesh.generate(self.dim, clear_first=True)

        params = {
            "dim": self.dim,
            "size_min": size_min,
            "size_max": size_max,
            "algorithm_2d": self.algorithm_2d,
            "algorithm_3d": self.algorithm_3d,
        }
        if note:
            params["note"] = note
        return record(document, op_type=self.OP_TYPE,
                      parameters=params,
                      rebuild_geometry=False,
                      rebuild_mesh=True)

    def _validate_sizes(self, document: GeometryDocument
                        ) -> tuple[Optional[float], Optional[float],
                                   Optional[str]]:
        diag = document.bbox_diagonal()
        if diag <= 0:
            return self.size_min, self.size_max, None
        floor = diag * self._SAFE_MIN_RATIO
        ceiling = diag * self._SAFE_MAX_RATIO
        smin, smax = self.size_min, self.size_max
        notes: list[str] = []
        if smin is not None and smin < floor:
            notes.append(f"size_min {smin} raised to {floor:.4g} (bbox*{self._SAFE_MIN_RATIO})")
            smin = floor
        if smax is not None and smax < floor:
            notes.append(f"size_max {smax} raised to {floor:.4g}")
            smax = floor
        if smin is not None and smin > ceiling:
            notes.append(f"size_min {smin} lowered to {ceiling:.4g} (bbox)")
            smin = ceiling
        if smax is not None and smax > ceiling:
            notes.append(f"size_max {smax} lowered to {ceiling:.4g}")
            smax = ceiling
        note = " | ".join(notes) if notes else None
        return smin, smax, note


@dataclass(frozen=True)
class RefineMeshOp(Operation):
    OP_TYPE: ClassVar[str] = "mesh.refine"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _mesh.refine()
        return record(document, op_type=self.OP_TYPE, parameters={},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class SetOrderOp(Operation):
    OP_TYPE: ClassVar[str] = "mesh.set_order"

    order: int = 2

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _mesh.set_order(self.order)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"order": self.order},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class OptimizeMeshOp(Operation):
    OP_TYPE: ClassVar[str] = "mesh.optimize"

    method: str = ""
    niter: int = 1
    quality: float = 0.0
    force: bool = False

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _mesh.optimize(self.method, force=self.force,
                       niter=self.niter, quality=self.quality)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"method": self.method,
                                  "niter": self.niter,
                                  "quality": self.quality,
                                  "force": self.force},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class RecombineOp(Operation):
    OP_TYPE: ClassVar[str] = "mesh.recombine"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _mesh.recombine()
        return record(document, op_type=self.OP_TYPE, parameters={},
                      rebuild_geometry=False, rebuild_mesh=True)


@dataclass(frozen=True)
class SetSizeFromCurvatureOp(Operation):
    OP_TYPE: ClassVar[str] = "mesh.size_from_curvature"

    elements_per_2pi: int = 12

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _mesh.set_size_from_curvature(self.elements_per_2pi)
        return record(document, op_type=self.OP_TYPE,
                      parameters={"elements_per_2pi": self.elements_per_2pi},
                      rebuild_geometry=False, rebuild_mesh=False)


@dataclass(frozen=True)
class ClearMeshOp(Operation):
    OP_TYPE: ClassVar[str] = "mesh.clear"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _mesh.clear()
        return record(document, op_type=self.OP_TYPE, parameters={},
                      rebuild_geometry=False, rebuild_mesh=True)
