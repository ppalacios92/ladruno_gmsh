"""Entity tree: volumes, surfaces, curves, points."""
from __future__ import annotations

from ..deps import require_dependencies


_FRAGMENT_ORIGINS = frozenset({"fragment", "fragment_all"})


def _is_fragment_origin(origin: str) -> bool:
    return origin in _FRAGMENT_ORIGINS


def _sort_fragment_last(entities):
    """Return entities with fragment products at the end.

    Preserves the stable relative order within each group.
    """
    regulars = [e for e in entities if not _is_fragment_origin(e.origin)]
    frags = [e for e in entities if _is_fragment_origin(e.origin)]
    return regulars + frags


class ModelTreeDock:
    """Dock with a QTreeWidget that lists entities grouped by dimension."""

    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtCore = deps["QtCore"]
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Model", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setHeaderLabels(
            ["Entity", "Dim", "Tag", "Origin", "Name"]
        )
        self.tree.setColumnWidth(0, 130)
        self.tree.setColumnWidth(1, 45)
        self.tree.setColumnWidth(2, 60)
        self.tree.setColumnWidth(3, 90)
        self.tree.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tree)

        # Quick filters.
        filter_box = QtWidgets.QGridLayout()
        self.btn_all_vols = QtWidgets.QPushButton("All volumes")
        self.btn_all_surfs = QtWidgets.QPushButton("All surfaces")
        self.btn_invert = QtWidgets.QPushButton("Invert")
        self.btn_clear = QtWidgets.QPushButton("Clear")
        filter_box.addWidget(self.btn_all_vols, 0, 0)
        filter_box.addWidget(self.btn_all_surfs, 0, 1)
        filter_box.addWidget(self.btn_invert, 1, 0)
        filter_box.addWidget(self.btn_clear, 1, 1)
        layout.addLayout(filter_box)

        self.input_regex = QtWidgets.QLineEdit()
        self.input_regex.setPlaceholderText(
            "Filter by name (regex). Press Enter to apply."
        )
        layout.addWidget(self.input_regex)

        self.btn_all_vols.clicked.connect(
            lambda: self._select_kind("volume")
        )
        self.btn_all_surfs.clicked.connect(
            lambda: self._select_kind("surface")
        )
        self.btn_invert.clicked.connect(self._invert_selection)
        self.btn_clear.clicked.connect(self.viewer.clear_multi_selection)
        self.input_regex.returnPressed.connect(self._select_by_regex)

        hint = QtWidgets.QLabel(
            "Click selects; Ctrl/Shift add. Then use Add selection in "
            "Booleans / Reorientation / Physical groups."
        )
        hint.setWordWrap(True)
        hint.setProperty("role", "hint")
        layout.addWidget(hint)

        self.summary = QtWidgets.QLabel("")
        self.summary.setProperty("role", "hint")
        layout.addWidget(self.summary)

        self.dock.setWidget(widget)

        viewer_session.documentChanged.connect(self.refresh)
        viewer_session.selectionChanged.connect(self._on_external_selection)
        viewer_session.multiSelectionChanged.connect(self._on_external_multi)
        self.refresh()

    def selected_entities(self) -> list:
        items = self.tree.selectedItems()
        out = []
        doc = self.viewer.api.document
        for it in items:
            uuid = it.data(0, 32)  # custom role
            if uuid is None:
                continue
            e = doc.find_by_uuid(str(uuid))
            if e is not None:
                out.append(e)
        return out

    def refresh(self) -> None:
        doc = self.viewer.api.document
        self.tree.clear()
        groups = {
            3: ("Volumes", doc.volumes),
            2: ("Surfaces", doc.surfaces),
            1: ("Curves", doc.curves),
            0: ("Points", doc.points),
        }
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        QtGui = deps["QtGui"]
        # Soft color to highlight fragment products.
        try:
            frag_brush = QtGui.QBrush(QtGui.QColor("#ffa033"))
        except Exception:
            frag_brush = None
        n_frag = 0
        for dim in (3, 2, 1, 0):
            label, items = groups[dim]
            if not items:
                continue
            # Fragment products at the end, preserving tag order
            # within each group.
            ordered = _sort_fragment_last(items)
            parent = QtWidgets.QTreeWidgetItem([
                f"{label} ({len(items)})", str(dim), "", "", "",
            ])
            for e in ordered:
                child = QtWidgets.QTreeWidgetItem([
                    e.kind, str(e.dim), str(e.tag),
                    e.origin or "", e.name or "",
                ])
                child.setData(0, 32, e.uuid)
                if _is_fragment_origin(e.origin) and frag_brush is not None:
                    for col in range(child.columnCount()):
                        child.setForeground(col, frag_brush)
                    n_frag += 1
                parent.addChild(child)
            self.tree.addTopLevelItem(parent)
            parent.setExpanded(dim == 3 and len(items) < 50)
        n = len(doc.entities)
        if n_frag:
            self.summary.setText(
                f"Total entities: {n}  (from fragment: {n_frag})"
            )
        else:
            self.summary.setText(f"Total entities: {n}")

    def _on_selection_changed(self) -> None:
        ents = self.selected_entities()
        uuids = {e.uuid for e in ents}
        # Avoid re-emitting if the viewer already has the same set
        # (this breaks the tree -> viewer -> tree loop).
        if uuids == set(self.viewer.multi_selection):
            return
        self.viewer.set_multi_selection(uuids)
        if ents:
            e = ents[-1]
            from ...bridge.picker import PickedEntity
            self.viewer.set_selection(PickedEntity(
                entity_uuid=e.uuid, dim=e.dim, tag=e.tag,
            ))
        else:
            self.viewer.set_selection(None)

    def _on_external_selection(self, picked) -> None:
        # No-op: tree <-> scene sync happens through
        # multiSelectionChanged in _on_external_multi.
        pass

    def _on_external_multi(self) -> None:
        """Sync the tree with the viewer's multi-selection."""
        target = set(self.viewer.multi_selection)
        self.tree.blockSignals(True)
        try:
            root = self.tree.invisibleRootItem()
            for i in range(root.childCount()):
                parent = root.child(i)
                for j in range(parent.childCount()):
                    child = parent.child(j)
                    uuid = str(child.data(0, 32))
                    child.setSelected(uuid in target)
        finally:
            self.tree.blockSignals(False)

    def _find_item(self, uuid: str):
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            parent = root.child(i)
            for j in range(parent.childCount()):
                child = parent.child(j)
                if str(child.data(0, 32)) == uuid:
                    return child
        return None

    # ── quick filters ───────────────────────────────────────────────

    def _select_kind(self, kind: str) -> None:
        ents = [e for e in self.viewer.api.document.entities if e.kind == kind]
        uuids = {e.uuid for e in ents}
        self.viewer.set_multi_selection(uuids)
        self.viewer.statusMessage.emit(
            f"Selected {len(uuids)} '{kind}' entities."
        )

    def _invert_selection(self) -> None:
        all_uuids = {e.uuid for e in self.viewer.api.document.entities}
        cur = set(self.viewer.multi_selection)
        self.viewer.set_multi_selection(all_uuids - cur)
        self.viewer.statusMessage.emit(
            f"Inverted: {len(all_uuids - cur)} entities selected."
        )

    def _select_by_regex(self) -> None:
        import re
        pattern = self.input_regex.text().strip()
        if not pattern:
            return
        try:
            rx = re.compile(pattern)
        except re.error as exc:
            self.viewer.statusMessage.emit(f"Invalid regex: {exc}")
            return
        matches = {e.uuid for e in self.viewer.api.document.entities
                   if rx.search(e.name or "")}
        self.viewer.set_multi_selection(matches)
        self.viewer.statusMessage.emit(
            f"Regex '{pattern}': {len(matches)} entities."
        )
