"""ViewerSession: orchestrates the model, the worker, the scene, and the docks."""
from __future__ import annotations

import traceback
from typing import Any, Iterable, Optional

from ..bridge import (
    SceneSnapshot,
    mesh_to_unstructured_grid,
    tessellate,
)
from ..bridge.picker import PickedEntity
from ..bridge.tessellator import TessellationParameters
from .deps import require_dependencies
from .state import ViewerState


def _qt():
    return require_dependencies()


class ViewerSession:
    """Bridge between :class:`api.Session` and the Qt layer.

    It exposes a ``QObject`` so signals can be emitted. Operations run
    synchronously on the main thread; ``busyChanged`` lets docks
    display visual feedback during long-running operations.
    """

    def __init__(self, api_session) -> None:
        deps = _qt()
        QtCore = deps["QtCore"]

        class _Bridge(QtCore.QObject):
            documentChanged = QtCore.Signal()
            sceneRefreshed = QtCore.Signal()
            selectionChanged = QtCore.Signal(object)
            multiSelectionChanged = QtCore.Signal()
            booleanSlotsChanged = QtCore.Signal()
            statusMessage = QtCore.Signal(str)
            busyChanged = QtCore.Signal(bool)
            logAppended = QtCore.Signal(str)
            cameraResetRequested = QtCore.Signal()
            cameraViewRequested = QtCore.Signal(str)
            orthographicToggled = QtCore.Signal(bool)
            boxSelectionToggled = QtCore.Signal(bool)
            saveStepRequested = QtCore.Signal()
            opacityChanged = QtCore.Signal(float)
            nodeSizeChanged = QtCore.Signal(float)
            visibilityChanged = QtCore.Signal()

        self._bridge = _Bridge()
        self.documentChanged = self._bridge.documentChanged
        self.sceneRefreshed = self._bridge.sceneRefreshed
        self.selectionChanged = self._bridge.selectionChanged
        self.multiSelectionChanged = self._bridge.multiSelectionChanged
        self.booleanSlotsChanged = self._bridge.booleanSlotsChanged
        self.statusMessage = self._bridge.statusMessage
        self.busyChanged = self._bridge.busyChanged
        self.logAppended = self._bridge.logAppended
        self.cameraResetRequested = self._bridge.cameraResetRequested
        self.cameraViewRequested = self._bridge.cameraViewRequested
        self.orthographicToggled = self._bridge.orthographicToggled
        self.boxSelectionToggled = self._bridge.boxSelectionToggled
        self.saveStepRequested = self._bridge.saveStepRequested
        self.opacityChanged = self._bridge.opacityChanged
        self.nodeSizeChanged = self._bridge.nodeSizeChanged
        self.visibilityChanged = self._bridge.visibilityChanged

        self.api = api_session
        self.state = ViewerState()
        self.scene_snapshot = SceneSnapshot()
        self._selection: Optional[PickedEntity] = None
        self._multi_selection: set[str] = set()
        self._boolean_object: set[str] = set()
        self._boolean_tool: set[str] = set()
        self._hidden: set[str] = set()

    # ── Accessors ───────────────────────────────────────────────────

    @property
    def entities(self):
        return self.api.entities

    @property
    def units(self):
        return self.api.units

    @property
    def tolerance(self):
        return self.api.tolerance

    @property
    def mesh_snapshot(self):
        return self.api.mesh_snapshot

    @property
    def selection(self) -> Optional[PickedEntity]:
        return self._selection

    def set_selection(self, picked: Optional[PickedEntity]) -> None:
        self._selection = picked
        self.state.selection_uuid = picked.entity_uuid if picked else None
        self.selectionChanged.emit(picked)

    # ── Multi-selection (the entities tinted red) ───────────────────

    @property
    def multi_selection(self) -> frozenset[str]:
        return frozenset(self._multi_selection)

    def set_multi_selection(self, uuids: Iterable[str]) -> None:
        new = {str(u) for u in uuids}
        if new == self._multi_selection:
            return
        self._multi_selection = new
        self.multiSelectionChanged.emit()

    def add_multi_selection(self, uuids: Iterable[str]) -> None:
        new = self._multi_selection | {str(u) for u in uuids}
        self.set_multi_selection(new)

    def toggle_multi_selection(self, uuid: str) -> None:
        u = str(uuid)
        new = set(self._multi_selection)
        if u in new:
            new.discard(u)
        else:
            new.add(u)
        self.set_multi_selection(new)

    def clear_multi_selection(self) -> None:
        self.set_multi_selection([])

    def get_selected_entities(self) -> list:
        """Resolve the multi-selection against the document.

        If the multi-selection is empty, fall back to the single picked
        entity.
        """
        doc = self.api.document
        ents = []
        for u in self._multi_selection:
            e = doc.find_by_uuid(u)
            if e is not None:
                ents.append(e)
        if ents:
            return ents
        if self._selection is not None:
            e = doc.find_by_uuid(self._selection.entity_uuid)
            return [e] if e is not None else []
        return []

    # ── Boolean slots (blue / orange tint) ──────────────────────────

    @property
    def boolean_object(self) -> frozenset[str]:
        return frozenset(self._boolean_object)

    @property
    def boolean_tool(self) -> frozenset[str]:
        return frozenset(self._boolean_tool)

    def set_boolean_object(self, uuids: Iterable[str]) -> None:
        new = {str(u) for u in uuids}
        if new == self._boolean_object:
            return
        self._boolean_object = new
        self.booleanSlotsChanged.emit()

    def set_boolean_tool(self, uuids: Iterable[str]) -> None:
        new = {str(u) for u in uuids}
        if new == self._boolean_tool:
            return
        self._boolean_tool = new
        self.booleanSlotsChanged.emit()

    def clear_boolean_slots(self) -> None:
        if not self._boolean_object and not self._boolean_tool:
            return
        self._boolean_object = set()
        self._boolean_tool = set()
        self.booleanSlotsChanged.emit()

    # ── Entity visibility ───────────────────────────────────────────

    @property
    def hidden(self) -> frozenset[str]:
        return frozenset(self._hidden)

    def _set_hidden(self, uuids) -> None:
        new = {str(u) for u in uuids}
        if new == self._hidden:
            return
        self._hidden = new
        self.visibilityChanged.emit()

    def hide_selected(self) -> None:
        ents = self.get_selected_entities()
        if not ents:
            self.statusMessage.emit("Nothing selected to hide.")
            return
        self._set_hidden(self._hidden | {e.uuid for e in ents})
        self.statusMessage.emit(
            f"Hidden {len(ents)} entities (total hidden: {len(self._hidden)})."
        )

    def hide_unselected(self) -> None:
        ents = self.get_selected_entities()
        if not ents:
            self.statusMessage.emit(
                "Select first to hide the rest."
            )
            return
        keep = {e.uuid for e in ents}
        all_uuids = {e.uuid for e in self.api.document.entities}
        self._set_hidden(all_uuids - keep)
        self.statusMessage.emit(
            f"Hidden {len(self._hidden)} entities, visible {len(keep)}."
        )

    def isolate_selected(self) -> None:
        """Revit-style alias for hide_unselected."""
        self.hide_unselected()

    def show_selected(self) -> None:
        ents = self.get_selected_entities()
        if not ents:
            self.statusMessage.emit("Nothing selected to show.")
            return
        self._set_hidden(self._hidden - {e.uuid for e in ents})
        self.statusMessage.emit(
            f"Showed {len(ents)} entities."
        )

    def show_all(self) -> None:
        if not self._hidden:
            return
        self._set_hidden(set())
        self.statusMessage.emit("All entities visible.")

    # ── Operations ──────────────────────────────────────────────────

    _MESH_METHODS = frozenset({
        "mesh", "refine_mesh", "set_order", "optimize_mesh",
        "recombine_mesh", "clear_mesh", "mesh_size_from_curvature",
    })

    def run_method(self, method: str, *args, **kwargs) -> Any:
        """Invoke ``api.<method>(*args, **kwargs)`` and emit signals."""
        self.busyChanged.emit(True)
        try:
            fn = getattr(self.api, method)
            result = fn(*args, **kwargs)
        except Exception as exc:
            self.statusMessage.emit(f"{method} failed: {exc}")
            self._append_log(traceback.format_exc())
            self.busyChanged.emit(False)
            return None
        finally:
            self._drain_gmsh_log()
        self.busyChanged.emit(False)
        self.documentChanged.emit()

        is_mesh_op = method in self._MESH_METHODS
        if is_mesh_op and method != "clear_mesh":
            self.state.show_mesh = True
        self.refresh_scene(with_mesh=self.state.show_mesh)

        m = self.api.mesh_snapshot
        if is_mesh_op and not m.is_empty:
            self.statusMessage.emit(
                f"{method} OK   ({m.n_nodes} nodes, {m.n_elements} elements, "
                f"dim={m.max_dim}, order={m.order})"
            )
        else:
            self.statusMessage.emit(f"{method} OK")
        return result

    def refresh_scene(self,
                      *,
                      with_mesh: Optional[bool] = None,
                      tess_params: Optional[TessellationParameters] = None
                      ) -> None:
        """Rebuild the :class:`SceneSnapshot`.

        - If the current gmsh mesh has 2D elements they are reused (not
          destroyed) — this preserves the FEM mesh the user just
          generated.
        - The ``UnstructuredGrid`` with the volumetric mesh is only
          built when ``with_mesh`` is ``True`` and a mesh exists.
        """
        self.busyChanged.emit(True)
        try:
            params = tess_params or TessellationParameters(
                target_size=self.state.tess_target_size,
                size_factor=self.state.tess_size_factor,
                elements_per_2pi=self.state.tess_elements_per_2pi,
            )
            # If the user already ran an explicit mesh.* operation we
            # do NOT let the viewer's tessellator generate 2D elements
            # on its own: that would contaminate the FEM mesh
            # (e.g. mesh(dim=1) would end up with triangles in gmsh
            # that are not in mesh_snapshot).
            respect = not self.api.mesh_snapshot.is_empty
            geom = tessellate(self.api.document, params,
                              respect_user_mesh=respect)
            grid = None
            show_mesh = with_mesh if with_mesh is not None else self.state.show_mesh
            if show_mesh and not self.api.mesh_snapshot.is_empty:
                grid = mesh_to_unstructured_grid()
            self.scene_snapshot = SceneSnapshot(
                geometry=geom,
                mesh_grid=grid,
                info={
                    "entity_count": len(geom),
                    "mesh_nodes": self.api.mesh_snapshot.n_nodes,
                    "mesh_elements": self.api.mesh_snapshot.n_elements,
                },
            )
        finally:
            self.busyChanged.emit(False)
        self._drain_gmsh_log()
        self.sceneRefreshed.emit()

    # ── Diagnostics helpers ─────────────────────────────────────────

    def show_quality(self) -> None:
        q = self.api.diagnostics.quality(metric=self.state.quality_metric)
        self.statusMessage.emit(
            f"Quality {q.metric}: min={q.min:.3f}, median={q.median:.3f}, "
            f"max={q.max:.3f}, n={q.count}"
        )

    def show_report(self) -> None:
        rep = self.api.diagnostics.report()
        text = rep.as_markdown()
        self.logAppended.emit("\n" + text + "\n")
        self.statusMessage.emit(
            "Report: " + ("OK" if rep.ok else "FINDINGS")
        )

    def reset_camera(self) -> None:
        self.cameraResetRequested.emit()

    def set_camera_view(self, name: str) -> None:
        """``name`` accepts ``top|bottom|front|back|left|right|iso``."""
        self.cameraViewRequested.emit(name)

    def toggle_orthographic(self) -> None:
        new = not self.state.orthographic
        self.state.orthographic = new
        self.orthographicToggled.emit(new)
        self.statusMessage.emit(
            "Projection: orthographic" if new else "Projection: perspective"
        )

    def toggle_box_selection(self) -> None:
        new = not getattr(self.state, "box_selection", False)
        self.state.box_selection = new
        self.boxSelectionToggled.emit(new)
        self.statusMessage.emit(
            "Box select on (left-drag)" if new
            else "Box select off"
        )

    def toggle_sticky_selection(self) -> None:
        new = not getattr(self.state, "sticky_selection", False)
        self.state.sticky_selection = new
        self.statusMessage.emit(
            "Sticky select: each click ADDS" if new
            else "Sticky select OFF: click replaces"
        )

    # ── Aggregate actions (delete, undo, export step) ───────────────

    def delete_selected(self) -> None:
        ents = self.get_selected_entities()
        if not ents:
            self.statusMessage.emit("Nothing selected to delete.")
            return
        self.run_method("remove_entities", entities=tuple(e.uuid for e in ents))
        self.clear_multi_selection()

    def explode_selected(self) -> None:
        """Break the selected entities: delete the parent and keep the
        boundary alive (volume -> faces, face -> edges, etc.).

        Routed through ``run_method`` so the operation lands in the
        history, the document is rebuilt and the scene is refreshed.
        """
        ents = self.get_selected_entities()
        if not ents:
            self.statusMessage.emit("Nothing to explode.")
            return
        children = self.run_method(
            "explode",
            entities=tuple(e.uuid for e in ents),
        )
        if not children:
            self.statusMessage.emit(
                "No boundary (could be dim 0 or isolated entities)."
            )
            return
        self.set_multi_selection([e.uuid for e in children])
        kinds = sorted({e.kind for e in children})
        self.statusMessage.emit(
            f"Explode: {len(ents)} -> {len(children)} entities "
            f"({', '.join(kinds)})."
        )

    def undo(self) -> None:
        ok = self.run_method("undo")
        if not ok:
            self.statusMessage.emit("Nothing to undo.")

    def export_unified_step(self) -> None:
        """Ask for a path, fuse volumes and export to STEP.

        **Destructive** operation: it breaks mesh conformity. The
        warning is emitted via statusMessage before running.
        """
        deps = _qt()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None, "Export unified STEP", "", "STEP (*.step *.stp)",
        )
        if not path:
            return
        self.statusMessage.emit(
            "Destructive unify: mesh conformity is lost."
        )
        self.run_method("unify_all_solids", dim=3)
        self.run_method("export", path)

    # ── Internals ───────────────────────────────────────────────────

    def _drain_gmsh_log(self) -> None:
        from ..kernel.session import session as _session
        try:
            lines = _session().drain_log()
        except Exception:
            return
        if lines:
            self._append_log("\n".join(lines))

    def _append_log(self, text: str) -> None:
        if text:
            self.logAppended.emit(text)


def launch(api_session, *, blocking: bool = True):
    """Create (or reuse) the ``QApplication`` and show the main window."""
    deps = _qt()
    QtCore = deps["QtCore"]
    QtGui = deps["QtGui"]
    QtWidgets = deps["QtWidgets"]
    from .window import MainWindow

    existing = QtWidgets.QApplication.instance()
    owned = existing is None
    if owned:
        # High-DPI: on Windows with display scaling > 100%, picking
        # coordinates diverge from logical Qt coordinates and clicks
        # register on cells far from where the user clicked. These
        # attributes must be set BEFORE QApplication is instantiated.
        for attr_name in ("AA_EnableHighDpiScaling", "AA_UseHighDpiPixmaps"):
            attr = getattr(QtCore.Qt, attr_name, None)
            if attr is not None:
                try:
                    QtCore.QCoreApplication.setAttribute(attr, True)
                except Exception:
                    pass
        try:
            policy = QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
            QtGui.QGuiApplication.setHighDpiScaleFactorRoundingPolicy(policy)
        except Exception:
            pass
    app = existing or QtWidgets.QApplication([])

    viewer = ViewerSession(api_session)
    window = MainWindow(viewer)
    window.show()
    viewer.refresh_scene()

    if blocking:
        app.exec_()
    return window if not owned else (window, app)
