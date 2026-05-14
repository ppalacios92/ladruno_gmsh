"""Consolidated report builder (Markdown / HTML)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import (
    duplicates as _dup,
    interference as _intf,
    manifoldness as _mf,
    normals as _nor,
    orphans as _orph,
    quality as _q,
)
from .duplicates import DuplicatesResult
from .interference import InterferenceResult
from .manifoldness import ManifoldnessResult
from .normals import NormalsResult
from .orphans import OrphansResult
from .quality import QualityResult


@dataclass(frozen=True)
class Report:
    orphans: OrphansResult = field(default_factory=OrphansResult)
    duplicates: DuplicatesResult = field(default_factory=DuplicatesResult)
    quality: Optional[QualityResult] = None
    manifoldness: ManifoldnessResult = field(default_factory=ManifoldnessResult)
    interference: InterferenceResult = field(default_factory=InterferenceResult)
    normals: NormalsResult = field(default_factory=NormalsResult)

    @property
    def ok(self) -> bool:
        checks = [
            self.orphans.ok,
            self.duplicates.ok,
            self.manifoldness.ok,
            self.interference.ok,
            self.normals.ok,
        ]
        if self.quality is not None:
            checks.append(self.quality.count_below(0.0) == 0)
        return all(checks)

    def as_markdown(self) -> str:
        lines: list[str] = ["# FEM Diagnostics", ""]

        lines.append("## Orphan entities and nodes")
        lines.append(f"- orphan entities: {len(self.orphans.orphan_entities)}")
        lines.append(f"- nodes without elements: {self.orphans.isolated_node_count}"
                     f" / {self.orphans.total_node_count}")
        lines.append("")

        lines.append("## Duplicates")
        lines.append(f"- detected by gmsh: {len(self.duplicates.duplicate_node_tags_gmsh)}")
        lines.append(f"- coincident pairs (KDTree, tol={self.duplicates.tolerance:g}): "
                     f"{len(self.duplicates.coincident_pairs)}")
        lines.append("")

        if self.quality is not None and self.quality.count > 0:
            q = self.quality
            lines.append(f"## Quality ({q.metric})")
            lines.append(f"- elements: {q.count}")
            lines.append(f"- min/median/mean/max: {q.min:.4f} / {q.median:.4f}"
                         f" / {q.mean:.4f} / {q.max:.4f}")
            lines.append(f"- elements with value < 0: {q.count_below(0.0)}")
            lines.append(f"- elements with value < 0.1: {q.count_below(0.1)}")
            lines.append("")
        elif self.quality is not None:
            lines.append("## Quality")
            lines.append("- empty mesh; quality was not evaluated.")
            lines.append("")

        lines.append("## Manifoldness")
        lines.append(f"- free edges: {self.manifoldness.free_edges_count}")
        lines.append(f"- non-manifold edges: {self.manifoldness.non_manifold_edges_count}")
        lines.append("")

        lines.append("## Volume interference")
        lines.append(f"- overlapping pairs (bbox/volume): {len(self.interference.items)}")
        lines.append(f"- measured: {self.interference.measured}")
        lines.append("")

        lines.append("## Normals")
        if self.normals.note:
            lines.append(f"- {self.normals.note}")
        else:
            lines.append(f"- surfaces with orientation inverted vs. volume: "
                         f"{len(self.normals.inverted_surfaces)}")
            lines.append(f"- faces inspected: {self.normals.inspected}")
        lines.append("")

        lines.append(f"**Overall result: {'OK' if self.ok else 'FINDINGS'}**")
        return "\n".join(lines)


def build(*,
          quality_metric: str = "minSICN",
          dup_tolerance: Optional[float] = None,
          measure_interference: bool = False) -> Report:
    """Run every check and build the consolidated report.

    When there is no mesh, ``quality`` stays ``None`` and the rest of
    the checks operate on the available geometry.
    """
    orphans = _orph.check()
    dups = _dup.check(tolerance=dup_tolerance)

    quality: Optional[QualityResult] = None
    if orphans.total_node_count > 0:
        try:
            quality = _q.check(metric=quality_metric)
        except Exception:
            quality = None

    try:
        mf = _mf.check()
    except Exception:
        mf = ManifoldnessResult()

    try:
        intf = _intf.check(measure=measure_interference)
    except Exception:
        intf = InterferenceResult()

    try:
        nor = _nor.check()
    except Exception:
        nor = NormalsResult()

    return Report(
        orphans=orphans,
        duplicates=dups,
        quality=quality,
        manifoldness=mf,
        interference=intf,
        normals=nor,
    )
