"""B-Rep healing controls."""
from __future__ import annotations

from ..deps import require_dependencies


class HealingDock:
    def __init__(self, viewer_session, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        self.viewer = viewer_session

        self.dock = QtWidgets.QDockWidget("Healing", parent)
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QFormLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)

        self.chk_auto_tol = QtWidgets.QCheckBox("auto")
        self.chk_auto_tol.setChecked(True)
        self.spin_tol = QtWidgets.QDoubleSpinBox()
        self.spin_tol.setDecimals(8)
        self.spin_tol.setRange(0.0, 1.0e6)
        self.spin_tol.setSingleStep(0.001)
        self.spin_tol.setEnabled(False)
        tol_row = QtWidgets.QHBoxLayout()
        tol_row.addWidget(self.chk_auto_tol)
        tol_row.addWidget(self.spin_tol)
        layout.addRow("Tolerance:", _wrap_layout(tol_row, QtWidgets))

        self.chk_fix_degen = QtWidgets.QCheckBox("fix degenerated")
        self.chk_fix_se = QtWidgets.QCheckBox("fix small edges")
        self.chk_fix_sf = QtWidgets.QCheckBox("fix small faces")
        self.chk_sew = QtWidgets.QCheckBox("sew faces")
        self.chk_solids = QtWidgets.QCheckBox("make solids")
        for chk in (self.chk_fix_degen, self.chk_fix_se, self.chk_fix_sf,
                    self.chk_sew, self.chk_solids):
            chk.setChecked(True)
            layout.addRow("", chk)

        self.btn_heal = QtWidgets.QPushButton("Heal")
        self.btn_dups = QtWidgets.QPushButton("Remove all duplicates")
        self.btn_clean = QtWidgets.QPushButton("Clean Revit (recipe)")
        # Sew loose faces and build solids (the inverse of Explode).
        # Only sew + make_solids; the other heal fixes are not applied.
        self.btn_merge_solid = QtWidgets.QPushButton(
            "Merge to solid (close volume)"
        )
        layout.addRow("", self.btn_heal)
        layout.addRow("", self.btn_dups)
        layout.addRow("", self.btn_clean)
        layout.addRow("", self.btn_merge_solid)

        self.dock.setWidget(widget)

        self.chk_auto_tol.toggled.connect(
            lambda v: self.spin_tol.setEnabled(not v)
        )
        self.btn_heal.clicked.connect(self._heal)
        self.btn_dups.clicked.connect(
            lambda: self.viewer.run_method("remove_all_duplicates")
        )
        self.btn_clean.clicked.connect(self._clean_revit)
        self.btn_merge_solid.clicked.connect(self._merge_to_solid)

    def _merge_to_solid(self) -> None:
        """If a multi-selection is active, operate only on those faces;
        otherwise, operate on every surface in the document."""
        tol = None if self.chk_auto_tol.isChecked() else self.spin_tol.value()
        ents = self.viewer.get_selected_entities()
        # Filter to dim=2 (the op would skip the rest anyway, but this
        # makes the user-facing message clear when volumes were
        # selected by mistake).
        face_uuids = tuple(e.uuid for e in ents if e.dim == 2)
        self.viewer.run_method(
            "merge_to_solid",
            entities=face_uuids,
            tolerance=tol,
        )

    def _heal(self) -> None:
        tol = None if self.chk_auto_tol.isChecked() else self.spin_tol.value()
        self.viewer.run_method(
            "heal",
            tolerance=tol,
            fix_degenerated=self.chk_fix_degen.isChecked(),
            fix_small_edges=self.chk_fix_se.isChecked(),
            fix_small_faces=self.chk_fix_sf.isChecked(),
            sew_faces=self.chk_sew.isChecked(),
            make_solids=self.chk_solids.isChecked(),
        )

    def _clean_revit(self) -> None:
        tol = None if self.chk_auto_tol.isChecked() else self.spin_tol.value()
        self.viewer.run_method(
            "clean_revit",
            tolerance=tol,
            make_solids=self.chk_solids.isChecked(),
        )


def _wrap_layout(layout, QtWidgets):
    w = QtWidgets.QWidget()
    w.setLayout(layout)
    layout.setContentsMargins(0, 0, 0, 0)
    return w
