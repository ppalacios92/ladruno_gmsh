"""Typed broker exceptions."""
from __future__ import annotations


class KernelError(Exception):
    """Base error from the broker towards gmsh."""


class GmshNotInitialized(KernelError):
    """The gmsh context has not been initialized."""


class UnsupportedFormat(KernelError):
    """File extension not supported by the broker."""


class ImportFailed(KernelError):
    """gmsh failed to read the geometry or mesh file."""


class ExportFailed(KernelError):
    """gmsh failed to write the output file."""


class BooleanFailed(KernelError):
    """Boolean operation with no results or invalid arguments."""


class HealingIncomplete(KernelError):
    """healShapes did not fully consolidate the model."""


class MeshFailed(KernelError):
    """Mesh generation or transformation failed."""


class EntityNotFound(KernelError):
    """The requested (dim, tag) entity does not exist in the current model."""
