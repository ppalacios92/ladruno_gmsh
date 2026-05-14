"""Compositor for boolean operations: object / tool / tolerance."""
from __future__ import annotations

from ..deps import require_dependencies


class BooleanDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Booleans", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self._object_uuids: list[str] = []
        self._tool_uuids: list[str] = []

        hint = QtWidgets.QLabel(
            "1) Select entities in the Model tree "
            "(Ctrl/Shift = multiple).\n"
            "2) Press Add selection on Object or Tool.\n"
            "3) Run the operation."
        )
        hint.setProperty("role", "hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addWidget(self._titled("Object"))
        self.object_list = QtWidgets.QListWidget()
        self.object_list.setMaximumHeight(110)
        layout.addWidget(self.object_list)
        btns_o = QtWidgets.QHBoxLayout()
        self.btn_add_obj = QtWidgets.QPushButton("Add selection")
        self.btn_clear_obj = QtWidgets.QPushButton("Clear")
        btns_o.addWidget(self.btn_add_obj)
        btns_o.addWidget(self.btn_clear_obj)
        layout.addLayout(btns_o)

        layout.addWidget(self._titled("Tool"))
        self.tool_list = QtWidgets.QListWidget()
        self.tool_list.setMaximumHeight(110)
        layout.addWidget(self.tool_list)
        btns_t = QtWidgets.QHBoxLayout()
        self.btn_add_tool = QtWidgets.QPushButton("Add selection")
        self.btn_clear_tool = QtWidgets.QPushButton("Clear")
        btns_t.addWidget(self.btn_add_tool)
        btns_t.addWidget(self.btn_clear_tool)
        layout.addLayout(btns_t)

        self.chk_remove_obj = QtWidgets.QCheckBox("remove object")
        self.chk_remove_obj.setChecked(True)
        self.chk_remove_tool = QtWidgets.QCheckBox("remove tool")
        self.chk_remove_tool.setChecked(True)
        layout.addWidget(self.chk_remove_obj)
        layout.addWidget(self.chk_remove_tool)

        actions = QtWidgets.QGridLayout()
        self.btn_cut = QtWidgets.QPushButton("Cut")
        self.btn_fuse = QtWidgets.QPushButton("Fuse")
        self.btn_intersect = QtWidgets.QPushButton("Intersect")
        self.btn_fragment = QtWidgets.QPushButton("Fragment")
        self.btn_fragment_all = QtWidgets.QPushButton("Fragment all (3D)")
        actions.addWidget(self.btn_cut, 0, 0)
        actions.addWidget(self.btn_fuse, 0, 1)
        actions.addWidget(self.btn_intersect, 1, 0)
        actions.addWidget(self.btn_fragment, 1, 1)
        actions.addWidget(self.btn_fragment_all, 2, 0, 1, 2)
        layout.addLayout(actions)

        layout.addStretch(1)
        self.dock.setWidget(widget)

        self.btn_add_obj.clicked.connect(
            lambda: self._add_selection(self._object_uuids, self.object_list)
        )
        self.btn_clear_obj.clicked.connect(
            lambda: self._clear(self._object_uuids, self.object_list)
        )
        self.btn_add_tool.clicked.connect(
            lambda: self._add_selection(self._tool_uuids, self.tool_list)
        )
        self.btn_clear_tool.clicked.connect(
            lambda: self._clear(self._tool_uuids, self.tool_list)
        )

        self.btn_cut.clicked.connect(lambda: self._run("cut"))
        self.btn_fuse.clicked.connect(lambda: self._run("fuse"))
        self.btn_intersect.clicked.connect(lambda: self._run("intersect"))
        self.btn_fragment.clicked.connect(lambda: self._run("fragment"))
        self.btn_fragment_all.clicked.connect(
            lambda: self.viewer.run_method("fragment_all", dim=3)
        )

        viewer_session.documentChanged.connect(self._purge_invalid)

    def _titled(self, text: str):
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        lab = QtWidgets.QLabel(text)
        lab.setProperty("role", "title")
        return lab

    def _add_selection(self, store: list, list_widget) -> None:
        ents = self.viewer.get_selected_entities()
        if not ents:
            self.viewer.statusMessage.emit(
                "Select entities in the Model tree or in the scene."
            )
            return
        added = 0
        for e in ents:
            if e.uuid in store:
                continue
            store.append(e.uuid)
            list_widget.addItem(f"({e.dim},{e.tag}) {e.name or e.kind}")
            added += 1
        self._publish_slots()
        self.viewer.clear_multi_selection()
        self.viewer.statusMessage.emit(
            f"+{added} entities ({len(store)} total)."
        )

    def _clear(self, store: list, list_widget) -> None:
        store.clear()
        list_widget.clear()
        self._publish_slots()

    def _publish_slots(self) -> None:
        """Reflect current uuids in the viewer so that the blue/orange
        tint is applied."""
        self.viewer.set_boolean_object(self._object_uuids)
        self.viewer.set_boolean_tool(self._tool_uuids)

    def _run(self, kind: str) -> None:
        if not self._object_uuids:
            self.viewer.statusMessage.emit(
                "Define at least one Object before running."
            )
            return
        kwargs = dict(
            object=tuple(self._object_uuids),
            tool=tuple(self._tool_uuids),
            remove_object=self.chk_remove_obj.isChecked(),
            remove_tool=self.chk_remove_tool.isChecked(),
        )
        self.viewer.run_method(kind, **kwargs)
        self._object_uuids.clear()
        self._tool_uuids.clear()
        self.object_list.clear()
        self.tool_list.clear()
        # run_method already emits documentChanged which clears the
        # viewer's boolean slots; here we just keep the dock visuals
        # consistent.

    def _purge_invalid(self) -> None:
        doc = self.viewer.api.document
        changed = False
        for store, widget in ((self._object_uuids, self.object_list),
                              (self._tool_uuids, self.tool_list)):
            valid = [u for u in store if doc.find_by_uuid(u) is not None]
            if valid != store:
                store[:] = valid
                widget.clear()
                for u in valid:
                    e = doc.find_by_uuid(u)
                    widget.addItem(f"({e.dim},{e.tag}) {e.name or e.kind}")
                changed = True
        if changed:
            self._publish_slots()
