"""Properties of the current selection: mass, bbox, area, OCC name."""
from __future__ import annotations

from ..deps import require_dependencies


class PropertiesDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Properties", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setLabelAlignment(
            deps["QtCore"].Qt.AlignRight | deps["QtCore"].Qt.AlignVCenter
        )

        self.labels: dict[str, "QtWidgets.QLabel"] = {}
        for key in ("uuid", "dim_tag", "kind", "name", "origin",
                    "mass", "bbox", "center", "lineage"):
            lab = QtWidgets.QLabel("-")
            lab.setTextInteractionFlags(
                deps["QtCore"].Qt.TextSelectableByMouse
            )
            self.labels[key] = lab
            layout.addRow(key + ":", lab)

        self.dock.setWidget(widget)
        viewer_session.selectionChanged.connect(self._on_selection)
        viewer_session.documentChanged.connect(self._on_doc_changed)

    def _on_selection(self, picked) -> None:
        if picked is None:
            for lab in self.labels.values():
                lab.setText("-")
            return
        doc = self.viewer.api.document
        e = doc.find_by_uuid(str(picked.entity_uuid))
        if e is None:
            return
        self.labels["uuid"].setText(e.uuid)
        self.labels["dim_tag"].setText(f"({e.dim}, {e.tag})")
        self.labels["kind"].setText(e.kind)
        self.labels["name"].setText(e.name or "")
        self.labels["origin"].setText(e.origin or "(import)")
        self.labels["mass"].setText(
            "-" if e.mass is None else f"{e.mass:.6g}"
        )
        if e.bbox is not None:
            b = e.bbox
            self.labels["bbox"].setText(
                f"[{b.xmin:.3g}, {b.ymin:.3g}, {b.zmin:.3g}] - "
                f"[{b.xmax:.3g}, {b.ymax:.3g}, {b.zmax:.3g}]"
            )
        else:
            self.labels["bbox"].setText("(unbounded)")
        if e.center_of_mass is not None:
            cx, cy, cz = e.center_of_mass
            self.labels["center"].setText(f"({cx:.3g}, {cy:.3g}, {cz:.3g})")
        else:
            self.labels["center"].setText("-")
        self.labels["lineage"].setText(
            ", ".join(e.lineage) if e.lineage else "(origin)"
        )

    def _on_doc_changed(self) -> None:
        sel = self.viewer.selection
        if sel is not None:
            self._on_selection(sel)
