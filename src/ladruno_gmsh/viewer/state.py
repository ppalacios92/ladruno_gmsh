"""ViewerState: visualization parameters and selection modes."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ViewerState:
    background: str = "#1f2227"
    show_axes: bool = True
    show_bbox: bool = False
    show_edges: bool = True
    show_normals: bool = False
    show_mesh: bool = False
    show_mesh_nodes: bool = True
    mesh_node_size: float = 5.0
    # User-preferred opacity of the CAD shell (from the slider). The
    # renderer applies a multiplicative auto-dim when 3D mesh is
    # active but does NOT overwrite this preference:
    # ``entity_opacity * auto_dim``.
    entity_opacity: float = 1.0
    selection_mode: str = "entity"      # "entity" | "face" | "element"
    tess_target_size: Optional[float] = None
    tess_size_factor: float = 1.0
    tess_elements_per_2pi: int = 12
    color_by: str = "kind"              # "kind" | "uuid" | "quality"
    quality_metric: str = "minSICN"
    quality_threshold: float = 0.1
    selection_uuid: Optional[str] = None
    tolerance_override: Optional[float] = None
    orthographic: bool = False
    box_selection: bool = False
    sticky_selection: bool = False
    last_click_modifiers: int = 0
