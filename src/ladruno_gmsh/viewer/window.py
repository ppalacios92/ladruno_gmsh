"""Main window: docks, toolbars, layout."""
from __future__ import annotations

from .deps import require_dependencies
from .docks import (
    BooleanDock,
    ConsoleDock,
    DiagnosticsDock,
    ExportDock,
    HealingDock,
    HistoryDock,
    MeshDock,
    ModelTreeDock,
    PhysicalGroupsDock,
    PropertiesDock,
    QualityDock,
    ReorientDock,
)
from .interaction import (
    install_picking,
    install_rectangle_picking,
    restore_navigation_style,
)
from .multiview import CentralViewArea
from .scene import ViewerScene
from .status import StatusBar
from .theme import stylesheet
from .toolbars import build_main_toolbar, build_view_toolbar


class MainWindow:
    """Main viewer window.

    Hosts:

    - a central PyVista view,
    - a top toolbar with the most-used actions,
    - dockable panels on left and right,
    - a console at the bottom,
    - a status bar with information chips.
    """

    def __init__(self, viewer_session) -> None:
        deps = require_dependencies()
        QtCore = deps["QtCore"]
        QtWidgets = deps["QtWidgets"]

        self.viewer = viewer_session
        self.win = QtWidgets.QMainWindow()
        self.win.setWindowTitle(
            f"ladruno_gmsh — {viewer_session.api.model_name}"
        )
        self.win.resize(1400, 900)
        self.win.setStyleSheet(stylesheet())

        # Center: PyVista.
        self.central = CentralViewArea(self.win)
        self.win.setCentralWidget(self.central.widget)
        self.scene = ViewerScene(self.central.plotter, viewer_session.state)

        # Menubar.
        self._build_menubar()

        # Toolbars.
        self.toolbar = build_main_toolbar(self.win, viewer_session)
        self.win.addToolBar(QtCore.Qt.TopToolBarArea, self.toolbar)
        self.view_toolbar = build_view_toolbar(self.win, viewer_session)
        self.win.addToolBar(QtCore.Qt.TopToolBarArea, self.view_toolbar)

        # Status bar.
        self.status = StatusBar(self.win)
        self.win.setStatusBar(self.status.bar)

        # Docks.
        self.model_tree = ModelTreeDock(viewer_session, self.win)
        self.history = HistoryDock(viewer_session, self.win)
        self.properties = PropertiesDock(viewer_session, self.win)
        self.healing = HealingDock(viewer_session, self.win)
        self.boolean = BooleanDock(viewer_session, self.win)
        self.mesh = MeshDock(viewer_session, self.win)
        self.reorient = ReorientDock(viewer_session, self.win)
        self.quality = QualityDock(viewer_session, self.win)
        self.diagnostics = DiagnosticsDock(viewer_session, self.win)
        self.physical_groups = PhysicalGroupsDock(viewer_session, self.win)
        self.console = ConsoleDock(viewer_session, self.win)
        self.export = ExportDock(viewer_session, self.win)

        left = QtCore.Qt.LeftDockWidgetArea
        right = QtCore.Qt.RightDockWidgetArea
        bottom = QtCore.Qt.BottomDockWidgetArea
        self.win.addDockWidget(left, self.model_tree.dock)
        self.win.addDockWidget(left, self.history.dock)
        self.win.tabifyDockWidget(self.model_tree.dock, self.history.dock)

        self.win.addDockWidget(right, self.properties.dock)
        self.win.addDockWidget(right, self.healing.dock)
        self.win.addDockWidget(right, self.boolean.dock)
        self.win.addDockWidget(right, self.mesh.dock)
        self.win.addDockWidget(right, self.reorient.dock)
        self.win.addDockWidget(right, self.quality.dock)
        self.win.addDockWidget(right, self.diagnostics.dock)
        self.win.addDockWidget(right, self.physical_groups.dock)
        self.win.addDockWidget(right, self.export.dock)
        for d in (self.healing.dock, self.boolean.dock, self.mesh.dock,
                  self.reorient.dock, self.quality.dock,
                  self.diagnostics.dock, self.physical_groups.dock,
                  self.export.dock):
            self.win.tabifyDockWidget(self.properties.dock, d)
        self.properties.dock.raise_()

        self.win.addDockWidget(bottom, self.console.dock)

        # Signal wiring.
        viewer_session.sceneRefreshed.connect(self._on_scene_refreshed)
        viewer_session.documentChanged.connect(self._on_document_changed)
        viewer_session.statusMessage.connect(self.status.show_message)
        viewer_session.busyChanged.connect(self._on_busy_changed)
        viewer_session.selectionChanged.connect(self._on_selection_changed)
        viewer_session.multiSelectionChanged.connect(self._apply_colors)
        viewer_session.booleanSlotsChanged.connect(self._apply_colors)
        viewer_session.documentChanged.connect(
            self.viewer.clear_boolean_slots
        )
        viewer_session.cameraResetRequested.connect(self._on_camera_reset)
        viewer_session.cameraViewRequested.connect(self._on_camera_view)
        viewer_session.orthographicToggled.connect(self.scene.set_orthographic)
        viewer_session.boxSelectionToggled.connect(self._on_box_toggle)
        viewer_session.opacityChanged.connect(self.scene.set_opacity)
        viewer_session.nodeSizeChanged.connect(self.scene.set_mesh_node_size)
        viewer_session.visibilityChanged.connect(self._apply_colors)

        # Scene picking.
        install_picking(self.central.plotter, viewer_session, self.scene)

        # Global shortcuts.
        self._install_shortcuts()

        # Paint initial state.
        self.status.update_from(viewer_session.api)

    def _install_shortcuts(self) -> None:
        deps = require_dependencies()
        QtGui = deps["QtGui"]
        QtWidgets = deps["QtWidgets"]
        QtCore = deps["QtCore"]

        def shortcut(seq: str, slot):
            sc = QtWidgets.QShortcut(QtGui.QKeySequence(seq), self.win)
            sc.setContext(QtCore.Qt.ApplicationShortcut)
            sc.activated.connect(slot)
            return sc

        # Shortcuts NOT bound to a menu QAction (to avoid Qt's
        # "Ambiguous shortcut overload" warnings). Delete, Ctrl+Z, Esc,
        # H, Shift+H, I, Ctrl+Shift+A and Shift+S are bound to their
        # menu actions instead.
        self._sc_box = shortcut("B", self.viewer.toggle_box_selection)
        self._sc_ortho = shortcut("O", self.viewer.toggle_orthographic)
        self._sc_top = shortcut("Ctrl+1",
                                lambda: self.viewer.set_camera_view("top"))
        self._sc_front = shortcut("Ctrl+2",
                                  lambda: self.viewer.set_camera_view("front"))
        self._sc_right = shortcut("Ctrl+3",
                                  lambda: self.viewer.set_camera_view("right"))
        self._sc_iso = shortcut("Ctrl+0",
                                lambda: self.viewer.set_camera_view("iso"))
        self._sc_explode = shortcut("X", self.viewer.explode_selected)

    def _clear_selection_and_box(self) -> None:
        """Esc shortcut: clear selection and leave box-select mode."""
        self.viewer.clear_multi_selection()
        self.viewer.set_selection(None)
        if self.viewer.state.box_selection:
            self.viewer.toggle_box_selection()
        self.viewer.statusMessage.emit("Selection cleared.")

    def _build_menubar(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        QtGui = deps["QtGui"]

        bar = self.win.menuBar()
        m_file = bar.addMenu("&File")

        a_open = m_file.addAction("Open STEP/IGES/STL...")
        a_open.setShortcut(QtGui.QKeySequence("Ctrl+O"))
        a_open.triggered.connect(self._action_open_new)

        a_add = m_file.addAction("Add file to current model...")
        a_add.setShortcut(QtGui.QKeySequence("Ctrl+Shift+O"))
        a_add.triggered.connect(self._action_add_file)

        m_file.addSeparator()

        a_save_p = m_file.addAction("Save project (.ladruno)...")
        a_save_p.setShortcut(QtGui.QKeySequence("Ctrl+S"))
        a_save_p.triggered.connect(self._action_save_project)

        a_open_p = m_file.addAction("Open project...")
        a_open_p.triggered.connect(self._action_open_project_info)

        m_file.addSeparator()

        a_exit = m_file.addAction("Close window")
        a_exit.triggered.connect(self.win.close)

        m_edit = bar.addMenu("&Edit")
        a_undo = m_edit.addAction("Undo")
        a_undo.setShortcut(QtGui.QKeySequence("Ctrl+Z"))
        a_undo.triggered.connect(self.viewer.undo)
        a_del = m_edit.addAction("Delete selected")
        a_del.setShortcut(QtGui.QKeySequence("Delete"))
        a_del.triggered.connect(self.viewer.delete_selected)
        a_esc = m_edit.addAction("Clear selection")
        a_esc.setShortcut(QtGui.QKeySequence("Escape"))
        a_esc.triggered.connect(self._clear_selection_and_box)

        m_view = bar.addMenu("&Visibility")
        a_hide = m_view.addAction("Hide selected")
        a_hide.setShortcut(QtGui.QKeySequence("H"))
        a_hide.triggered.connect(self.viewer.hide_selected)
        a_hide_other = m_view.addAction("Hide unselected")
        a_hide_other.setShortcut(QtGui.QKeySequence("Shift+H"))
        a_hide_other.triggered.connect(self.viewer.hide_unselected)
        a_iso = m_view.addAction("Isolate selected")
        a_iso.setShortcut(QtGui.QKeySequence("I"))
        a_iso.triggered.connect(self.viewer.isolate_selected)
        m_view.addSeparator()
        a_show_sel = m_view.addAction("Show selected")
        a_show_sel.setShortcut(QtGui.QKeySequence("Shift+S"))
        a_show_sel.triggered.connect(self.viewer.show_selected)
        a_show_all = m_view.addAction("Show all")
        a_show_all.setShortcut(QtGui.QKeySequence("Ctrl+Shift+A"))
        a_show_all.triggered.connect(self.viewer.show_all)

    def _action_open_new(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.win, "Open model",
            "", "CAD/Mesh (*.step *.stp *.iges *.igs *.brep *.stl *.msh)",
        )
        if not path:
            return
        QtWidgets.QMessageBox.information(
            self.win, "Open",
            "To open in a clean session, run in Python:\n\n"
            f"  from ladruno_gmsh import open_model\n"
            f"  session = open_model(r'{path}')\n\n"
            "Hot-swapping the active model is not supported in this version."
        )

    def _action_add_file(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.win, "Add file to current session",
            "", "CAD/Mesh (*.step *.stp *.iges *.igs *.brep *.stl *.msh)",
        )
        if not path:
            return
        self.viewer.run_method("merge", path)

    def _action_save_project(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.win, "Save project",
            "", "ladruno project (*.ladruno *.lgmsh)",
        )
        if not path:
            return
        from ..io.project import save as _save
        try:
            out = _save(self.viewer.api, path)
        except Exception as exc:
            self.viewer.statusMessage.emit(f"Save failed: {exc}")
            return
        self.viewer.statusMessage.emit(f"Project saved: {out}")

    def _action_open_project_info(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.win, "Open project",
            "", "ladruno project (*.ladruno *.lgmsh)",
        )
        if not path:
            return
        QtWidgets.QMessageBox.information(
            self.win, "Open project",
            "To replay the project in a clean session, run:\n\n"
            f"  from ladruno_gmsh.io.project import load\n"
            f"  session = load(r'{path}')\n\n"
            "Hot-swapping the active session is not supported in this version."
        )

    def show(self) -> None:
        self.win.show()

    # ── Slots ───────────────────────────────────────────────────────

    def _on_scene_refreshed(self) -> None:
        self.scene.render(self.viewer.scene_snapshot)
        self.status.update_from(self.viewer.api)
        self._apply_colors()
        # If we were still in box mode, actors have just changed; we
        # must reinstall the picker so it targets the new ones. Without
        # this, after a delete/mesh the picker stays dangling and the
        # user cannot orbit or leave the mode.
        if self.viewer.state.box_selection:
            try:
                self._box_picker = install_rectangle_picking(
                    self.central.plotter, self.viewer, self.scene,
                )
            except Exception as exc:
                self.viewer.statusMessage.emit(
                    f"box: reinstall after refresh failed: {exc}"
                )

    def _apply_colors(self) -> None:
        self.scene.recolor(
            multi_selection=self.viewer.multi_selection,
            boolean_object=self.viewer.boolean_object,
            boolean_tool=self.viewer.boolean_tool,
            hidden=self.viewer.hidden,
        )

    def _on_document_changed(self) -> None:
        self.status.update_from(self.viewer.api)

    def _on_busy_changed(self, busy: bool) -> None:
        deps = require_dependencies()
        QtCore = deps["QtCore"]
        QtWidgets = deps["QtWidgets"]
        if busy:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        else:
            QtWidgets.QApplication.restoreOverrideCursor()

    def _on_selection_changed(self, picked) -> None:
        # The red / blue / orange tint is managed by _apply_colors via
        # multiSelectionChanged. Nothing extra to do here; the
        # PropertiesDock updates through its own connection.
        pass

    def _on_camera_reset(self) -> None:
        # Routed through scene.reset_camera so the first-render flag is
        # cleared and future refreshes do not reframe.
        try:
            self.scene.reset_camera()
        except Exception:
            pass

    def _on_camera_view(self, name: str) -> None:
        plotter = self.central.plotter
        try:
            method = {
                "top":    plotter.view_xy,
                "bottom": lambda: (plotter.view_xy(negative=True)
                                   if "negative" in
                                   plotter.view_xy.__doc__.lower()
                                   else plotter.view_xy()),
                "front":  plotter.view_xz,
                "back":   lambda: plotter.view_xz(),
                "left":   lambda: plotter.view_yz(),
                "right":  plotter.view_yz,
                "iso":    plotter.view_isometric,
            }[name]
            method()
        except Exception:
            try:
                plotter.reset_camera()
            except Exception:
                pass

    def _on_box_toggle(self, on: bool) -> None:
        if on:
            self._box_picker = install_rectangle_picking(
                self.central.plotter, self.viewer, self.scene,
            )
        else:
            try:
                self.central.plotter.disable_picking()
            except Exception:
                pass
            self._box_picker = None
            restore_navigation_style(self.central.plotter, self.viewer)
            install_picking(self.central.plotter, self.viewer, self.scene)
