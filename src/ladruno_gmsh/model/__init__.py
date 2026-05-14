"""Immutable domain model. Depends on neither gmsh nor Qt."""
from .document import GeometryDocument
from .entity import DimTag, Entity
from .history import OperationGraph, OperationNode
from .mesh_snapshot import MeshSnapshot
from .tolerances import Tolerance
from .units import Units

__all__ = [
    "GeometryDocument",
    "Entity",
    "DimTag",
    "OperationGraph",
    "OperationNode",
    "MeshSnapshot",
    "Tolerance",
    "Units",
]
