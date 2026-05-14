"""Single boundary with gmsh. No other package should import gmsh directly."""
from .errors import (
    BooleanFailed,
    EntityNotFound,
    ExportFailed,
    GmshNotInitialized,
    HealingIncomplete,
    ImportFailed,
    KernelError,
    MeshFailed,
    UnsupportedFormat,
)
from .session import GmshSession, session

__all__ = [
    "GmshSession",
    "session",
    "KernelError",
    "GmshNotInitialized",
    "UnsupportedFormat",
    "ImportFailed",
    "ExportFailed",
    "BooleanFailed",
    "HealingIncomplete",
    "MeshFailed",
    "EntityNotFound",
]
