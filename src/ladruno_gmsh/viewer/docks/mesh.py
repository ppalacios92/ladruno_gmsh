"""Mesh algorithms, sizes, order and size fields."""
from __future__ import annotations

from ..deps import require_dependencies


_ALGO_2D = [
    "Automatic", "Delaunay", "Frontal-Delaunay",
    "Frontal-Delaunay-Quads", "Packing", "Quasi-Structured-Quad",
]
_ALGO_3D = ["Delaunay", "Frontal", "HXT", "MMG3D"]
_OPT_METHODS = ["", "Netgen", "HighOrder", "Laplace2D",
                "Relocate2D", "Relocate3D"]


class MeshDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Mesh", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.spin_size = QtWidgets.QDoubleSpinBox()
        self.spin_size.setDecimals(6)
        self.spin_size.setRange(0.0, 1.0e6)
        self.spin_size.setValue(0.0)
        layout.addRow("size (0=auto):", self.spin_size)

        self.combo_2d = QtWidgets.QComboBox()
        self.combo_2d.addItems(_ALGO_2D)
        self.combo_2d.setCurrentText("Frontal-Delaunay")
        layout.addRow("2D algorithm:", self.combo_2d)

        self.combo_3d = QtWidgets.QComboBox()
        self.combo_3d.addItems(_ALGO_3D)
        self.combo_3d.setCurrentText("HXT")
        layout.addRow("3D algorithm:", self.combo_3d)

        self.spin_order = QtWidgets.QSpinBox()
        self.spin_order.setRange(1, 4)
        self.spin_order.setValue(1)
        layout.addRow("order:", self.spin_order)

        dim_row = QtWidgets.QHBoxLayout()
        self.btn_mesh_1d = QtWidgets.QPushButton("1D")
        self.btn_mesh_2d = QtWidgets.QPushButton("2D")
        self.btn_mesh_3d = QtWidgets.QPushButton("3D")
        self.btn_mesh_all = QtWidgets.QPushButton("All (0→3)")
        for b in (self.btn_mesh_1d, self.btn_mesh_2d,
                  self.btn_mesh_3d, self.btn_mesh_all):
            dim_row.addWidget(b)
        layout.addRow("mesh dim:", _wrap_h(dim_row, QtWidgets))

        self.btn_refine = QtWidgets.QPushButton("Refine")
        layout.addRow("", self.btn_refine)
        self.btn_recombine = QtWidgets.QPushButton("Recombine")
        layout.addRow("", self.btn_recombine)
        self.btn_clear = QtWidgets.QPushButton("Clear mesh")
        layout.addRow("", self.btn_clear)

        sep = QtWidgets.QLabel("Optimization")
        sep.setProperty("role", "title")
        layout.addRow(sep)

        self.combo_opt = QtWidgets.QComboBox()
        self.combo_opt.addItems(_OPT_METHODS)
        layout.addRow("method:", self.combo_opt)

        self.spin_niter = QtWidgets.QSpinBox()
        self.spin_niter.setRange(1, 50)
        self.spin_niter.setValue(3)
        layout.addRow("iters:", self.spin_niter)

        self.btn_optimize = QtWidgets.QPushButton("Optimize")
        layout.addRow("", self.btn_optimize)

        sep2 = QtWidgets.QLabel("Display")
        sep2.setProperty("role", "title")
        layout.addRow(sep2)

        self.chk_show_mesh = QtWidgets.QCheckBox("Show mesh in scene")
        layout.addRow("", self.chk_show_mesh)

        self.chk_show_nodes = QtWidgets.QCheckBox("Show nodes")
        self.chk_show_nodes.setChecked(
            bool(getattr(viewer_session.state, "show_mesh_nodes", True))
        )
        layout.addRow("", self.chk_show_nodes)

        self.slider_node_size = QtWidgets.QSlider()
        self.slider_node_size.setOrientation(deps["QtCore"].Qt.Horizontal)
        self.slider_node_size.setRange(1, 30)
        self.slider_node_size.setValue(
            int(getattr(viewer_session.state, "mesh_node_size", 5.0))
        )
        layout.addRow("node size:", self.slider_node_size)

        self.slider_opacity = QtWidgets.QSlider()
        self.slider_opacity.setOrientation(deps["QtCore"].Qt.Horizontal)
        self.slider_opacity.setRange(10, 100)
        self.slider_opacity.setValue(
            int(round(float(getattr(viewer_session.state,
                                    "entity_opacity", 1.0)) * 100))
        )
        layout.addRow("opacity:", self.slider_opacity)

        sep3 = QtWidgets.QLabel("Orientation")
        sep3.setProperty("role", "title")
        layout.addRow(sep3)
        self.btn_outward = QtWidgets.QPushButton("Set all outward")
        layout.addRow("", self.btn_outward)

        self.dock.setWidget(widget)

        self.btn_mesh_1d.clicked.connect(lambda: self._mesh_dim(1))
        self.btn_mesh_2d.clicked.connect(lambda: self._mesh_dim(2))
        self.btn_mesh_3d.clicked.connect(lambda: self._mesh_dim(3))
        self.btn_mesh_all.clicked.connect(lambda: self._mesh_dim(3))
        self.btn_refine.clicked.connect(
            lambda: self.viewer.run_method("refine_mesh")
        )
        self.btn_recombine.clicked.connect(
            lambda: self.viewer.run_method("recombine_mesh")
        )
        self.btn_clear.clicked.connect(
            lambda: self.viewer.run_method("clear_mesh")
        )
        self.btn_optimize.clicked.connect(self._optimize)
        self.chk_show_mesh.toggled.connect(self._toggle_show_mesh)
        self.chk_show_nodes.toggled.connect(self._toggle_show_nodes)
        self.slider_node_size.valueChanged.connect(self._on_node_size)
        self.slider_opacity.valueChanged.connect(self._on_opacity)
        self.btn_outward.clicked.connect(self._on_outward)

    def _mesh_dim(self, dim: int) -> None:
        size = self.spin_size.value() or None
        self.viewer.run_method(
            "mesh",
            dim=dim,
            size=size,
            order=self.spin_order.value(),
            algorithm_2d=self.combo_2d.currentText(),
            algorithm_3d=self.combo_3d.currentText(),
        )

    def _optimize(self) -> None:
        self.viewer.run_method(
            "optimize_mesh",
            method=self.combo_opt.currentText(),
            niter=self.spin_niter.value(),
        )

    def _toggle_show_mesh(self, on: bool) -> None:
        self.viewer.state.show_mesh = on
        self.viewer.refresh_scene(with_mesh=on)

    def _toggle_show_nodes(self, on: bool) -> None:
        self.viewer.state.show_mesh_nodes = on
        # Toggling on/off requires recreating the actor (it does not
        # exist if it was off), so a refresh is needed here.
        self.viewer.refresh_scene(with_mesh=self.viewer.state.show_mesh)

    def _on_node_size(self, value: int) -> None:
        # Direct actor update via signal: changing the VTK SetPointSize
        # is cheap and does NOT require rebuilding the scene. Doing
        # refresh_scene on every slider tick froze the UI while the
        # tessellator and mesh actors were rebuilt.
        self.viewer.state.mesh_node_size = float(value)
        self.viewer.nodeSizeChanged.emit(float(value))

    def _on_opacity(self, value: int) -> None:
        self.viewer.opacityChanged.emit(value / 100.0)

    def _on_outward(self) -> None:
        self.viewer.busyChanged.emit(True)
        try:
            self.viewer.api.reorient.set_all_outward()
        except Exception as exc:
            self.viewer.statusMessage.emit(f"set_all_outward failed: {exc}")
            self.viewer.busyChanged.emit(False)
            return
        self.viewer.busyChanged.emit(False)
        self.viewer.documentChanged.emit()
        self.viewer.refresh_scene()
        self.viewer.statusMessage.emit("Normals: all pointing outward.")


def _wrap_h(layout, QtWidgets):
    w = QtWidgets.QWidget()
    w.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    return w
