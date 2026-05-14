"""Multi-view with tabs and panels.

For this first version the central widget hosts a single PyVista view;
the structure is prepared for future subdivisions.
"""
from __future__ import annotations

from .deps import require_dependencies


class CentralViewArea:
    """Wraps a :class:`pyvistaqt.QtInteractor` in a simple layout."""

    def __init__(self, parent=None) -> None:
        deps = require_dependencies()
        QtWidgets = deps["QtWidgets"]
        QtInteractor = deps["QtInteractor"]

        self.widget = QtWidgets.QFrame(parent)
        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.plotter = QtInteractor(self.widget)
        layout.addWidget(self.plotter.interactor)

    def close(self) -> None:
        try:
            self.plotter.close()
        except Exception:
            pass
