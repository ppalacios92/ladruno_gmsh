"""Numeric helpers: bbox, KDTree, derived tolerances."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, sqrt
from typing import Iterable


_ABSURD_THRESHOLD = 1.0e12


@dataclass(frozen=True)
class BBox:
    xmin: float
    ymin: float
    zmin: float
    xmax: float
    ymax: float
    zmax: float

    @classmethod
    def from_tuple(cls, values: Iterable[float]) -> "BBox":
        xmin, ymin, zmin, xmax, ymax, zmax = values
        return cls(float(xmin), float(ymin), float(zmin),
                   float(xmax), float(ymax), float(zmax))

    @classmethod
    def union(cls, boxes: Iterable["BBox"]) -> "BBox | None":
        it = iter(boxes)
        try:
            first = next(it)
        except StopIteration:
            return None
        xmin, ymin, zmin = first.xmin, first.ymin, first.zmin
        xmax, ymax, zmax = first.xmax, first.ymax, first.zmax
        for b in it:
            if b.xmin < xmin:
                xmin = b.xmin
            if b.ymin < ymin:
                ymin = b.ymin
            if b.zmin < zmin:
                zmin = b.zmin
            if b.xmax > xmax:
                xmax = b.xmax
            if b.ymax > ymax:
                ymax = b.ymax
            if b.zmax > zmax:
                zmax = b.zmax
        return cls(xmin, ymin, zmin, xmax, ymax, zmax)

    @property
    def size(self) -> tuple[float, float, float]:
        return (self.xmax - self.xmin,
                self.ymax - self.ymin,
                self.zmax - self.zmin)

    @property
    def center(self) -> tuple[float, float, float]:
        return (0.5 * (self.xmin + self.xmax),
                0.5 * (self.ymin + self.ymax),
                0.5 * (self.zmin + self.zmax))

    @property
    def diagonal(self) -> float:
        dx, dy, dz = self.size
        return sqrt(dx * dx + dy * dy + dz * dz)

    @property
    def is_degenerate(self) -> bool:
        return any(s <= 0.0 for s in self.size)

    @property
    def is_finite(self) -> bool:
        """``True`` if every component is finite and of reasonable magnitude.

        The absolute threshold (``1e12``) filters out the bboxes that
        gmsh returns for open or badly parameterized surfaces in broken
        exports (a building never spans 1 Tm).
        """
        values = (self.xmin, self.ymin, self.zmin,
                  self.xmax, self.ymax, self.zmax)
        return all(isfinite(v) and abs(v) < _ABSURD_THRESHOLD for v in values)
