"""Console showing gmsh.logger output and typed errors."""
from __future__ import annotations

from ..deps import require_dependencies


class ConsoleDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Console", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self.view = QtWidgets.QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setMaximumBlockCount(5000)
        self.view.setStyleSheet("font-family: Consolas, monospace; font-size: 10px;")
        layout.addWidget(self.view)

        row = QtWidgets.QHBoxLayout()
        self.btn_clear = QtWidgets.QPushButton("Clear")
        self.btn_save = QtWidgets.QPushButton("Save as...")
        row.addStretch(1)
        row.addWidget(self.btn_save)
        row.addWidget(self.btn_clear)
        layout.addLayout(row)

        self.dock.setWidget(widget)

        viewer_session.logAppended.connect(self.append)
        self.btn_clear.clicked.connect(self.view.clear)
        self.btn_save.clicked.connect(self._save)

    def append(self, text: str) -> None:
        if text:
            self.view.appendPlainText(text)

    def _save(self) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self.dock, "Save console", "ladruno_gmsh.log",
            "Text (*.log *.txt)",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(self.view.toPlainText())
        except Exception as exc:
            self.viewer.statusMessage.emit(f"Save log failed: {exc}")
