"""Element quality histograms and filters."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..kernel import connectivity as _conn
from ..kernel import quality as _q


@dataclass(frozen=True)
class QualityResult:
    metric: str
    values: np.ndarray = field(default_factory=lambda: np.empty(0))
    element_tags: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))
    bins: int = 20

    @property
    def count(self) -> int:
        return int(self.values.size)

    @property
    def min(self) -> float:
        return float(self.values.min()) if self.values.size else float("nan")

    @property
    def max(self) -> float:
        return float(self.values.max()) if self.values.size else float("nan")

    @property
    def mean(self) -> float:
        return float(self.values.mean()) if self.values.size else float("nan")

    @property
    def median(self) -> float:
        return float(np.median(self.values)) if self.values.size else float("nan")

    def histogram(self, bins: int | None = None
                  ) -> tuple[np.ndarray, np.ndarray]:
        b = int(bins) if bins is not None else self.bins
        if self.values.size == 0:
            return np.empty(0), np.empty(b + 1)
        return np.histogram(self.values, bins=b)

    def count_below(self, threshold: float) -> int:
        if self.values.size == 0:
            return 0
        return int(np.sum(self.values < threshold))

    def tags_below(self, threshold: float) -> np.ndarray:
        if self.values.size == 0:
            return np.empty(0, dtype=np.int64)
        mask = self.values < threshold
        return self.element_tags[mask]


def check(metric: str = "minSICN", dim: int = -1) -> QualityResult:
    """Compute the quality metric over every element in the model (or
    of the given dimension)."""
    elements = _conn.get_elements(dim=dim)
    all_tags: list[int] = []
    for tag_arr in elements.tags:
        if tag_arr.size:
            all_tags.extend(int(x) for x in tag_arr.tolist())
    if not all_tags:
        return QualityResult(metric=metric)
    values = _q.element_qualities(all_tags, metric=metric)
    return QualityResult(
        metric=metric,
        values=values,
        element_tags=np.asarray(all_tags, dtype=np.int64),
    )
