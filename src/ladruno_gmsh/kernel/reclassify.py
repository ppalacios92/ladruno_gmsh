"""B-Rep reconstruction from discrete mesh: classifySurfaces, createGeometry, createTopology."""
from __future__ import annotations

from math import pi
from typing import Iterable, Optional

import gmsh

from .errors import MeshFailed
from .session import session


DimTagPair = tuple[int, int]


def classify_surfaces(*,
                      angle_deg: float = 40.0,
                      boundary: bool = True,
                      for_reparametrization: bool = True,
                      curve_angle_deg: float = 180.0,
                      export_discrete: bool = True) -> None:
    """Rebuild logical faces over a discrete mesh (typical for STL).

    Afterwards :func:`create_geometry` and :func:`create_topology` can
    be invoked to obtain a B-Rep suitable for booleans.
    """
    session().ensure()
    try:
        gmsh.model.mesh.classifySurfaces(
            angle_deg * pi / 180.0,
            boundary,
            for_reparametrization,
            curve_angle_deg * pi / 180.0,
            export_discrete,
        )
    except Exception as exc:
        raise MeshFailed(f"classifySurfaces failed: {exc}") from exc


def create_geometry(dim_tags: Optional[Iterable[DimTagPair]] = None) -> None:
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    try:
        gmsh.model.mesh.createGeometry(arg)
    except Exception as exc:
        raise MeshFailed(f"createGeometry failed: {exc}") from exc


def create_topology(*,
                    make_simply_connected: bool = True,
                    export_discrete: bool = True) -> None:
    session().ensure()
    try:
        gmsh.model.mesh.createTopology(make_simply_connected, export_discrete)
    except Exception as exc:
        raise MeshFailed(f"createTopology failed: {exc}") from exc
