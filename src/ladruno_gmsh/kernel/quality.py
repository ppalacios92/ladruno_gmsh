"""Element quality metrics and Jacobians."""
from __future__ import annotations

from typing import Iterable, Optional

import gmsh
import numpy as np

from .errors import MeshFailed
from .session import session


VALID_METRICS = (
    "minSICN", "minSIGE", "minSJ",
    "gamma", "eta", "innerRadius", "outerRadius", "volume",
)


def element_qualities(element_tags: Iterable[int],
                      metric: str = "minSICN") -> np.ndarray:
    if metric not in VALID_METRICS:
        raise ValueError(f"Unknown metric: {metric}. "
                         f"Accepted: {VALID_METRICS}")
    session().ensure()
    tags = np.asarray(list(element_tags), dtype=np.int64)
    if tags.size == 0:
        return np.empty(0, dtype=np.float64)
    try:
        values = gmsh.model.mesh.getElementQualities(tags.tolist(), metric)
    except Exception as exc:
        raise MeshFailed(f"getElementQualities failed: {exc}") from exc
    return np.asarray(values, dtype=np.float64)


def jacobian(element_tag: int,
             local_coord: Optional[Iterable[float]] = None
             ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    session().ensure()
    coord = list(local_coord) if local_coord is not None else [0.0, 0.0, 0.0]
    try:
        jac, det, points = gmsh.model.mesh.getJacobian(int(element_tag), coord)
    except Exception as exc:
        raise MeshFailed(f"getJacobian failed: {exc}") from exc
    return (
        np.asarray(jac, dtype=np.float64),
        np.asarray(det, dtype=np.float64),
        np.asarray(points, dtype=np.float64),
    )
