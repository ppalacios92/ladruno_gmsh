"""Export of results and projects."""
from __future__ import annotations

from ..deps import require_dependencies


_FORMATS = [
    ("STEP", "*.step"),
    ("IGES", "*.iges"),
    ("BREP", "*.brep"),
    ("STL",  "*.stl"),
    ("MSH",  "*.msh"),
    ("VTU",  "*.vtu"),
]


class ExportDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Export", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.combo_fmt = QtWidgets.QComboBox()
        for name, _ in _FORMATS:
            self.combo_fmt.addItem(name)
        layout.addWidget(QtWidgets.QLabel("Format:"))
        layout.addWidget(self.combo_fmt)

        self.btn_export = QtWidgets.QPushButton("Export...")
        layout.addWidget(self.btn_export)

        sep = QtWidgets.QLabel("Project (.lgmsh)")
        sep.setProperty("role", "title")
        layout.addWidget(sep)

        self.btn_save = QtWidgets.QPushButton("Save project...")
        self.btn_load = QtWidgets.QPushButton("Load project (info)...")
        layout.addWidget(self.btn_save)
        layout.addWidget(self.btn_load)

        layout.addStretch(1)
        self.dock.setWidget(widget)

        self.btn_export.clicked.connect(self._export)
        self.btn_save.clicked.connect(self._save_project)
        self.btn_load.clicked.connect(self._load_project_info)

    def _export(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        idx = self.combo_fmt.currentIndex()
        _, pattern = _FORMATS[idx]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.dock,
            f"Export as {self.combo_fmt.currentText()}",
            "",
            f"{self.combo_fmt.currentText()} ({pattern})",
        )
        if not path:
            return
        try:
            self.viewer.api.export(path)
        except Exception as exc:
            self.viewer.statusMessage.emit(f"export failed: {exc}")
            return
        self.viewer.statusMessage.emit(f"Exported: {path}")

    def _save_project(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.dock, "Save project", "", "ladruno project (*.lgmsh)",
        )
        if not path:
            return
        from ...io.project import save as _save
        try:
            _save(self.viewer.api, path)
        except Exception as exc:
            self.viewer.statusMessage.emit(f"save project failed: {exc}")
            return
        self.viewer.statusMessage.emit(f"Project saved: {path}")

    def _load_project_info(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self.dock, "Open project", "", "ladruno project (*.lgmsh)",
        )
        if not path:
            return
        QtWidgets.QMessageBox.information(
            self.dock, "Load project",
            "To replay the project in a clean session, run:\n"
            "  from ladruno_gmsh.io.project import load\n"
            f"  session = load(r'{path}')\n"
            "Hot-swapping the active session is not supported in this version.",
        )
