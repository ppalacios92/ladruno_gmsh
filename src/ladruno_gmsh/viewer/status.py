"""Status bar with information chips."""
from __future__ import annotations

from .deps import require_dependencies


class StatusBar:
    """Bottom bar with count chips and transient messages."""

    def __init__(self, parent) -> None:
        deps = require_dependencies()
        self._QtWidgets = deps["QtWidgets"]

        self.bar = self._QtWidgets.QStatusBar(parent)
        self.chip_entities = self._QtWidgets.QLabel("entities: 0")
        self.chip_mesh = self._QtWidgets.QLabel("mesh: -")
        self.chip_tolerance = self._QtWidgets.QLabel("tol: -")
        self.chip_units = self._QtWidgets.QLabel("units: -")
        for w in (self.chip_entities, self.chip_mesh,
                  self.chip_tolerance, self.chip_units):
            w.setStyleSheet("padding: 0 8px;")
            self.bar.addPermanentWidget(w)

    def show_message(self, msg: str, timeout: int = 4000) -> None:
        self.bar.showMessage(msg, timeout)

    def update_from(self, session) -> None:
        n = len(session.entities)
        m = session.mesh_snapshot
        units = session.units.value
        tol = session.tolerance.linear
        self.chip_entities.setText(f"entities: {n}")
        if m.is_empty:
            self.chip_mesh.setText("mesh: -")
        else:
            self.chip_mesh.setText(
                f"mesh: {m.n_nodes} nodes / {m.n_elements} elements"
            )
        self.chip_tolerance.setText(f"tol: {tol:.3e}")
        self.chip_units.setText(f"units: {units}")
