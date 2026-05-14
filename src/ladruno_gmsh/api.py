"""High-level entry point. Exposes `open_model` and `Session`."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Iterable, Iterator, Optional, Sequence

from . import diagnostics as _diag
from .kernel import io as _io
from .kernel.session import session as _session
from .model.document import GeometryDocument
from .model.entity import DimTag, Entity
from .model.history import OperationGraph
from .model.tolerances import Tolerance
from .model.units import Units
from .operations import (
    AddPhysicalGroupOp,
    ClassifySurfacesOp,
    ClearMeshOp,
    CreateGeometryOp,
    CreateTopologyOp,
    CutOp,
    ExplodeOp,
    FragmentAllOp,
    FragmentOp,
    FuseOp,
    GenerateMeshOp,
    HealOp,
    ImportOp,
    IntersectOp,
    MergeOp,
    MergeToSolidOp,
    Operation,
    OptimizeMeshOp,
    RecombineOp,
    RefineMeshOp,
    ReclassifyNodesOp,
    RelocateNodesOp,
    RemoveAllDuplicatesOp,
    RemoveEntitiesOp,
    RemovePhysicalGroupOp,
    ReverseElementsOp,
    ReverseOp,
    SetAllOutwardOp,
    SetOrderOp,
    SetOutwardOp,
    SetSizeFromCurvatureOp,
    UnifyAllOp,
)
from .operations._helpers import op_from_node, rebuild_entities


EntitySelector = "Entity | DimTag | tuple[int, int] | str"


def _to_dim_tags(items: Iterable[EntitySelector],
                 document: GeometryDocument) -> tuple[tuple[int, int], ...]:
    out: list[tuple[int, int]] = []
    for x in items:
        if isinstance(x, Entity):
            out.append((x.dim, x.tag))
        elif isinstance(x, DimTag):
            out.append((int(x.dim), int(x.tag)))
        elif isinstance(x, tuple) and len(x) == 2:
            out.append((int(x[0]), int(x[1])))
        elif isinstance(x, str):
            e = document.find_by_uuid(x)
            if e is None:
                raise KeyError(f"UUID not found: {x}")
            out.append((e.dim, e.tag))
        else:
            raise TypeError(f"Invalid entity selector: {type(x).__name__}")
    return tuple(out)


def _to_entity_tags(items: Iterable[EntitySelector],
                    document: GeometryDocument) -> tuple[int, ...]:
    return tuple(t for _d, t in _to_dim_tags(items, document))


class _DiagnosticsNamespace:
    def __init__(self, owner: "Session") -> None:
        self._owner = owner

    def orphans(self) -> _diag.OrphansResult:
        self._owner._ensure_active()
        return _diag.orphans.check()

    def duplicates(self, *,
                   tolerance: Optional[float] = None) -> _diag.DuplicatesResult:
        self._owner._ensure_active()
        return _diag.duplicates.check(tolerance=tolerance)

    def quality(self, metric: str = "minSICN") -> _diag.QualityResult:
        self._owner._ensure_active()
        return _diag.quality.check(metric=metric)

    def manifoldness(self) -> _diag.ManifoldnessResult:
        self._owner._ensure_active()
        return _diag.manifoldness.check()

    def interference(self, *, measure: bool = False) -> _diag.InterferenceResult:
        self._owner._ensure_active()
        return _diag.interference.check(measure=measure)

    def normals(self) -> _diag.NormalsResult:
        self._owner._ensure_active()
        return _diag.normals.check()

    def report(self, *,
               quality_metric: str = "minSICN",
               dup_tolerance: Optional[float] = None,
               measure_interference: bool = False) -> _diag.Report:
        self._owner._ensure_active()
        return _diag.build(
            quality_metric=quality_metric,
            dup_tolerance=dup_tolerance,
            measure_interference=measure_interference,
        )


class _ReorientNamespace:
    def __init__(self, owner: "Session") -> None:
        self._owner = owner

    def reverse(self, entities: Iterable[EntitySelector]) -> Operation:
        dim_tags = _to_dim_tags(entities, self._owner._document)
        return self._owner._apply(ReverseOp(dim_tags=dim_tags))

    def reverse_elements(self,
                         element_tags: Iterable[int]) -> Operation:
        return self._owner._apply(
            ReverseElementsOp(element_tags=tuple(int(t) for t in element_tags))
        )

    def set_outward(self, volume: EntitySelector) -> Operation:
        dim_tags = _to_dim_tags([volume], self._owner._document)
        if not dim_tags or dim_tags[0][0] != 3:
            raise ValueError("set_outward requires a volume (dim=3)")
        return self._owner._apply(SetOutwardOp(volume_tag=dim_tags[0][1]))

    def set_all_outward(self) -> Operation:
        """Apply setOutwardOrientation to every volume."""
        return self._owner._apply(SetAllOutwardOp())

    def reclassify_nodes(self) -> Operation:
        return self._owner._apply(ReclassifyNodesOp())

    def relocate_nodes(self, *,
                       dim: int = -1, tag: int = -1) -> Operation:
        return self._owner._apply(RelocateNodesOp(dim=dim, tag=tag))


class _ReclassifyNamespace:
    def __init__(self, owner: "Session") -> None:
        self._owner = owner

    def classify_surfaces(self, *,
                          angle: float = 40.0,
                          boundary: bool = True,
                          for_reparametrization: bool = True,
                          curve_angle: float = 180.0,
                          export_discrete: bool = True) -> Operation:
        return self._owner._apply(ClassifySurfacesOp(
            angle_deg=angle,
            boundary=boundary,
            for_reparametrization=for_reparametrization,
            curve_angle_deg=curve_angle,
            export_discrete=export_discrete,
        ))

    def create_geometry(self) -> Operation:
        return self._owner._apply(CreateGeometryOp())

    def create_topology(self, *,
                        make_simply_connected: bool = True,
                        export_discrete: bool = True) -> Operation:
        return self._owner._apply(CreateTopologyOp(
            make_simply_connected=make_simply_connected,
            export_discrete=export_discrete,
        ))


class _PhysicalGroupsNamespace:
    def __init__(self, owner: "Session") -> None:
        self._owner = owner

    def add(self,
            name: str,
            entities: Iterable[EntitySelector],
            *,
            dim: Optional[int] = None) -> Operation:
        dim_tags = _to_dim_tags(entities, self._owner._document)
        if not dim_tags:
            raise ValueError("Entities are required to create the group")
        if dim is None:
            dim = dim_tags[0][0]
        tags = tuple(t for d, t in dim_tags if d == dim)
        return self._owner._apply(AddPhysicalGroupOp(
            dim=dim, entity_tags=tags, name=name,
        ))

    def list(self) -> list:
        from .kernel import physical_groups as _pg
        self._owner._ensure_active()
        return _pg.list_groups()

    def remove(self, dim_tags: Iterable[tuple[int, int]]) -> Operation:
        return self._owner._apply(RemovePhysicalGroupOp(
            dim_tags=tuple((int(d), int(t)) for d, t in dim_tags),
        ))


class Session:
    """High-level facade.

    Holds a :class:`GeometryDocument` and mediates requests against the
    kernel. Every operation is applied through :meth:`_apply` and is
    recorded in :attr:`document.history`'s timeline.
    """

    def __init__(self,
                 *,
                 document: GeometryDocument,
                 model_name: str,
                 tolerance: Tolerance) -> None:
        self._document = document
        self._model_name = model_name
        self._tolerance = tolerance
        self._closed = False

        self.diagnostics = _DiagnosticsNamespace(self)
        self.reorient = _ReorientNamespace(self)
        self.reclassify = _ReclassifyNamespace(self)
        self.physical_groups = _PhysicalGroupsNamespace(self)

    # ── Properties ───────────────────────────────────────────────────

    @property
    def document(self) -> GeometryDocument:
        return self._document

    @property
    def entities(self) -> tuple[Entity, ...]:
        return self._document.entities

    @property
    def volumes(self) -> tuple[Entity, ...]:
        return self._document.volumes

    @property
    def surfaces(self) -> tuple[Entity, ...]:
        return self._document.surfaces

    @property
    def tolerance(self) -> Tolerance:
        return self._tolerance

    @property
    def units(self) -> Units:
        return self._document.units

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def history(self) -> OperationGraph:
        return self._document.history

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def mesh_snapshot(self):
        return self._document.mesh

    # ── Selection ────────────────────────────────────────────────────

    def select_by_name(self, name: str,
                       *, contains: bool = True) -> tuple[Entity, ...]:
        if contains:
            return tuple(e for e in self._document.entities
                         if name in (e.name or ""))
        return tuple(e for e in self._document.entities if e.name == name)

    def select_by_uuid(self, uuid_str: str) -> Optional[Entity]:
        return self._document.find_by_uuid(uuid_str)

    def select_by_dim_tag(self, dim: int, tag: int) -> Optional[Entity]:
        return self._document.find_by_dim_tag(dim, tag)

    # ── Geometry: import / merge ─────────────────────────────────────

    def merge(self, path: str | Path,
              *, highest_dim_only: bool = True) -> Operation:
        return self._apply(MergeOp(path=str(Path(path)),
                                   highest_dim_only=highest_dim_only))

    # ── Healing ──────────────────────────────────────────────────────

    def heal(self, *,
             tolerance: Optional[float] = None,
             fix_degenerated: bool = True,
             fix_small_edges: bool = True,
             fix_small_faces: bool = True,
             sew_faces: bool = True,
             make_solids: bool = True) -> Operation:
        return self._apply(HealOp(
            tolerance=tolerance,
            fix_degenerated=fix_degenerated,
            fix_small_edges=fix_small_edges,
            fix_small_faces=fix_small_faces,
            sew_faces=sew_faces,
            make_solids=make_solids,
        ))

    def remove_all_duplicates(self) -> Operation:
        return self._apply(RemoveAllDuplicatesOp())

    # ── Booleans ─────────────────────────────────────────────────────

    def cut(self,
            *,
            object: Iterable[EntitySelector],
            tool: Iterable[EntitySelector],
            remove_object: bool = True,
            remove_tool: bool = True) -> Operation:
        objs = _to_dim_tags(object, self._document)
        tools = _to_dim_tags(tool, self._document)
        return self._apply(CutOp(objects=objs, tools=tools,
                                 remove_object=remove_object,
                                 remove_tool=remove_tool))

    def fuse(self,
             *,
             object: Iterable[EntitySelector],
             tool: Iterable[EntitySelector],
             remove_object: bool = True,
             remove_tool: bool = True) -> Operation:
        objs = _to_dim_tags(object, self._document)
        tools = _to_dim_tags(tool, self._document)
        return self._apply(FuseOp(objects=objs, tools=tools,
                                  remove_object=remove_object,
                                  remove_tool=remove_tool))

    def intersect(self,
                  *,
                  object: Iterable[EntitySelector],
                  tool: Iterable[EntitySelector],
                  remove_object: bool = True,
                  remove_tool: bool = True) -> Operation:
        objs = _to_dim_tags(object, self._document)
        tools = _to_dim_tags(tool, self._document)
        return self._apply(IntersectOp(objects=objs, tools=tools,
                                       remove_object=remove_object,
                                       remove_tool=remove_tool))

    def fragment(self,
                 *,
                 object: Iterable[EntitySelector],
                 tool: Iterable[EntitySelector] = (),
                 remove_object: bool = True,
                 remove_tool: bool = True) -> Operation:
        objs = _to_dim_tags(object, self._document)
        tools = _to_dim_tags(tool, self._document)
        return self._apply(FragmentOp(objects=objs, tools=tools,
                                      remove_object=remove_object,
                                      remove_tool=remove_tool))

    def fragment_all(self, *, dim: int = 3) -> Operation:
        return self._apply(FragmentAllOp(dim=dim))

    # ── Mesh ─────────────────────────────────────────────────────────

    def mesh(self,
             *,
             dim: int = 3,
             size: Optional[float] = None,
             size_min: Optional[float] = None,
             size_max: Optional[float] = None,
             order: Optional[int] = None,
             algorithm_2d: Optional[str] = None,
             algorithm_3d: Optional[str] = None) -> "Session":
        if size is not None:
            size_min = size_min if size_min is not None else size
            size_max = size_max if size_max is not None else size
        self._apply(GenerateMeshOp(
            dim=dim,
            size_min=size_min,
            size_max=size_max,
            algorithm_2d=algorithm_2d,
            algorithm_3d=algorithm_3d,
        ))
        if order is not None and order != 1:
            self._apply(SetOrderOp(order=order))
        return self

    def refine_mesh(self) -> Operation:
        return self._apply(RefineMeshOp())

    def set_order(self, order: int) -> Operation:
        return self._apply(SetOrderOp(order=order))

    def optimize_mesh(self, method: str = "",
                      *, niter: int = 1,
                      quality: float = 0.0,
                      force: bool = False) -> Operation:
        return self._apply(OptimizeMeshOp(
            method=method, niter=niter, quality=quality, force=force,
        ))

    def recombine_mesh(self) -> Operation:
        return self._apply(RecombineOp())

    def clear_mesh(self) -> Operation:
        return self._apply(ClearMeshOp())

    def mesh_size_from_curvature(self, elements_per_2pi: int = 12) -> Operation:
        return self._apply(SetSizeFromCurvatureOp(
            elements_per_2pi=elements_per_2pi,
        ))

    # ── Revit cleanup (canonical recipe) ─────────────────────────────

    def clean_revit(self, *,
                    tolerance: Optional[float] = None,
                    make_solids: bool = True,
                    fragment_dim: int = 3) -> "Session":
        """Chain heal + remove_all_duplicates + fragment_all.

        Recipe for preparing Revit exports before meshing. Each step is
        recorded independently in the timeline so it stays editable.
        """
        self.heal(tolerance=tolerance, make_solids=make_solids)
        self.remove_all_duplicates()
        if len(list(self._document.entities)) > 1:
            self.fragment_all(dim=fragment_dim)
            self.remove_all_duplicates()
        return self

    # ── Topological exploration ─────────────────────────────────────

    def boundary_of(self,
                    entities: Iterable[EntitySelector],
                    *,
                    recursive: bool = False
                    ) -> tuple[Entity, ...]:
        """Pure query: return the boundary entities (dim-1) of the given ones.

        Volume -> its surfaces. Surface -> its curves. Curve -> its
        points. With ``recursive=True`` it descends to the points in a
        single pass. Does not modify the model.
        """
        self._ensure_active()
        dim_tags = _to_dim_tags(entities, self._document)
        if not dim_tags:
            return ()
        from .kernel import geometry as _geom
        bnd = _geom.boundary(
            list(dim_tags),
            combined=False,
            oriented=False,
            recursive=recursive,
        )
        out: list[Entity] = []
        seen: set[str] = set()
        for d, t in bnd:
            tag_abs = abs(int(t))
            ent = self._document.find_by_dim_tag(int(d), tag_abs)
            if ent is not None and ent.uuid not in seen:
                seen.add(ent.uuid)
                out.append(ent)
        return tuple(out)

    def explode(self,
                entities: Iterable[EntitySelector]
                ) -> tuple[Entity, ...]:
        """Break the given entities: delete the parents leaving their
        boundary alive (volume -> faces, face -> edges, etc.).

        Destructive: the parent disappears from the document. The
        operation is recorded in the timeline and returns the new
        boundary Entity objects (with fresh UUIDs from the rebuilt
        document).
        """
        self._ensure_active()
        dim_tags = _to_dim_tags(entities, self._document)
        if not dim_tags:
            return ()
        from .kernel import geometry as _geom
        bnd = _geom.boundary(
            list(dim_tags),
            combined=False,
            oriented=False,
            recursive=False,
        )
        wanted = {(int(d), abs(int(t))) for d, t in bnd}
        self._apply(ExplodeOp(dim_tags=dim_tags))
        out: list[Entity] = []
        for e in self._document.entities:
            if (e.dim, e.tag) in wanted:
                out.append(e)
        return tuple(out)

    def explode_selection(self,
                          entities: Iterable[EntitySelector]
                          ) -> tuple[Entity, ...]:
        """Destructive alias of :meth:`explode` (UI compatibility). Use
        :meth:`boundary_of` if you only need to inspect the boundary
        without touching the model."""
        return self.explode(entities)

    # ── Direct entity manipulation ──────────────────────────────────

    def remove_entities(self,
                        entities: Iterable[EntitySelector],
                        *,
                        recursive: bool = True) -> Operation:
        dim_tags = _to_dim_tags(entities, self._document)
        if not dim_tags:
            raise ValueError("Nothing to remove")
        return self._apply(RemoveEntitiesOp(
            dim_tags=dim_tags, recursive=recursive,
        ))

    def unify_all_solids(self, *, dim: int = 3) -> Operation:
        """Fuse every volume (or surface) into a single entity.

        Meant for exporting a clean STEP to CAD after fragmenting for
        FEM.
        """
        return self._apply(UnifyAllOp(dim=dim))

    def merge_to_solid(self,
                       entities: Iterable[EntitySelector] = (),
                       *,
                       tolerance: Optional[float] = None) -> Operation:
        """Sew loose surfaces and create closed volumes.

        Typical case: after an :meth:`explode` isolated faces remain
        and you want to recompose a solid. Also useful for STL/B-Rep
        imported as face sets.

        Args:
            entities: if given, only those are processed (filtered to
                dim=2). Empty = every surface.
            tolerance: maximum closing distance. If ``None``,
                ``bbox_diagonal * 1e-6`` is used.
        """
        dim_tags = _to_dim_tags(entities, self._document) if entities else ()
        return self._apply(MergeToSolidOp(
            tolerance=tolerance, dim_tags=dim_tags,
        ))

    # ── History: undo ───────────────────────────────────────────────

    def undo(self) -> bool:
        """Replay the whole timeline except the last step.

        Returns ``True`` if there was something to undo.
        """
        nodes = self._document.history.nodes
        if len(nodes) <= 1:
            return False  # only the initial import remains
        source = self._document.source_files[0] if self._document.source_files else None
        if source is None:
            return False

        # Drop the current model and create a new one with the same name.
        s = _session()
        try:
            s.set_current(self._model_name)
            s.remove_model()
        except Exception:
            pass
        s.add_model(self._model_name)

        empty = GeometryDocument(
            entities=(),
            units=self._document.units,
            source_files=(source,),
        )
        document = empty
        for node in nodes[:-1]:
            op = op_from_node(node)
            if op is None:
                continue
            document = op.apply(document)
        self._document = document
        return True

    # ── Export ───────────────────────────────────────────────────────

    def export(self, path: str | Path) -> Path:
        self._ensure_active()
        return _io.write(path)

    def export_many(self, paths: Iterable[str | Path]) -> list[Path]:
        self._ensure_active()
        return _io.write_many(paths)

    # ── Viewer ───────────────────────────────────────────────────────

    def show(self, *, blocking: bool = True):
        """Launch the viewer window on top of this session."""
        try:
            from .viewer.session import launch as _launch
        except ImportError as exc:
            raise ImportError(
                "The viewer requires optional dependencies. "
                'Install with: pip install "ladruno_gmsh[viewer]"'
            ) from exc
        return _launch(self, blocking=blocking)

    # ── Lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        if self._closed:
            return
        try:
            s = _session()
            if self._model_name in s.list_models():
                s.set_current(self._model_name)
                s.remove_model()
        finally:
            self._closed = True

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def __iter__(self) -> Iterator[Entity]:
        return iter(self._document.entities)

    def __len__(self) -> int:
        return len(self._document.entities)

    def __repr__(self) -> str:
        n = len(self._document.entities)
        m = self._document.mesh
        mesh_info = f", mesh_nodes={m.n_nodes}" if not m.is_empty else ""
        return (f"Session(model={self._model_name!r}, entities={n}"
                f"{mesh_info}, units={self._document.units.value})")

    # ── Internals ────────────────────────────────────────────────────

    def _ensure_active(self) -> None:
        if self._closed:
            raise RuntimeError("Session closed.")
        _session().set_current(self._model_name)

    def _apply(self, op: Operation) -> Operation:
        self._ensure_active()
        self._document = op.apply(self._document)
        return op


_PROJECT_SUFFIXES = frozenset({".ladruno", ".lgmsh"})


def open_model(path: str | Path,
               *,
               units: str | Units = Units.MILLIMETER,
               tolerance: "str | float | Tolerance" = "auto",
               highest_dim_only: bool = True,
               model_name: Optional[str] = None) -> Session:
    """Load a geometry/mesh file or a .ladruno/.lgmsh project.

    - Geometry/mesh (STEP, IGES, BREP, STL, MSH): the file is imported
      and a clean session is created.
    - Project (``.ladruno`` / ``.lgmsh``): delegated to
      :func:`ladruno_gmsh.io.project.load`, which extracts the zip,
      imports the original source file and replays the whole timeline.
      To skip the replay (only open the base file), use
      ``from ladruno_gmsh.io.project import load`` directly with
      ``replay=False``.
    """
    p = Path(path)

    if p.suffix.lower() in _PROJECT_SUFFIXES:
        from .io.project import load as _load_project
        return _load_project(p)

    units_e = Units.parse(units)

    s = _session()
    s.ensure()

    if model_name is None:
        model_name = f"{p.stem}__{uuid.uuid4().hex[:8]}"
    s.add_model(model_name)

    try:
        empty = GeometryDocument(
            entities=(),
            units=units_e,
            source_files=(p,),
        )
        op = ImportOp(path=str(p), highest_dim_only=highest_dim_only)
        document = op.apply(empty)
        tol = Tolerance.resolve(tolerance, document.bbox_diagonal())
        return Session(document=document, model_name=model_name, tolerance=tol)
    except Exception:
        try:
            if model_name in s.list_models():
                s.set_current(model_name)
                s.remove_model()
        except Exception:
            pass
        raise


def _cli_main() -> int:
    """Entry point for the ``ladruno-gmsh`` script."""
    import argparse

    parser = argparse.ArgumentParser(prog="ladruno-gmsh")
    parser.add_argument("file", help="Geometry or mesh file.")
    parser.add_argument("--units", default="mm")
    parser.add_argument("--clean", action="store_true",
                        help="Apply the clean_revit recipe after loading.")
    parser.add_argument("--mesh", type=float, default=None,
                        help="Generate a 3D mesh with the given size.")
    parser.add_argument("--report", action="store_true",
                        help="Print the FEM diagnostics at the end.")
    args = parser.parse_args()

    with open_model(args.file, units=args.units) as session:
        print(session)
        if args.clean:
            session.clean_revit()
            print("clean_revit ->", session)
        if args.mesh is not None:
            session.mesh(size=args.mesh, dim=3)
            print("mesh ->", session)
        if args.report:
            print(session.diagnostics.report().as_markdown())
    return 0
