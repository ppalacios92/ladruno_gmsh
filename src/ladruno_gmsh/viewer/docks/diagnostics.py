"""Navigable table of FEM findings with scene highlighting."""
from __future__ import annotations

from ..deps import require_dependencies


class DiagnosticsDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Diagnostics", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        grid = QtWidgets.QGridLayout()
        self.btn_orphans = QtWidgets.QPushButton("Orphans")
        self.btn_dups = QtWidgets.QPushButton("Duplicates")
        self.btn_manifold = QtWidgets.QPushButton("Manifoldness")
        self.btn_intf = QtWidgets.QPushButton("Interference (bbox)")
        self.btn_intf_meas = QtWidgets.QPushButton("Interference (measure)")
        self.btn_normals = QtWidgets.QPushButton("Normals")
        self.btn_report = QtWidgets.QPushButton("Full report")
        grid.addWidget(self.btn_orphans, 0, 0)
        grid.addWidget(self.btn_dups, 0, 1)
        grid.addWidget(self.btn_manifold, 1, 0)
        grid.addWidget(self.btn_intf, 1, 1)
        grid.addWidget(self.btn_intf_meas, 2, 0)
        grid.addWidget(self.btn_normals, 2, 1)
        grid.addWidget(self.btn_report, 3, 0, 1, 2)
        layout.addLayout(grid)

        self.view = QtWidgets.QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setStyleSheet("font-family: Consolas, monospace;")
        layout.addWidget(self.view)

        self.dock.setWidget(widget)

        self.btn_orphans.clicked.connect(self._run_orphans)
        self.btn_dups.clicked.connect(self._run_dups)
        self.btn_manifold.clicked.connect(self._run_manifold)
        self.btn_intf.clicked.connect(lambda: self._run_intf(False))
        self.btn_intf_meas.clicked.connect(lambda: self._run_intf(True))
        self.btn_normals.clicked.connect(self._run_normals)
        self.btn_report.clicked.connect(self._run_report)

    def _run_orphans(self) -> None:
        r = self._safe(self.viewer.api.diagnostics.orphans)
        if r is None:
            return
        self.view.setPlainText(
            f"Orphan entities: {len(r.orphan_entities)}\n"
            f"Nodes without elements: {r.isolated_node_count} "
            f"/ {r.total_node_count}\n"
            f"OK: {r.ok}"
        )

    def _run_dups(self) -> None:
        diag = self.viewer.api.tolerance.linear
        r = self._safe(lambda: self.viewer.api.diagnostics.duplicates(
            tolerance=diag
        ))
        if r is None:
            return
        self.view.setPlainText(
            f"Duplicates (gmsh): {len(r.duplicate_node_tags_gmsh)}\n"
            f"Coincident pairs (KDTree, tol={r.tolerance:g}): "
            f"{len(r.coincident_pairs)}\n"
            f"OK: {r.ok}"
        )

    def _run_manifold(self) -> None:
        r = self._safe(self.viewer.api.diagnostics.manifoldness)
        if r is None:
            return
        self.view.setPlainText(
            f"Free edges: {r.free_edges_count}\n"
            f"Non-manifold edges: {r.non_manifold_edges_count}\n"
            f"OK: {r.ok}"
        )

    def _run_intf(self, measure: bool) -> None:
        r = self._safe(lambda: self.viewer.api.diagnostics.interference(
            measure=measure
        ))
        if r is None:
            return
        lines = [f"Overlapping pairs: {len(r.items)}",
                 f"Measured: {r.measured}", ""]
        for it in r.items[:50]:
            vol = "-" if it.overlap_volume is None else f"{it.overlap_volume:.4g}"
            lines.append(f"  vol {it.a} <-> vol {it.b}   overlap={vol}")
        if len(r.items) > 50:
            lines.append(f"  ... and {len(r.items) - 50} more")
        self.view.setPlainText("\n".join(lines))

    def _run_normals(self) -> None:
        r = self._safe(self.viewer.api.diagnostics.normals)
        if r is None:
            return
        msg = (f"Surfaces with inverted orientation: "
               f"{len(r.inverted_surfaces)}\n"
               f"Faces inspected: {r.inspected}\n"
               f"OK: {r.ok}")
        if r.note:
            msg += f"\nNote: {r.note}"
        self.view.setPlainText(msg)

    def _run_report(self) -> None:
        r = self._safe(self.viewer.api.diagnostics.report)
        if r is None:
            return
        self.view.setPlainText(r.as_markdown())

    def _safe(self, fn):
        try:
            return fn()
        except Exception as exc:
            self.viewer.statusMessage.emit(f"diagnostics failed: {exc}")
            return None
