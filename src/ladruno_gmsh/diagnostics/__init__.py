"""FEM analysis over GeometryDocument and MeshSnapshot."""
from . import (
    duplicates,
    interference,
    manifoldness,
    normals,
    orphans,
    quality,
    report,
)
from .duplicates import DuplicatesResult
from .interference import InterferenceItem, InterferenceResult
from .manifoldness import ManifoldnessResult
from .normals import NormalsResult
from .orphans import OrphansResult
from .quality import QualityResult
from .report import Report, build

__all__ = [
    "orphans",
    "duplicates",
    "quality",
    "manifoldness",
    "interference",
    "normals",
    "report",
    "OrphansResult",
    "DuplicatesResult",
    "QualityResult",
    "ManifoldnessResult",
    "InterferenceResult",
    "InterferenceItem",
    "NormalsResult",
    "Report",
    "build",
]
