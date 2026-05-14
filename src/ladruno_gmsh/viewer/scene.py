"""PyVista actor management, overlays and refresh.

Strategy: **a single actor with a combined PolyData** that carries
per-cell ``cell_data["entity_uuid"]`` and a color array
``display_rgba``. This lets a model with thousands of entities render
in a single VTK call; selection coloring and visibility (alpha=0) are
vectorized numpy operations.
"""
from __future__ import annotations

from typing import Iterable, Optional

import numpy as np

from ..bridge.snapshot import SceneSnapshot
from .state import ViewerState


_KIND_COLOR = {
    "volume":  (127, 166, 255),
    "surface": (155, 209, 160),
    "curve":   (243, 178,  63),
    "point":   (226, 106, 106),
    "unknown": (160, 166, 176),
}
_COLOR_SELECTED = (255,  50,  50)
_COLOR_BOOL_OBJ = ( 75, 140, 255)
_COLOR_BOOL_TOOL = (255, 150,  50)


class ViewerScene:
    """Sync a :class:`SceneSnapshot` with a PyVista plotter."""

    def __init__(self, plotter, state: ViewerState) -> None:
        self.plotter = plotter
        self.state = state
        self._actor = None
        self._merged = None                            # pv.PolyData
        self._cell_uuid: np.ndarray | None = None      # object (N_cells,)
        self._base_rgb: np.ndarray | None = None       # (N_cells, 3) uint8
        self._mesh_actor = None
        self._mesh_nodes_actor = None
        self._opacity = 1.0
        self._first_render = True

    # ── lifecycle ───────────────────────────────────────────────────

    def render(self, snapshot: SceneSnapshot) -> None:
        # Camera snapshot before touching anything. After refreshes
        # (delete, mesh, etc.) we want the user to keep looking from
        # the same angle and zoom; only on the very first render do we
        # auto-frame.
        saved_camera = None
        if not self._first_render:
            try:
                saved_camera = self.plotter.camera_position
            except Exception:
                saved_camera = None

        self.clear()
        if not snapshot.geometry:
            self.plotter.set_background(self.state.background)
            return

        all_blocks: list[object] = []
        cell_uuids: list[str] = []
        rgbs: list[np.ndarray] = []

        for uuid, poly in snapshot.geometry.items():
            n = int(poly.n_cells)
            if n == 0:
                continue
            kind = _kind_from_dim(poly)
            color = np.array(_KIND_COLOR.get(kind, _KIND_COLOR["unknown"]),
                             dtype=np.uint8)
            cell_uuids.extend([uuid] * n)
            rgbs.append(np.tile(color, (n, 1)))
            all_blocks.append(poly)

        if not all_blocks:
            return

        merged = all_blocks[0].copy()
        for block in all_blocks[1:]:
            merged = merged.merge(block, merge_points=False)

        base_rgb = np.vstack(rgbs).astype(np.uint8)
        self._base_rgb = base_rgb
        self._cell_uuid = np.asarray(cell_uuids, dtype=object)
        self._merged = merged

        # ``entity_idx`` (int32) is a back-reference cell -> index in
        # ``self._cell_uuid``. VTK does not preserve string/object
        # arrays through the rectangle-picker extraction filters, but
        # int32 survives. The box-select callback uses this to map
        # selected cells back to entity uuids.
        merged.cell_data["entity_idx"] = np.arange(
            base_rgb.shape[0], dtype=np.int32,
        )

        # If a volumetric mesh exists, dim the CAD shell so the
        # internal tet edges show through. The user-controlled opacity
        # (state.entity_opacity, dock slider) is respected as a
        # multiplier — we do not overwrite it.
        has_3d_cells = (
            self.state.show_mesh
            and snapshot.mesh_grid is not None
            and _grid_has_dim(snapshot.mesh_grid, 3)
        )
        user_opacity = float(getattr(self.state, "entity_opacity", 1.0))
        auto_dim = 0.18 if has_3d_cells else 1.0
        self._opacity = max(0.0, min(1.0, user_opacity * auto_dim))

        rgba = np.empty((base_rgb.shape[0], 4), dtype=np.uint8)
        rgba[:, :3] = base_rgb
        rgba[:, 3] = int(self._opacity * 255)
        merged.cell_data["display_rgba"] = rgba

        try:
            self._actor = self.plotter.add_mesh(
                merged,
                scalars="display_rgba",
                rgb=True,
                show_edges=self.state.show_edges,
                edge_color="#1f2227",
                line_width=0.5,
                pickable=True,
                name="entities",
            )
        except Exception:
            self._actor = None

        if has_3d_cells and self._actor is not None:
            try:
                self._actor.GetProperty().SetOpacity(self._opacity)
            except Exception:
                pass

        if self.state.show_mesh and snapshot.mesh_grid is not None:
            grid = snapshot.mesh_grid
            # ``extract_all_edges`` returns EVERY edge — including the
            # internal ones of each tet/hex cell. A bare wireframe style
            # on the grid only renders surface edges, leaving the
            # interior visually hollow. For meshes above this cap the
            # cost (millions of segments) is not worth it; we fall back
            # to surface feature edges so the viewer stays responsive.
            #
            # ``pickable=False``: mesh wireframe/nodes must NOT intercept
            # the picker. If the CAD shell is translucent (3D auto-dim),
            # the picker prefers opaque objects in front and would
            # select an edge instead of the entity.
            _MAX_CELLS_FOR_INTERIOR_EDGES = 250_000
            try:
                if int(grid.n_cells) <= _MAX_CELLS_FOR_INTERIOR_EDGES:
                    edges = grid.extract_all_edges()
                else:
                    edges = grid.extract_surface().extract_feature_edges(
                        boundary_edges=True,
                        feature_edges=True,
                        non_manifold_edges=True,
                        manifold_edges=False,
                        feature_angle=30.0,
                    )
                self._mesh_actor = self.plotter.add_mesh(
                    edges,
                    color="#e0e0e0" if has_3d_cells else "#cccccc",
                    line_width=1.2 if has_3d_cells else 1.0,
                    pickable=False,
                    name="mesh_grid",
                )
            except Exception:
                self._mesh_actor = None

            if self.state.show_mesh_nodes:
                try:
                    import pyvista as pv
                    nodes_poly = pv.PolyData(np.asarray(grid.points,
                                                       dtype=np.float64))
                    self._mesh_nodes_actor = self.plotter.add_mesh(
                        nodes_poly,
                        color="#ffa033",
                        point_size=float(self.state.mesh_node_size),
                        render_points_as_spheres=True,
                        pickable=False,
                        name="mesh_nodes",
                    )
                except Exception:
                    self._mesh_nodes_actor = None

        if self.state.show_axes:
            try:
                self.plotter.show_axes()
            except Exception:
                pass

        self.plotter.set_background(self.state.background)
        # Only frame on the first render. On refreshes we preserve the
        # user's camera (zoom, pan, angle).
        if saved_camera is not None:
            try:
                self.plotter.camera_position = saved_camera
            except Exception:
                pass
        else:
            try:
                self.plotter.reset_camera()
            except Exception:
                pass
        self.set_orthographic(self.state.orthographic)
        self._first_render = False

    def reset_camera(self) -> None:
        """Force re-framing. Wire this to the toolbar's ``Reset view``."""
        try:
            self.plotter.reset_camera()
        except Exception:
            pass
        self._first_render = False

    def clear(self) -> None:
        for name in ("entities", "mesh_grid", "mesh_nodes"):
            try:
                self.plotter.remove_actor(name)
            except Exception:
                pass
        self._actor = None
        self._merged = None
        self._cell_uuid = None
        self._base_rgb = None
        self._mesh_actor = None
        self._mesh_nodes_actor = None

    # ── vectorized recolor + visibility ─────────────────────────────

    def recolor(self,
                *,
                multi_selection: Iterable[str] = (),
                boolean_object: Iterable[str] = (),
                boolean_tool: Iterable[str] = (),
                hidden: Iterable[str] = ()) -> None:
        if (self._merged is None or self._cell_uuid is None
                or self._base_rgb is None):
            return
        sel = set(str(u) for u in multi_selection)
        obj = set(str(u) for u in boolean_object)
        tool = set(str(u) for u in boolean_tool)
        hid = set(str(u) for u in hidden)
        uuids = self._cell_uuid

        rgba = np.empty((self._base_rgb.shape[0], 4), dtype=np.uint8)
        rgba[:, :3] = self._base_rgb
        rgba[:, 3] = int(self._opacity * 255)

        if obj:
            mask = np.isin(uuids, list(obj))
            rgba[mask, :3] = _COLOR_BOOL_OBJ
            rgba[mask, 3] = 255
        if tool:
            mask = np.isin(uuids, list(tool))
            rgba[mask, :3] = _COLOR_BOOL_TOOL
            rgba[mask, 3] = 255
        if sel:
            # Selection always opaque: red wins over the auto-dim of
            # the CAD shell when a 3D mesh is active.
            mask = np.isin(uuids, list(sel))
            rgba[mask, :3] = _COLOR_SELECTED
            rgba[mask, 3] = 255
        if hid:
            mask = np.isin(uuids, list(hid))
            rgba[mask, 3] = 0

        self._merged.cell_data["display_rgba"] = rgba
        try:
            self._merged.GetCellData().GetArray("display_rgba").Modified()
        except Exception:
            pass
        try:
            self.plotter.render()
        except Exception:
            pass

    # ── visual settings ─────────────────────────────────────────────

    def set_opacity(self, value: float) -> None:
        """Set CAD shell opacity. Persist the preference in
        ``state.entity_opacity`` so it survives refreshes."""
        value = float(max(0.0, min(1.0, value)))
        self.state.entity_opacity = value
        self._opacity = value
        if self._actor is None:
            return
        try:
            self._actor.GetProperty().SetOpacity(value)
            self.plotter.render()
        except Exception:
            pass

    def set_mesh_node_size(self, value: float) -> None:
        """Change the node-sphere size without rebuilding anything.

        Called on every slider tick; a full refresh_scene would freeze
        the UI by re-tessellating and rebuilding mesh actors. Here we
        only touch the VTK property of the actor.
        """
        value = float(max(0.5, value))
        self.state.mesh_node_size = value
        if self._mesh_nodes_actor is None:
            return
        try:
            self._mesh_nodes_actor.GetProperty().SetPointSize(value)
            self.plotter.render()
        except Exception:
            pass

    def set_orthographic(self, on: bool) -> None:
        try:
            self.plotter.parallel_projection = bool(on)
        except Exception:
            try:
                self.plotter.camera.SetParallelProjection(bool(on))
            except Exception:
                pass
        self.state.orthographic = bool(on)
        try:
            self.plotter.render()
        except Exception:
            pass


def _kind_from_dim(poly) -> str:
    try:
        dims = poly.cell_data.get("dim")
        if dims is None or len(dims) == 0:
            return "unknown"
        d = int(dims[0])
        return {0: "point", 1: "curve", 2: "surface", 3: "volume"}.get(d, "unknown")
    except Exception:
        return "unknown"


def _grid_has_dim(grid, dim: int) -> bool:
    """``True`` if the ``UnstructuredGrid`` has cells with
    ``cell_data["dim"] == dim``."""
    try:
        dims = grid.cell_data.get("dim")
        if dims is None:
            return False
        return bool((np.asarray(dims) == int(dim)).any())
    except Exception:
        return False
