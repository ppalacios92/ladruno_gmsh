"""Headless viewer construction tests."""
from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.filterwarnings(
    "ignore::DeprecationWarning",
)


@pytest.fixture(scope="module")
def qt_app():
    try:
        from qtpy import QtWidgets
    except ImportError:
        pytest.skip("Qt not available.")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def test_viewer_imports() -> None:
    from ladruno_gmsh.viewer import ViewerSession, launch, require_dependencies
    require_dependencies()
    assert ViewerSession is not None
    assert callable(launch)


def test_viewer_session_constructs(qt_app, two_boxes_step: Path) -> None:
    from ladruno_gmsh import open_model
    from ladruno_gmsh.viewer.session import ViewerSession

    with open_model(two_boxes_step, units="m") as s:
        viewer = ViewerSession(s)
        assert viewer.api is s
        viewer.refresh_scene()
        assert viewer.scene_snapshot.entity_count > 0


def test_main_window_constructs(qt_app, two_boxes_step: Path) -> None:
    from ladruno_gmsh import open_model
    from ladruno_gmsh.viewer.session import ViewerSession
    from ladruno_gmsh.viewer.window import MainWindow

    with open_model(two_boxes_step, units="m") as s:
        viewer = ViewerSession(s)
        window = MainWindow(viewer)
        try:
            assert "ladruno_gmsh" in window.win.windowTitle()
            assert window.model_tree.tree.topLevelItemCount() > 0
            viewer.refresh_scene()
            assert window.scene._actor is not None
        finally:
            window.win.close()
            window.central.close()


def test_diagnostics_dock_actions(qt_app, two_boxes_step: Path) -> None:
    """Verify that DiagnosticsDock handlers execute without error."""
    from ladruno_gmsh import open_model
    from ladruno_gmsh.viewer.session import ViewerSession
    from ladruno_gmsh.viewer.window import MainWindow

    with open_model(two_boxes_step, units="m") as s:
        s.fragment_all(dim=3)
        s.remove_all_duplicates()
        s.mesh(size=0.5, dim=3)
        viewer = ViewerSession(s)
        window = MainWindow(viewer)
        try:
            dock = window.diagnostics
            dock._run_orphans()
            dock._run_dups()
            dock._run_manifold()
            dock._run_intf(False)
            dock._run_normals()
            dock._run_report()
            assert "FEM Diagnostics" in dock.view.toPlainText()
        finally:
            window.win.close()
            window.central.close()
