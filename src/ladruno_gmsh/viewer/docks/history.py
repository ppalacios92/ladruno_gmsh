"""Operation timeline with parameter editing."""
from __future__ import annotations

from ..deps import require_dependencies


class HistoryDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("History", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self.list = QtWidgets.QListWidget()
        self.list.setAlternatingRowColors(True)
        layout.addWidget(self.list)

        self.detail = QtWidgets.QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(120)
        layout.addWidget(self.detail)

        self.dock.setWidget(widget)

        self.list.currentRowChanged.connect(self._on_row_changed)
        viewer_session.documentChanged.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for i, node in enumerate(self.viewer.api.history.nodes):
            self.list.addItem(f"{i:02d}  {node.op_type}")

    def _on_row_changed(self, row: int) -> None:
        nodes = self.viewer.api.history.nodes
        if row < 0 or row >= len(nodes):
            self.detail.setPlainText("")
            return
        n = nodes[row]
        lines = [
            f"op_id     : {n.op_id}",
            f"op_type   : {n.op_type}",
            f"inputs    : {list(n.inputs)}",
            f"outputs   : {len(n.output_uuids)} entities",
            "parameters:",
        ]
        for k, v in n.parameters.items():
            lines.append(f"  {k} = {v}")
        self.detail.setPlainText("\n".join(lines))
