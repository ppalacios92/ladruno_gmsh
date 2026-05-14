"""Optional viewer dependencies check."""
from __future__ import annotations

import warnings


def _silence_pyvista_known_bugs() -> None:
    """Silence harmless but noisy warnings from pyvista 0.47.3.

    1. ``UserWarning`` with a traceback mentioning ``Plotter.pickpoint``:
       pyvista tries to set a forbidden attribute on its own
       locked-down class inside the ``left_button_down`` callback when
       rectangle picking is active. The exception is caught
       internally and re-emitted as a warning. Picking still works.
    2. ``PyVistaDeprecationWarning`` about ``orig_extract_id`` (renamed
       to ``original_cell_ids`` in future versions). We already read
       our own ``entity_idx``, so we ignore it.
    """
    warnings.filterwarnings(
        "ignore", category=UserWarning, message=r"(?s).*pickpoint.*",
    )
    try:
        from pyvista.core.errors import PyVistaDeprecationWarning
        warnings.filterwarnings(
            "ignore", category=PyVistaDeprecationWarning,
            message=r"(?s).*orig_extract_id.*",
        )
    except Exception:
        pass


def require_dependencies() -> dict:
    """Validate the Qt + PyVista stack. Raises ``ImportError`` with
    install instructions if any dependency is missing."""
    missing: list[str] = []
    out: dict = {}

    try:
        import pyvista as pv
        out["pv"] = pv
    except ImportError:
        missing.append("pyvista")

    try:
        from pyvistaqt import QtInteractor
        out["QtInteractor"] = QtInteractor
    except ImportError:
        missing.append("pyvistaqt")

    try:
        import vtk
        out["vtk"] = vtk
    except ImportError:
        missing.append("vtk")

    try:
        from qtpy import QtCore, QtGui, QtWidgets
        out["QtCore"] = QtCore
        out["QtGui"] = QtGui
        out["QtWidgets"] = QtWidgets
    except ImportError:
        missing.append("qtpy")

    if missing:
        names = ", ".join(sorted(set(missing)))
        raise ImportError(
            "The viewer requires optional dependencies that are not "
            f"installed: {names}. "
            'Install with: pip install "ladruno_gmsh[viewer]"'
        )

    _silence_pyvista_known_bugs()
    return out
