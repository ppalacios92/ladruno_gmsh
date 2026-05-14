"""Interactive physical group assignment."""
from __future__ import annotations

from ..deps import require_dependencies


class PhysicalGroupsDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Physical groups", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.list = QtWidgets.QListWidget()
        self.list.setMaximumHeight(160)
        layout.addWidget(QtWidgets.QLabel("Existing groups:"))
        layout.addWidget(self.list)
        self.btn_refresh = QtWidgets.QPushButton("Refresh")
        layout.addWidget(self.btn_refresh)

        form = QtWidgets.QFormLayout()
        self.input_name = QtWidgets.QLineEdit()
        form.addRow("name:", self.input_name)
        self.spin_dim = QtWidgets.QSpinBox()
        self.spin_dim.setRange(0, 3)
        self.spin_dim.setValue(3)
        form.addRow("dim:", self.spin_dim)
        layout.addLayout(form)

        self._uuids: list[str] = []
        self.sel_list = QtWidgets.QListWidget()
        self.sel_list.setMaximumHeight(120)
        layout.addWidget(QtWidgets.QLabel("Entities:"))
        layout.addWidget(self.sel_list)
        row = QtWidgets.QHBoxLayout()
        self.btn_add_sel = QtWidgets.QPushButton("Add selection")
        self.btn_clear_sel = QtWidgets.QPushButton("Clear")
        row.addWidget(self.btn_add_sel)
        row.addWidget(self.btn_clear_sel)
        layout.addLayout(row)

        self.btn_create = QtWidgets.QPushButton("Create group")
        layout.addWidget(self.btn_create)

        layout.addStretch(1)
        self.dock.setWidget(widget)

        self.btn_refresh.clicked.connect(self._refresh)
        self.btn_add_sel.clicked.connect(self._add_selection)
        self.btn_clear_sel.clicked.connect(self._clear_selection)
        self.btn_create.clicked.connect(self._create)
        viewer_session.documentChanged.connect(self._refresh)
        self._refresh()

    def _refresh(self) -> None:
        self.list.clear()
        try:
            groups = self.viewer.api.physical_groups.list()
        except Exception as exc:
            self.viewer.statusMessage.emit(f"physical groups: {exc}")
            return
        for g in groups:
            self.list.addItem(
                f"[{g.dim}] {g.tag}  {g.name or '(no name)'}  "
                f"({len(g.entity_tags)} ents)"
            )

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
            self.sel_list.addItem(f"({e.dim},{e.tag}) {e.name or e.kind}")
            added += 1
        self.viewer.statusMessage.emit(
            f"+{added} entities ({len(self._uuids)} total)."
        )

    def _clear_selection(self) -> None:
        self._uuids.clear()
        self.sel_list.clear()

    def _create(self) -> None:
        name = self.input_name.text().strip()
        if not name:
            self.viewer.statusMessage.emit("Enter a name for the group.")
            return
        if not self._uuids:
            self.viewer.statusMessage.emit("Add entities to the selection.")
            return
        try:
            self.viewer.api.physical_groups.add(
                name=name,
                entities=tuple(self._uuids),
                dim=self.spin_dim.value(),
            )
        except Exception as exc:
            self.viewer.statusMessage.emit(f"create group failed: {exc}")
            return
        self._clear_selection()
        self.input_name.clear()
        self._refresh()
        self.viewer.statusMessage.emit(f"group '{name}' created.")
