"""ladruno_gmsh: geometry and mesh broker over gmsh with a PyVista/Qt viewer."""
from .api import Session, open_model
from .kernel import (
    BooleanFailed,
    EntityNotFound,
    ExportFailed,
    HealingIncomplete,
    ImportFailed,
    KernelError,
    MeshFailed,
    UnsupportedFormat,
)
from .model import (
    DimTag,
    Entity,
    GeometryDocument,
    MeshSnapshot,
    OperationGraph,
    OperationNode,
    Tolerance,
    Units,
)
from .utils.numeric import BBox

__version__ = "0.0.1"

__all__ = [
    "__version__",
    "Session",
    "open_model",
    "GeometryDocument",
    "Entity",
    "DimTag",
    "BBox",
    "MeshSnapshot",
    "OperationGraph",
    "OperationNode",
    "Tolerance",
    "Units",
    "KernelError",
    "UnsupportedFormat",
    "ImportFailed",
    "ExportFailed",
    "BooleanFailed",
    "HealingIncomplete",
    "MeshFailed",
    "EntityNotFound",
]
