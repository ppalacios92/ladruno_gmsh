"""Dockable panels (QDockWidget) of the viewer."""
from .boolean import BooleanDock
from .console import ConsoleDock
from .diagnostics import DiagnosticsDock
from .export import ExportDock
from .healing import HealingDock
from .history import HistoryDock
from .mesh import MeshDock
from .model_tree import ModelTreeDock
from .physical_groups import PhysicalGroupsDock
from .properties import PropertiesDock
from .quality import QualityDock
from .reorient import ReorientDock

__all__ = [
    "ModelTreeDock",
    "HistoryDock",
    "PropertiesDock",
    "BooleanDock",
    "HealingDock",
    "MeshDock",
    "ReorientDock",
    "QualityDock",
    "DiagnosticsDock",
    "PhysicalGroupsDock",
    "ConsoleDock",
    "ExportDock",
]
