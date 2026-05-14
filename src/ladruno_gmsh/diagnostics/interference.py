"""Residual overlaps between volumes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import gmsh

from ..kernel import geometry as _geom
from ..kernel.session import session
from ..utils.numeric import BBox


@dataclass(frozen=True)
class InterferenceItem:
    a: int
    b: int
    overlap_bbox: bool
    overlap_volume: Optional[float] = None  # None if not measured


@dataclass(frozen=True)
class InterferenceResult:
    items: tuple[InterferenceItem, ...] = ()
    measured: bool = False

    @property
    def ok(self) -> bool:
        return not any(
            (it.overlap_volume is not None and it.overlap_volume > 0.0)
            for it in self.items
        )


def _bboxes_overlap(a: BBox, b: BBox, *, eps: float = 1e-9) -> bool:
    return not (
        a.xmax + eps < b.xmin or b.xmax + eps < a.xmin
        or a.ymax + eps < b.ymin or b.ymax + eps < a.ymin
        or a.zmax + eps < b.zmin or b.zmax + eps < a.zmin
    )


def check(*, measure: bool = False,
          volume_threshold: float = 1e-12,
          max_pairs: int = 1000) -> InterferenceResult:
    """Detect overlaps between volume pairs.

    By default only evaluates bbox-vs-bbox (fast). With
    ``measure=True`` it copies the overlapping volumes, runs
    ``intersect`` and measures the resulting mass. Expensive: O(N^2)
    in the worst case.
    """
    session().ensure()
    vols = _geom.list_entities(3)
    if len(vols) < 2:
        return InterferenceResult()

    bboxes: list[tuple[tuple[int, int], BBox]] = []
    for d, t in vols:
        try:
            b = _geom.bbox(d, t)
        except Exception:
            b = None
        if b is None or not b.is_finite:
            continue
        bboxes.append(((d, t), b))

    items: list[InterferenceItem] = []
    count = 0
    for i, ((di, ti), bi) in enumerate(bboxes):
        for (dj, tj), bj in bboxes[i + 1:]:
            if not _bboxes_overlap(bi, bj):
                continue
            volume: Optional[float] = None
            if measure:
                try:
                    cp_a = gmsh.model.occ.copy([(di, ti)])
                    cp_b = gmsh.model.occ.copy([(dj, tj)])
                    out, _ovv = gmsh.model.occ.intersect(
                        cp_a, cp_b,
                        removeObject=True, removeTool=True,
                    )
                    gmsh.model.occ.synchronize()
                    total = 0.0
                    for od, ot in out:
                        try:
                            total += float(gmsh.model.occ.getMass(od, ot))
                        except Exception:
                            pass
                    if out:
                        gmsh.model.occ.remove(out, recursive=True)
                        gmsh.model.occ.synchronize()
                    volume = total
                except Exception:
                    volume = None

            items.append(InterferenceItem(
                a=ti, b=tj,
                overlap_bbox=True,
                overlap_volume=volume,
            ))
            count += 1
            if count >= max_pairs:
                break
        if count >= max_pairs:
            break

    significant = [
        it for it in items
        if it.overlap_volume is None or it.overlap_volume > volume_threshold
    ]
    return InterferenceResult(items=tuple(significant), measured=measure)
