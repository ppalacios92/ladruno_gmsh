"""Themed toolbars (main and view)."""
from __future__ import annotations

from typing import Callable

from .deps import require_dependencies


def build_main_toolbar(parent, viewer_session) -> object:
    deps = require_dependencies()
    QtWidgets = deps["QtWidgets"]

    bar = QtWidgets.QToolBar("Main", parent)
    bar.setMovable(False)

    def add(label: str, slot: Callable[[], None], tooltip: str = "") -> None:
        act = bar.addAction(label)
        if tooltip:
            act.setToolTip(tooltip)
        act.triggered.connect(slot)

    add("Refresh", viewer_session.refresh_scene,
        "Re-tessellate and refresh the scene.")
    add("Undo",
        lambda: viewer_session.run_method("undo"),
        "Replay the timeline without the last step. Slow but safe. (Ctrl+Z)")
    bar.addSeparator()
    add("Clean Revit",
        lambda: viewer_session.run_method("clean_revit"),
        "heal + remove_all_duplicates + fragment_all.")
    add("Heal",
        lambda: viewer_session.run_method("heal"),
        "Apply healShapes with automatic tolerance.")
    add("Fragment all",
        lambda: viewer_session.run_method("fragment_all"),
        "Fragment every volume against every other.")
    add("Unify all (3D)",
        lambda: viewer_session.run_method("unify_all_solids", dim=3),
        "Fuse all volumes into one (for clean CAD output).")
    bar.addSeparator()
    add("Mesh 3D",
        lambda: viewer_session.run_method("mesh", dim=3),
        "Generate volumetric mesh with default parameters.")
    add("Quality",
        lambda: viewer_session.show_quality(),
        "Compute element quality metrics.")
    add("Report",
        lambda: viewer_session.show_report(),
        "Generate the full FEM diagnostics report.")
    bar.addSeparator()
    add("Delete",
        viewer_session.delete_selected,
        "Remove multi-selected entities (Delete key).")
    add("Box select",
        viewer_session.toggle_box_selection,
        "Toggle rectangle selection (left-drag).")
    add("Sticky",
        viewer_session.toggle_sticky_selection,
        "Each click ADDS to the selection instead of replacing it.")
    add("Explode",
        viewer_session.explode_selected,
        "Replace the selection with its boundary "
        "(volume->faces, face->edges, edge->points). Key X.")
    add("Ortho",
        viewer_session.toggle_orthographic,
        "Toggle orthographic / perspective projection.")
    bar.addSeparator()
    add("Reset view", viewer_session.reset_camera,
        "Re-center the camera.")
    add("Export STEP",
        viewer_session.export_unified_step,
        "Unify volumes and export to STEP for downstream CAD.")
    return bar


def build_view_toolbar(parent, viewer_session) -> object:
    """Toolbar with standard views and camera modes."""
    deps = require_dependencies()
    QtWidgets = deps["QtWidgets"]

    bar = QtWidgets.QToolBar("Views", parent)
    bar.setMovable(False)

    def add(label: str, slot, tooltip: str = "") -> None:
        act = bar.addAction(label)
        if tooltip:
            act.setToolTip(tooltip)
        act.triggered.connect(slot)

    add("Top",   lambda: viewer_session.set_camera_view("top"),
        "Top view (Ctrl+1)")
    add("Front", lambda: viewer_session.set_camera_view("front"),
        "Front view (Ctrl+2)")
    add("Right", lambda: viewer_session.set_camera_view("right"),
        "Right view (Ctrl+3)")
    add("Iso",   lambda: viewer_session.set_camera_view("iso"),
        "Isometric view (Ctrl+0)")
    bar.addSeparator()
    add("Persp/Ortho", viewer_session.toggle_orthographic,
        "Toggle projection (key O)")
    bar.addSeparator()

    # Revit-style visibility.
    add("Hide", viewer_session.hide_selected, "Hide selection (H)")
    add("Isolate", viewer_session.isolate_selected,
        "Isolate selection (I)")
    add("Show all", viewer_session.show_all,
        "Show all (Ctrl+Shift+A)")
    bar.addSeparator()

    # Inline opacity slider.
    label = QtWidgets.QLabel("Opacity:")
    label.setStyleSheet("padding: 0 6px;")
    bar.addWidget(label)
    slider = QtWidgets.QSlider(deps["QtCore"].Qt.Horizontal)
    slider.setRange(10, 100)
    slider.setValue(100)
    slider.setFixedWidth(140)
    slider.valueChanged.connect(
        lambda v: viewer_session.opacityChanged.emit(v / 100.0)
    )
    bar.addWidget(slider)
    return bar
