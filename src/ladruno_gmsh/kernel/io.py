"""File import and write: STEP, IGES, BREP, STL, MSH."""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterable, Iterator

import gmsh

from .errors import ExportFailed, ImportFailed, UnsupportedFormat
from .session import session


@contextmanager
def _silence_stdout() -> Iterator[None]:
    """Redirect the stdout and stderr descriptors to the null device.

    Required because the OCC kernel's STEP/IGES exporter prints
    statistics directly to fd=1/fd=2 without going through
    ``gmsh.logger``.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    try:
        saved_out = os.dup(1)
        saved_err = os.dup(2)
    except (AttributeError, OSError):
        yield
        return
    devnull = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(devnull, 1)
        os.dup2(devnull, 2)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(saved_out)
        os.close(saved_err)
        os.close(devnull)


OCC_BREP_FORMATS: frozenset[str] = frozenset({
    ".step", ".stp", ".iges", ".igs", ".brep",
})

MESH_FORMATS: frozenset[str] = frozenset({
    ".stl", ".msh", ".bdf", ".inp", ".vtk", ".vtu",
})

SUPPORTED_INPUT: frozenset[str] = OCC_BREP_FORMATS | frozenset({".stl", ".msh"})

SUPPORTED_OUTPUT: frozenset[str] = OCC_BREP_FORMATS | frozenset({
    ".stl", ".msh", ".vtk", ".vtu", ".bdf", ".inp",
})


def import_shapes(path: str | Path,
                  *,
                  highest_dim_only: bool = True) -> list[tuple[int, int]]:
    """Load a geometry or mesh file into the active gmsh model.

    For B-Rep formats (STEP/IGES/BREP) uses ``model.occ.importShapes``
    and synchronizes. For meshes (STL/MSH) uses ``gmsh.open``.

    Args:
        path: Absolute or relative path.
        highest_dim_only: If ``True``, only entities of the highest
            dimension present in the file are returned.

    Returns:
        List of freshly created ``(dim, tag)`` pairs.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    ext = p.suffix.lower()
    if ext not in SUPPORTED_INPUT:
        raise UnsupportedFormat(
            f"Unsupported format: {ext}. "
            f"Accepted: {sorted(SUPPORTED_INPUT)}"
        )

    session().ensure()
    abs_path = str(p.resolve())

    if ext in OCC_BREP_FORMATS:
        try:
            dim_tags = gmsh.model.occ.importShapes(
                abs_path, highestDimOnly=highest_dim_only
            )
            gmsh.model.occ.synchronize()
        except Exception as exc:
            raise ImportFailed(f"Failed to import {p.name}: {exc}") from exc
        return [(int(d), int(t)) for d, t in dim_tags]

    try:
        gmsh.open(abs_path)
    except Exception as exc:
        raise ImportFailed(f"Failed to open {p.name}: {exc}") from exc

    entities = [(int(d), int(t)) for d, t in gmsh.model.getEntities()]
    if highest_dim_only and entities:
        max_dim = max(d for d, _ in entities)
        entities = [(d, t) for d, t in entities if d == max_dim]
    return entities


def write(path: str | Path) -> Path:
    """Export the active model. The format is inferred from the extension."""
    p = Path(path)
    ext = p.suffix.lower()
    if ext not in SUPPORTED_OUTPUT:
        raise UnsupportedFormat(
            f"Unsupported output format: {ext}. "
            f"Accepted: {sorted(SUPPORTED_OUTPUT)}"
        )

    session().ensure()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with _silence_stdout():
            gmsh.write(str(p.resolve()))
    except Exception as exc:
        raise ExportFailed(f"Failed to write {p.name}: {exc}") from exc
    return p


def write_many(paths: Iterable[str | Path]) -> list[Path]:
    """Export the active model to several formats in a single pass."""
    return [write(p) for p in paths]
