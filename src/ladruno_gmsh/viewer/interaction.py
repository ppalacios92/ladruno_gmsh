"""Interaction styles, picking and selection modes.

Policy: **delegate as much as possible to pyvista** for standard
click-pick. We only take direct VTK observer control when the user
turns on box-select mode.

- **Navigation** (default): ``plotter.enable_mesh_picking`` with
  ``left_clicking=True``. PyVista distinguishes click vs drag
  internally and only calls our callback for real clicks. PyVista's
  wrapped style (TrackballCamera with a ``_parent`` weakref) is
  preserved.
- **Box-select** (toggle B): we switch to
  ``vtkInteractorStyleRubberBandPick`` forced into Select mode. The
  left-drag draws the rectangle; on release,
  ``vtkAreaPicker.GetFrustum()`` plus a test against ``cell_centers``
  identifies the entities (we do NOT use ``vtkExtractGeometry`` because
  the numpy-object -> vtkStringArray conversion does not survive that
  pipeline).
- **ESC**: a ``KeyPressEvent`` observer that is always active.

Every step emits ``statusMessage`` so the user can see in the status
bar what is happening (click hit/miss, frustum size, etc.).
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import vtk

from ..bridge.picker import picked_entity_from_polydata
from .deps import require_dependencies


_KEYPRESS_OBSERVERS: dict[int, list[int]] = {}
_PRESS_OBSERVERS: dict[int, list[int]] = {}


def _add_press_observer(iren, callback) -> None:
    """Install a LeftButtonPressEvent observer with high priority so it
    runs before pyvista's click/drag heuristic."""
    key = id(iren)
    for obs_id in _PRESS_OBSERVERS.get(key, []):
        try:
            iren.RemoveObserver(obs_id)
        except Exception:
            pass
    _PRESS_OBSERVERS[key] = []
    obs_id = iren.AddObserver("LeftButtonPressEvent", callback, 10.0)
    _PRESS_OBSERVERS[key].append(obs_id)


def install_picking(plotter, viewer_session, scene=None) -> None:
    """Navigation mode: pyvista point pick + ESC observer.

    Capture Ctrl/Shift modifiers at button-press time so the
    toggle/add/replace decision is reliable even when pyvista's
    callback fires later — by then ``QApplication.keyboardModifiers()``
    may no longer report the keys as held down.
    """
    deps = require_dependencies()
    QtCore = deps["QtCore"]
    QtWidgets = deps["QtWidgets"]

    iren = plotter.iren.interactor

    try:
        plotter.disable_picking()
    except Exception:
        pass

    # PRESS observer that stashes the active modifiers in the viewer
    # state. Runs before pyvista's click/drag heuristic.
    def _capture_modifiers(_o, _e):
        mods = QtWidgets.QApplication.keyboardModifiers()
        viewer_session.state.last_click_modifiers = int(mods)

    _add_press_observer(iren, _capture_modifiers)

    def _on_pick(picked_mesh, picker=None):
        mods_int = int(viewer_session.state.last_click_modifiers)
        is_ctrl = bool(mods_int & int(QtCore.Qt.ControlModifier))
        is_shift = bool(mods_int & int(QtCore.Qt.ShiftModifier))
        sticky = bool(viewer_session.state.sticky_selection)

        if picked_mesh is None:
            viewer_session.statusMessage.emit("click: no hit")
            if not (is_ctrl or is_shift or sticky):
                viewer_session.clear_multi_selection()
                viewer_session.set_selection(None)
            return

        # Verify that the picked mesh is the entity merged polydata
        # (has entity_uuid in cell_data). If not, most likely a
        # secondary actor without that metadata was activated; trusting
        # it would yield a bad cell_id and we would highlight "something
        # else".
        try:
            has_uuid = ("entity_uuid" in picked_mesh.cell_data
                        or "entity_idx" in picked_mesh.cell_data)
        except Exception:
            has_uuid = False
        if not has_uuid:
            viewer_session.statusMessage.emit(
                "click: actor without entity_uuid "
                "(check pickable=False on secondary actors)"
            )
            return

        # Resolve the cell id from whichever picker actually fired.
        # PyVista versions differ in whether they pass ``picker=`` to the
        # callback. Defaulting to ``cell_id = 0`` was wrong: every miss
        # selected the first cell of the picked polydata (visually far
        # from the click).
        cell_id = -1
        for src in (picker,
                    getattr(plotter, "picker", None),
                    getattr(getattr(plotter, "iren", None), "picker", None)):
            if src is None:
                continue
            try:
                cid = int(src.GetCellId())
            except Exception:
                continue
            if cid >= 0:
                cell_id = cid
                break
        if cell_id < 0:
            viewer_session.statusMessage.emit("click: picker has no cell id")
            return
        pick = picked_entity_from_polydata(picked_mesh, cell_id)
        if pick is None and scene is not None:
            cell_uuid = getattr(scene, "_cell_uuid", None)
            merged = getattr(scene, "_merged", None)
            if (cell_uuid is not None and merged is not None
                    and picked_mesh is merged):
                if 0 <= cell_id < len(cell_uuid):
                    try:
                        dim = int(merged.cell_data["dim"][cell_id])
                        tag = int(merged.cell_data["tag"][cell_id])
                        from ..bridge.picker import PickedEntity
                        pick = PickedEntity(
                            entity_uuid=str(cell_uuid[cell_id]),
                            dim=dim, tag=tag,
                        )
                    except Exception:
                        pick = None
        if pick is None:
            viewer_session.statusMessage.emit(
                f"click: cell={cell_id} has no entity_uuid"
            )
            return

        # If the click fell on a hidden entity (isolate), behave as a
        # miss: hidden entities cannot be selected.
        if pick.entity_uuid in viewer_session.hidden:
            viewer_session.statusMessage.emit(
                f"click: ({pick.dim},{pick.tag}) hidden (isolate)"
            )
            if not (is_ctrl or is_shift or sticky):
                viewer_session.clear_multi_selection()
                viewer_session.set_selection(None)
            return

        if is_ctrl:
            viewer_session.toggle_multi_selection(pick.entity_uuid)
            mode = "toggle"
        elif is_shift or sticky:
            viewer_session.add_multi_selection([pick.entity_uuid])
            mode = "add" if not sticky else "sticky"
        else:
            viewer_session.set_multi_selection([pick.entity_uuid])
            mode = "replace"
        viewer_session.set_selection(pick)
        viewer_session.statusMessage.emit(
            f"click {mode}: ({pick.dim},{pick.tag}) "
            f"-> {len(viewer_session.multi_selection)} total"
        )

    # Order of preference:
    #   1. ``picker='cell'`` — ray-cast against the actual cells.
    #      Works well with the translucent CAD shell because it
    #      ignores alpha and keeps the cell physically closest to the
    #      click ray. This is what the user expects ("I click here ->
    #      I select THIS face").
    #   2. ``picker='hardware'`` — fallback. Reads the rendered pixel;
    #      with a translucent shell or many actors in front it can
    #      return the wrong cell.
    #   3. Minimal call — for pyvista versions that reject these kwargs.
    picked_ok = False
    for kw in (
        dict(callback=_on_pick, left_clicking=True, show=False,
             show_message=False, use_actor=False, picker='cell'),
        dict(callback=_on_pick, left_clicking=True, show=False,
             show_message=False, use_actor=False, picker='hardware'),
        dict(callback=_on_pick, left_clicking=True, show=False,
             show_message=False, use_actor=False),
        dict(callback=_on_pick, show=False, show_message=False,
             use_actor=False),
    ):
        try:
            plotter.enable_mesh_picking(**kw)
            picker_kind = kw.get("picker", "default")
            viewer_session.statusMessage.emit(
                f"Picking installed: picker={picker_kind}, "
                f"left_clicking={kw.get('left_clicking', False)}"
            )
            picked_ok = True
            break
        except TypeError:
            continue
        except Exception:
            continue
    if not picked_ok:
        viewer_session.statusMessage.emit(
            "Could not install picking. Check your pyvista version."
        )

    _attach_keypress(plotter.iren.interactor, viewer_session)


def install_rectangle_picking(plotter, viewer_session, scene) -> object:
    """Box-select mode via pyvista's native API.

    Implements the AutoCAD / SolidWorks convention:

    - **Left -> right** drag ("window"): selects only entities
      **fully inside** the rectangle.
    - **Right -> left** drag ("crossing"): selects entities that
      **touch** the rectangle, even if only one face is visible.

    PyVista resolves the frustum for us via
    ``enable_rectangle_through_picking``. We manually capture the press
    and release positions of the left button on the ``iren`` to know
    the drag direction (the API does not expose this).
    """
    deps = require_dependencies()
    QtCore = deps["QtCore"]

    try:
        plotter.disable_picking()
    except Exception:
        pass

    iren = plotter.iren.interactor

    # Remove observers from any previous install so we do not stack.
    for obs_id in getattr(viewer_session, "_box_observers", []) or []:
        try:
            iren.RemoveObserver(obs_id)
        except Exception:
            pass
    viewer_session._box_observers = []

    # Capture drag start/end coordinates to decide
    # window (drag right) vs crossing (drag left).
    drag_state = {"start_x": 0, "start_y": 0,
                  "end_x": 0, "end_y": 0,
                  "mode": "crossing"}

    def _on_press(_o, _e):
        try:
            x, y = iren.GetEventPosition()
            drag_state["start_x"] = int(x)
            drag_state["start_y"] = int(y)
        except Exception:
            pass

    def _on_release(_o, _e):
        try:
            x, y = iren.GetEventPosition()
            drag_state["end_x"] = int(x)
            drag_state["end_y"] = int(y)
            # AutoCAD: end.x >= start.x -> window (drag right)
            #           end.x  < start.x -> crossing (drag left)
            drag_state["mode"] = (
                "window" if drag_state["end_x"] >= drag_state["start_x"]
                else "crossing"
            )
        except Exception:
            pass

    box_observers: list[int] = []
    box_observers.append(
        iren.AddObserver("LeftButtonPressEvent", _on_press, 5.0)
    )
    box_observers.append(
        iren.AddObserver("LeftButtonReleaseEvent", _on_release, 5.0)
    )
    viewer_session._box_observers = box_observers

    def _on_box(picked):
        if picked is None:
            viewer_session.statusMessage.emit("box: no hit")
            return
        mode = drag_state["mode"]
        hidden = set(viewer_session.hidden)
        if mode == "window":
            uuids = _uuids_fully_inside(picked, scene, hidden=hidden)
        else:
            uuids = _uuids_from_picked(picked, scene, hidden=hidden)
        if not uuids:
            viewer_session.statusMessage.emit(
                f"box [{mode}]: 0 entities."
            )
            return

        mods_int = int(viewer_session.state.last_click_modifiers)
        is_ctrl = bool(mods_int & int(QtCore.Qt.ControlModifier))
        is_shift = bool(mods_int & int(QtCore.Qt.ShiftModifier))
        if is_ctrl:
            existing = set(viewer_session.multi_selection)
            viewer_session.set_multi_selection(existing ^ uuids)
        elif is_shift or viewer_session.state.sticky_selection:
            viewer_session.add_multi_selection(uuids)
        else:
            viewer_session.set_multi_selection(uuids)
        viewer_session.statusMessage.emit(
            f"box [{mode}]: +{len(uuids)} entities -> "
            f"{len(viewer_session.multi_selection)} total"
        )

    enabled = False
    try:
        plotter.enable_rectangle_through_picking(
            callback=_on_box,
            show=False,
            show_message=False,
            start=True,
            color="#ffa033",
            style="wireframe",
            line_width=2.0,
        )
        enabled = True
    except Exception as exc:
        viewer_session.statusMessage.emit(
            f"box: enable_rectangle_through_picking failed: {exc}"
        )

    _attach_keypress(iren, viewer_session)

    viewer_session.statusMessage.emit(
        "Box select on. Drag left->right: window (fully inside). "
        "Drag right->left: crossing (touching)."
        if enabled else
        "Box select could not be enabled (check pyvista>=0.43)."
    )
    return None


def restore_navigation_style(plotter, viewer_session) -> None:
    """Clean up box-mode observers, disable the current picker and
    **force** the TrackballCamera style so that the left drag orbits
    the camera again.

    PyVista's ``disable_picking`` tries to restore the previous style,
    but after a ``mesh-picking -> rectangle-picking`` transition the
    stored style can be inconsistent (especially under pyvistaqt with
    its wrapped QtInteractor). ``enable_trackball_style`` brings us
    back to a known 3D-navigation state.
    """
    iren = plotter.iren.interactor
    for obs_id in getattr(viewer_session, "_box_observers", []) or []:
        try:
            iren.RemoveObserver(obs_id)
        except Exception:
            pass
    viewer_session._box_observers = []
    try:
        plotter.disable_picking()
    except Exception:
        pass
    try:
        plotter.enable_trackball_style()
    except Exception:
        pass


def _picked_entity_idx(picked) -> np.ndarray:
    """Concatenate ``cell_data['entity_idx']`` from every block of the
    rectangle picker's result. Returns an ``ndarray[int64]``."""
    parts: list[np.ndarray] = []

    def _drain(block) -> None:
        if block is None:
            return
        try:
            arr = block.cell_data.get("entity_idx")
        except Exception:
            arr = None
        if arr is None or len(arr) == 0:
            return
        try:
            parts.append(np.asarray(arr, dtype=np.int64))
        except Exception:
            return

    if hasattr(picked, "n_blocks"):
        for i in range(int(picked.n_blocks)):
            _drain(picked[i])
    else:
        _drain(picked)
    if not parts:
        return np.empty(0, dtype=np.int64)
    return np.concatenate(parts)


def _uuids_from_picked(picked, scene,
                       *, hidden: Optional[set[str]] = None) -> set[str]:
    """*Crossing* mode: an entity is included if it has **at least one**
    cell inside the frustum (it touches the rectangle).

    ``hidden`` (uuids hidden by isolate) is always excluded: invisible
    entities cannot be selected.
    """
    cell_uuid = getattr(scene, "_cell_uuid", None)
    if cell_uuid is None:
        return set()
    idx = _picked_entity_idx(picked)
    if idx.size == 0:
        return set()
    idx = idx[(idx >= 0) & (idx < len(cell_uuid))]
    if idx.size == 0:
        return set()
    hidden = hidden or set()
    out: set[str] = set()
    for u in cell_uuid[idx]:
        su = str(u)
        if su and su != "None" and su not in hidden:
            out.add(su)
    return out


def _uuids_fully_inside(picked, scene,
                        *, hidden: Optional[set[str]] = None) -> set[str]:
    """*Window* mode: an entity is included only if **all** of its cells
    fell inside the frustum.

    ``hidden`` is excluded before counts are compared.
    """
    cell_uuid = getattr(scene, "_cell_uuid", None)
    if cell_uuid is None:
        return set()
    idx = _picked_entity_idx(picked)
    if idx.size == 0:
        return set()
    idx = idx[(idx >= 0) & (idx < len(cell_uuid))]
    if idx.size == 0:
        return set()

    cu = np.asarray(cell_uuid)
    picked_uuids, picked_counts = np.unique(cu[idx], return_counts=True)
    total_uuids, total_counts = np.unique(cu, return_counts=True)
    total_by_uuid = dict(zip(total_uuids.tolist(), total_counts.tolist()))

    hidden = hidden or set()
    out: set[str] = set()
    for u, k in zip(picked_uuids.tolist(), picked_counts.tolist()):
        su = str(u)
        if not su or su == "None" or su in hidden:
            continue
        if int(k) >= int(total_by_uuid.get(u, k)):
            out.add(su)
    return out


# ── Pure logic (testable without Qt) ────────────────────────────────


def pick_entities_in_frustum(frustum, scene) -> Optional[set[str]]:
    """Return the uuids of entities whose cell centers fall inside the
    given frustum. ``None`` if the scene has no mesh.

    Testable function: does not depend on Qt/VTK events, only on the
    frustum and the arrays exposed by :class:`ViewerScene`.
    """
    if frustum is None:
        return None
    merged = getattr(scene, "_merged", None)
    cell_uuid = getattr(scene, "_cell_uuid", None)
    if merged is None or cell_uuid is None:
        return None
    try:
        centers = merged.cell_centers().points
    except Exception:
        return None
    inside_mask = np.zeros(len(centers), dtype=bool)
    for i in range(len(centers)):
        try:
            v = frustum.FunctionValue(
                float(centers[i, 0]),
                float(centers[i, 1]),
                float(centers[i, 2]),
            )
        except Exception:
            continue
        if v <= 0:
            inside_mask[i] = True
    if not inside_mask.any():
        return set()
    return {str(u) for u in cell_uuid[inside_mask]}


def resolve_pick(scene, cell_id: int):
    """Resolve a ``cell_id`` against the scene's merged mesh and return
    the corresponding ``PickedEntity`` or ``None``."""
    from ..bridge.picker import PickedEntity, picked_entity_from_polydata
    merged = getattr(scene, "_merged", None)
    if merged is None or cell_id < 0:
        return None
    pick = picked_entity_from_polydata(merged, cell_id)
    if pick is not None:
        return pick
    # Fallback using cell_uuid + cell_data["dim"/"tag"].
    cell_uuid = getattr(scene, "_cell_uuid", None)
    if cell_uuid is None or not (0 <= cell_id < len(cell_uuid)):
        return None
    try:
        dim = int(merged.cell_data["dim"][cell_id])
        tag = int(merged.cell_data["tag"][cell_id])
    except Exception:
        return None
    return PickedEntity(
        entity_uuid=str(cell_uuid[cell_id]), dim=dim, tag=tag,
    )


# ── internal helpers ────────────────────────────────────────────────


def _attach_keypress(iren, viewer_session) -> None:
    key = id(iren)
    for obs_id in _KEYPRESS_OBSERVERS.get(key, []):
        try:
            iren.RemoveObserver(obs_id)
        except Exception:
            pass
    _KEYPRESS_OBSERVERS[key] = []

    def _on_keypress(_obj, _evt):
        sym = (iren.GetKeySym() or "").lower()
        if sym in ("escape", "esc"):
            viewer_session.clear_multi_selection()
            viewer_session.set_selection(None)
            if getattr(viewer_session.state, "box_selection", False):
                viewer_session.toggle_box_selection()

    obs_id = iren.AddObserver("KeyPressEvent", _on_keypress)
    _KEYPRESS_OBSERVERS[key].append(obs_id)
