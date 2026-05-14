"""Selection tests: point click, multi, box-select, ESC.

This does NOT simulate mouse events (that is fragile headless).
Instead it exercises the pure functions of the pipeline:

- :func:`picked_entity_from_polydata` over the merged mesh.
- :func:`resolve_pick` and :func:`pick_entities_in_frustum`.
- :class:`ViewerSession` setters with signal verification.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import vtk


@pytest.fixture(scope="module")
def qt_app():
    try:
        from qtpy import QtWidgets
    except ImportError:
        pytest.skip("Qt not available.")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def _build_window(two_boxes_step: Path):
    from ladruno_gmsh import open_model
    from ladruno_gmsh.viewer.session import ViewerSession
    from ladruno_gmsh.viewer.window import MainWindow

    session = open_model(two_boxes_step, units="m")
    session.fragment_all(dim=3)
    session.remove_all_duplicates()
    viewer = ViewerSession(session)
    window = MainWindow(viewer)
    viewer.refresh_scene()
    return session, viewer, window


def test_merged_mesh_has_entity_uuid(qt_app, two_boxes_step: Path) -> None:
    """The merged mesh must carry ``entity_uuid`` per cell."""
    session, viewer, window = _build_window(two_boxes_step)
    try:
        merged = window.scene._merged
        assert merged is not None
        assert merged.n_cells > 0
        assert "entity_uuid" in merged.cell_data
        assert "dim" in merged.cell_data
        assert "tag" in merged.cell_data
        assert window.scene._cell_uuid is not None
        assert len(window.scene._cell_uuid) == merged.n_cells
    finally:
        window.win.close()
        session.close()


def test_resolve_pick_returns_valid_entity(qt_app, two_boxes_step: Path) -> None:
    """Given a valid cell_id, resolve_pick returns the entity."""
    from ladruno_gmsh.viewer.interaction import resolve_pick

    session, viewer, window = _build_window(two_boxes_step)
    try:
        merged = window.scene._merged
        assert merged is not None
        # Probe several cells
        for cell_id in (0, merged.n_cells // 2, merged.n_cells - 1):
            pick = resolve_pick(window.scene, cell_id)
            assert pick is not None, f"cell_id={cell_id} did not resolve"
            assert pick.entity_uuid
            assert pick.dim in (0, 1, 2, 3)
            assert pick.tag > 0
            # The uuid must exist in the document
            ent = session.document.find_by_uuid(pick.entity_uuid)
            assert ent is not None, f"uuid {pick.entity_uuid} not in doc"
    finally:
        window.win.close()
        session.close()


def test_resolve_pick_with_invalid_cell_returns_none(
    qt_app, two_boxes_step: Path,
) -> None:
    from ladruno_gmsh.viewer.interaction import resolve_pick

    session, viewer, window = _build_window(two_boxes_step)
    try:
        assert resolve_pick(window.scene, -1) is None
        assert resolve_pick(window.scene, 10_000_000) is None
    finally:
        window.win.close()
        session.close()


def test_set_multi_selection_emits_signal_and_recolors(
    qt_app, two_boxes_step: Path,
) -> None:
    """set_multi_selection must emit multiSelectionChanged and trigger
    the scene recolor."""
    session, viewer, window = _build_window(two_boxes_step)
    received = []
    try:
        viewer.multiSelectionChanged.connect(
            lambda: received.append(frozenset(viewer.multi_selection))
        )

        ent = session.volumes[0]
        viewer.set_multi_selection([ent.uuid])

        assert ent.uuid in viewer.multi_selection
        assert len(received) == 1
        assert ent.uuid in received[0]
    finally:
        window.win.close()
        session.close()


def test_box_pick_extracts_all_when_frustum_covers_scene(
    qt_app, two_boxes_step: Path,
) -> None:
    """A huge frustum centered on the model must include every surface
    entity (cells are triangles on surfaces)."""
    from ladruno_gmsh.viewer.interaction import pick_entities_in_frustum

    session, viewer, window = _build_window(two_boxes_step)
    try:
        merged = window.scene._merged
        assert merged is not None

        xmin, xmax, ymin, ymax, zmin, zmax = merged.bounds
        pad = max(abs(xmax - xmin), abs(ymax - ymin), abs(zmax - zmin)) * 10

        # Build 6 outward planes (normals pointing OUTWARD) so that
        # FunctionValue<=0 means inside the box.
        planes = vtk.vtkPlanes()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(xmin - pad, 0, 0)
        pts.InsertNextPoint(xmax + pad, 0, 0)
        pts.InsertNextPoint(0, ymin - pad, 0)
        pts.InsertNextPoint(0, ymax + pad, 0)
        pts.InsertNextPoint(0, 0, zmin - pad)
        pts.InsertNextPoint(0, 0, zmax + pad)
        norms = vtk.vtkDoubleArray()
        norms.SetNumberOfComponents(3)
        norms.InsertNextTuple3(-1, 0, 0)
        norms.InsertNextTuple3( 1, 0, 0)
        norms.InsertNextTuple3(0, -1, 0)
        norms.InsertNextTuple3(0,  1, 0)
        norms.InsertNextTuple3(0, 0, -1)
        norms.InsertNextTuple3(0, 0,  1)
        planes.SetPoints(pts)
        planes.SetNormals(norms)

        uuids = pick_entities_in_frustum(planes, window.scene)
        assert uuids is not None
        # Every scene entity must appear in the result
        scene_uuids = {str(u) for u in window.scene._cell_uuid}
        assert uuids == scene_uuids
    finally:
        window.win.close()
        session.close()


def test_box_pick_empty_when_frustum_outside(
    qt_app, two_boxes_step: Path,
) -> None:
    """A frustum far from the model captures no entities."""
    from ladruno_gmsh.viewer.interaction import pick_entities_in_frustum

    session, viewer, window = _build_window(two_boxes_step)
    try:
        merged = window.scene._merged
        xmin, _xmax, ymin, _ymax, zmin, _zmax = merged.bounds

        # Box far from the model
        far = max(abs(xmin), abs(ymin), abs(zmin)) * 100 + 1000
        planes = vtk.vtkPlanes()
        pts = vtk.vtkPoints()
        pts.InsertNextPoint(far, 0, 0)
        pts.InsertNextPoint(far + 1, 0, 0)
        pts.InsertNextPoint(0, far, 0)
        pts.InsertNextPoint(0, far + 1, 0)
        pts.InsertNextPoint(0, 0, far)
        pts.InsertNextPoint(0, 0, far + 1)
        norms = vtk.vtkDoubleArray()
        norms.SetNumberOfComponents(3)
        norms.InsertNextTuple3(-1, 0, 0)
        norms.InsertNextTuple3( 1, 0, 0)
        norms.InsertNextTuple3(0, -1, 0)
        norms.InsertNextTuple3(0,  1, 0)
        norms.InsertNextTuple3(0, 0, -1)
        norms.InsertNextTuple3(0, 0,  1)
        planes.SetPoints(pts)
        planes.SetNormals(norms)

        uuids = pick_entities_in_frustum(planes, window.scene)
        assert uuids is not None
        assert len(uuids) == 0
    finally:
        window.win.close()
        session.close()


def test_clear_multi_selection_emits(qt_app, two_boxes_step: Path) -> None:
    session, viewer, window = _build_window(two_boxes_step)
    received = []
    try:
        viewer.multiSelectionChanged.connect(
            lambda: received.append(len(viewer.multi_selection))
        )
        ent = session.volumes[0]
        viewer.set_multi_selection([ent.uuid])
        viewer.clear_multi_selection()
        assert len(viewer.multi_selection) == 0
        # At least two emissions: set and clear
        assert len(received) >= 2
    finally:
        window.win.close()
        session.close()


def test_hide_then_show_all_roundtrip(qt_app, two_boxes_step: Path) -> None:
    """Verify the hide -> show all roundtrip over the uuid set."""
    session, viewer, window = _build_window(two_boxes_step)
    try:
        ent = session.volumes[0]
        viewer.set_multi_selection([ent.uuid])
        viewer.hide_selected()
        assert ent.uuid in viewer.hidden
        viewer.show_all()
        assert len(viewer.hidden) == 0
    finally:
        window.win.close()
        session.close()


def test_explode_volume_returns_surfaces(qt_app, two_boxes_step: Path) -> None:
    """Exploding a volume returns its faces (dim=2)."""
    session, viewer, window = _build_window(two_boxes_step)
    try:
        vol = session.volumes[0]
        children = session.explode_selection([vol.uuid])
        assert len(children) > 0
        assert all(e.dim == 2 for e in children), (
            f"Expected dim=2 for all; got {[e.dim for e in children]}"
        )
    finally:
        window.win.close()
        session.close()


def test_explode_surface_returns_curves(qt_app, two_boxes_step: Path) -> None:
    """Exploding a surface returns its curves (dim=1)."""
    session, viewer, window = _build_window(two_boxes_step)
    try:
        if not session.surfaces:
            pytest.skip("No surfaces in the model.")
        surf = session.surfaces[0]
        children = session.explode_selection([surf.uuid])
        assert len(children) > 0
        assert all(e.dim == 1 for e in children)
    finally:
        window.win.close()
        session.close()


def test_explode_via_viewer_updates_selection(
    qt_app, two_boxes_step: Path,
) -> None:
    """viewer.explode_selected updates multi_selection with the boundary."""
    session, viewer, window = _build_window(two_boxes_step)
    try:
        vol = session.volumes[0]
        viewer.set_multi_selection([vol.uuid])
        assert vol.uuid in viewer.multi_selection
        viewer.explode_selected()
        # The selection must now contain surfaces, not the volume
        new_sel = set(viewer.multi_selection)
        assert vol.uuid not in new_sel
        assert len(new_sel) > 0
        for u in new_sel:
            e = session.document.find_by_uuid(u)
            assert e is not None and e.dim == 2
    finally:
        window.win.close()
        session.close()


def test_explode_empty_selection_noop(
    qt_app, two_boxes_step: Path,
) -> None:
    """Explode with no selection does not fail and does not change state."""
    session, viewer, window = _build_window(two_boxes_step)
    try:
        viewer.clear_multi_selection()
        viewer.explode_selected()  # must not raise
        assert len(viewer.multi_selection) == 0
    finally:
        window.win.close()
        session.close()
