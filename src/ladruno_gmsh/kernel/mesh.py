"""Mesh generation and control: algorithms, sizes, order, optimization, fields."""
from __future__ import annotations

from typing import Iterable, Optional

import gmsh

from .errors import MeshFailed
from .session import session


DimTagPair = tuple[int, int]


_ALGO_2D = {
    "MeshAdapt": 1,
    "Automatic": 2,
    "InitialMeshOnly": 3,
    "Delaunay": 5,
    "Frontal-Delaunay": 6,
    "BAMG": 7,
    "Frontal-Delaunay-Quads": 8,
    "Packing": 9,
    "Quasi-Structured-Quad": 11,
}

_ALGO_3D = {
    "Delaunay": 1,
    "Frontal": 4,
    "MMG3D": 7,
    "R-tree": 9,
    "HXT": 10,
}


def set_algorithm_2d(name: str) -> None:
    if name not in _ALGO_2D:
        raise MeshFailed(f"Unknown 2D algorithm: {name}. "
                         f"Available: {sorted(_ALGO_2D)}")
    session().ensure()
    gmsh.option.setNumber("Mesh.Algorithm", _ALGO_2D[name])


def set_algorithm_3d(name: str) -> None:
    if name not in _ALGO_3D:
        raise MeshFailed(f"Unknown 3D algorithm: {name}. "
                         f"Available: {sorted(_ALGO_3D)}")
    session().ensure()
    gmsh.option.setNumber("Mesh.Algorithm3D", _ALGO_3D[name])


def set_size_global(size_min: Optional[float] = None,
                    size_max: Optional[float] = None,
                    *,
                    force_uniform: bool = True) -> None:
    """Set the global mesh size.

    When ``force_uniform`` (default), also disables
    ``Mesh.MeshSizeFromPoints`` so per-point sizes stored by a previous
    operation do **not** override the global value.
    """
    session().ensure()
    if force_uniform:
        gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    if size_min is not None:
        gmsh.option.setNumber("Mesh.MeshSizeMin", float(size_min))
    if size_max is not None:
        gmsh.option.setNumber("Mesh.MeshSizeMax", float(size_max))


def set_size_from_curvature(target_elements_per_2pi: int) -> None:
    """Enable automatic curvature-based sizing (gmsh
    ``Mesh.MeshSizeFromCurvature``)."""
    session().ensure()
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature",
                          int(target_elements_per_2pi))


def set_size_on_entities(dim_tags: Iterable[DimTagPair], size: float) -> None:
    session().ensure()
    pairs = [(int(d), int(t)) for d, t in dim_tags]
    gmsh.model.mesh.setSize(pairs, float(size))


def reset_size_options() -> None:
    """Restore the global size options to a predictable state.

    Required before a deliberate ``generate`` because viewer
    tessellation may have left ``MeshSizeFromCurvature`` or other
    overrides active that would dominate over the user's
    ``MeshSizeMin/Max``.
    """
    session().ensure()
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 1)
    gmsh.option.setNumber("Mesh.MeshSizeFromParametricPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 1)
    gmsh.option.setNumber("Mesh.MeshSizeFactor", 1.0)


def clear_mesh(dim_tags: Optional[Iterable[DimTagPair]] = None) -> None:
    """Clear the mesh from the model (or from the given subset)."""
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    gmsh.model.mesh.clear(arg)


def generate(dim: int = 3, *, clear_first: bool = True) -> None:
    """Generate the mesh. By default clears the previous mesh so that a
    size change always takes effect."""
    session().ensure()
    if clear_first:
        try:
            gmsh.model.mesh.clear([])
        except Exception:
            pass
    try:
        gmsh.model.mesh.generate(int(dim))
    except Exception as exc:
        raise MeshFailed(f"generate(dim={dim}) failed: {exc}") from exc


def refine() -> None:
    session().ensure()
    try:
        gmsh.model.mesh.refine()
    except Exception as exc:
        raise MeshFailed(f"refine failed: {exc}") from exc


def set_order(order: int) -> None:
    session().ensure()
    try:
        gmsh.model.mesh.setOrder(int(order))
    except Exception as exc:
        raise MeshFailed(f"setOrder({order}) failed: {exc}") from exc


def recombine() -> None:
    session().ensure()
    gmsh.model.mesh.recombine()


def split_quadrangles(quality: float = 1.0) -> None:
    session().ensure()
    gmsh.model.mesh.splitQuadrangles(float(quality))


def optimize(method: str = "",
             *,
             force: bool = False,
             niter: int = 1,
             dim_tags: Optional[Iterable[DimTagPair]] = None,
             quality: float = 0.0) -> None:
    """Wrapper around ``model.mesh.optimize``.

    ``method`` accepts ``""``, ``"Netgen"``, ``"HighOrder"``,
    ``"HighOrderElastic"``, ``"HighOrderFastCurving"``, ``"Laplace2D"``,
    ``"Relocate2D"``, ``"Relocate3D"``, ``"QuadQuasiStructured"``,
    ``"UntangleMeshGeometry"``.

    Tolerates the two signatures that coexist (4 vs 5 arguments) across
    gmsh versions.
    """
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    try:
        try:
            gmsh.model.mesh.optimize(
                method, force, int(niter), arg, float(quality)
            )
        except TypeError:
            gmsh.model.mesh.optimize(method, force, int(niter), arg)
    except Exception as exc:
        raise MeshFailed(f"optimize({method!r}) failed: {exc}") from exc


def clear(dim_tags: Optional[Iterable[DimTagPair]] = None) -> None:
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    gmsh.model.mesh.clear(arg)


def get_last_entity_error() -> list[DimTagPair]:
    session().ensure()
    try:
        return [(int(d), int(t))
                for d, t in gmsh.model.mesh.getLastEntityError()]
    except Exception:
        return []


def get_last_node_error() -> list[int]:
    session().ensure()
    try:
        return [int(n) for n in gmsh.model.mesh.getLastNodeError()]
    except Exception:
        return []


def add_size_field(field_type: str) -> int:
    session().ensure()
    return int(gmsh.model.mesh.field.add(field_type))


def set_field_number(tag: int, option: str, value: float) -> None:
    session().ensure()
    gmsh.model.mesh.field.setNumber(int(tag), option, float(value))


def set_field_numbers(tag: int, option: str, values: list[float]) -> None:
    session().ensure()
    gmsh.model.mesh.field.setNumbers(int(tag), option,
                                     [float(v) for v in values])


def set_background_field(tag: int) -> None:
    session().ensure()
    gmsh.model.mesh.field.setAsBackgroundMesh(int(tag))


def boundary_layer(field_tag: int) -> None:
    session().ensure()
    gmsh.model.mesh.field.setAsBoundaryLayer(int(field_tag))
