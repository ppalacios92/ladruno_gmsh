"""Normal reorientation and element reversal."""
from __future__ import annotations

from ..deps import require_dependencies


class ReorientDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Reorientation", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self._uuids: list[str] = []
        self.list = QtWidgets.QListWidget()
        self.list.setMaximumHeight(140)
        layout.addWidget(QtWidgets.QLabel("Entities:"))
        layout.addWidget(self.list)

        row = QtWidgets.QHBoxLayout()
        self.btn_add = QtWidgets.QPushButton("Add selection")
        self.btn_clear = QtWidgets.QPushButton("Clear")
        row.addWidget(self.btn_add)
        row.addWidget(self.btn_clear)
        layout.addLayout(row)

        self.btn_reverse = QtWidgets.QPushButton("Reverse")
        self.btn_outward = QtWidgets.QPushButton("Set outward (selected volume)")
        self.btn_reclass = QtWidgets.QPushButton("Reclassify nodes")
        self.btn_relocate = QtWidgets.QPushButton("Relocate nodes")
        for b in (self.btn_reverse, self.btn_outward,
                  self.btn_reclass, self.btn_relocate):
            layout.addWidget(b)

        layout.addStretch(1)
        self.dock.setWidget(widget)

        self.btn_add.clicked.connect(self._add_selection)
        self.btn_clear.clicked.connect(self._clear)
        self.btn_reverse.clicked.connect(self._reverse)
        self.btn_outward.clicked.connect(self._set_outward)
        self.btn_reclass.clicked.connect(lambda: self._call("reclassify_nodes"))
        self.btn_relocate.clicked.connect(lambda: self._call("relocate_nodes"))

    def _call(self, name: str) -> None:
        self.viewer.busyChanged.emit(True)
        try:
            getattr(self.viewer.api.reorient, name)()
        except Exception as exc:
            self.viewer.statusMessage.emit(f"{name} failed: {exc}")
            self.viewer.busyChanged.emit(False)
            return
        self.viewer.busyChanged.emit(False)
        self.viewer.documentChanged.emit()
        self.viewer.refresh_scene()

    def _add_selection(self) -> None:
        ents = self.viewer.get_selected_entities()
        if not ents:
            self.viewer.statusMessage.emit(
                "Select entities in the Model tree first."
            )
            return
        added = 0
        for e in ents:
            if e.uuid in self._uuids:
                continue
            self._uuids.append(e.uuid)
            self.list.addItem(f"({e.dim},{e.tag}) {e.name or e.kind}")
            added += 1
        self.viewer.statusMessage.emit(
            f"+{added} entities ({len(self._uuids)} total)."
        )

    def _clear(self) -> None:
        self._uuids.clear()
        self.list.clear()

    def _reverse(self) -> None:
        if not self._uuids:
            return
        self.viewer.busyChanged.emit(True)
        try:
            self.viewer.api.reorient.reverse(tuple(self._uuids))
        except Exception as exc:
            self.viewer.statusMessage.emit(f"reverse failed: {exc}")
            self.viewer.busyChanged.emit(False)
            return
        self.viewer.busyChanged.emit(False)
        self.viewer.documentChanged.emit()
        self.viewer.refresh_scene()

    def _set_outward(self) -> None:
        picked = self.viewer.selection
        if picked is None or picked.dim != 3:
            self.viewer.statusMessage.emit(
                "Select a volume to use set_outward."
            )
            return
        self.viewer.busyChanged.emit(True)
        try:
            self.viewer.api.reorient.set_outward(picked.entity_uuid)
        except Exception as exc:
            self.viewer.statusMessage.emit(f"set_outward failed: {exc}")
            self.viewer.busyChanged.emit(False)
            return
        self.viewer.busyChanged.emit(False)
        self.viewer.documentChanged.emit()
        self.viewer.refresh_scene()
