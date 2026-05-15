"""Internal helpers shared by operations.

Build ``Entity`` and ``MeshSnapshot`` instances from gmsh's current
state. Private; operations call them when closing each step.
"""
from __future__ import annotations

from typing import Any, Iterable, Mapping, Optional

from ..kernel import connectivity as _conn
from ..kernel import geometry as _geom
from ..model.document import GeometryDocument
from ..model.entity import DimTag, Entity
from ..model.history import OperationNode
from ..model.mesh_snapshot import MeshSnapshot


def rebuild_entities(
    lineage_op_id: Optional[str] = None,
    *,
    op_type: str = "",
    pre_doc: Optional[GeometryDocument] = None,
    produced_dim_tags: Optional[Iterable[tuple[int, int]]] = None,
) -> list[Entity]:
    """Rebuild the entity list from the active gmsh model.

    Rules for ``Entity.origin``:

    1. If ``produced_dim_tags`` is given (explicit list of op outputs,
       e.g. ``out`` from ``occ.fragment``), those receive ``op_type``.
       The rest preserves ``origin`` from ``pre_doc``. Needed for ops
       that recycle tags (fragment/cut/fuse: OCC tends to reuse tags
       1, 2, ... for the resulting pieces).
    2. Without ``produced_dim_tags``, default rule: if a (dim, tag)
       did not exist in ``pre_doc`` it is new and receives
       ``op_type``; if it existed, its ``origin`` is preserved.
    """
    out: list[Entity] = []
    lineage = (lineage_op_id,) if lineage_op_id else ()
    pre_by_dt: dict[tuple[int, int], Entity] = {}
    if pre_doc is not None:
        pre_by_dt = {(e.dim, e.tag): e for e in pre_doc.entities}
    produced: Optional[set[tuple[int, int]]] = None
    if produced_dim_tags is not None:
        produced = {(int(d), int(t)) for d, t in produced_dim_tags}
    for dim, tag in _geom.list_entities(-1):
        try:
            box = _geom.bbox(dim, tag)
        except Exception:
            box = None
        dt = (int(dim), int(tag))
        prev = pre_by_dt.get(dt)
        if produced is not None and dt in produced:
            origin = op_type or ""
        elif prev is not None:
            origin = prev.origin
        else:
            origin = op_type or ""
        out.append(Entity.new(
            dim_tag=DimTag(dim, tag),
            name=_geom.entity_name(dim, tag),
            bbox=box,
            mass=_geom.mass(dim, tag),
            center_of_mass=_geom.center_of_mass(dim, tag),
            lineage=lineage,
            origin=origin,
        ))
    return out


def build_mesh_snapshot() -> MeshSnapshot:
    """Take a synthetic snapshot of the current mesh."""
    try:
        nodes = _conn.get_nodes()
        elements = _conn.get_elements()
    except Exception:
        return MeshSnapshot.empty()

    by_type: dict[str, int] = {}
    max_dim = 0
    max_order = 1
    for element_type, tags in zip(elements.types, elements.tags):
        if tags.size == 0:
            continue
        try:
            props = _conn.get_element_properties(int(element_type))
        except Exception:
            continue
        by_type[props["name"]] = by_type.get(props["name"], 0) + int(tags.size)
        if props["dim"] > max_dim:
            max_dim = int(props["dim"])
        if props["order"] > max_order:
            max_order = int(props["order"])

    return MeshSnapshot(
        n_nodes=int(nodes.count),
        n_elements=int(elements.total_count),
        elements_by_type=by_type,
        max_dim=max_dim,
        order=max_order,
    )


def op_from_node(node) -> "Operation | None":
    """Rebuild an :class:`Operation` from a timeline node.

    Returns ``None`` if the type is not in the table.
    """
    from . import (  # late imports to avoid cycles
        booleans, exports, geometry, healing, imports, mesh, physical_groups,
        reclassify, reorient,
    )
    import dataclasses as _dc

    table = {
        "import": imports.ImportOp,
        "merge": imports.MergeOp,
        "heal": healing.HealOp,
        "remove_all_duplicates": healing.RemoveAllDuplicatesOp,
        "cut": booleans.CutOp,
        "fuse": booleans.FuseOp,
        "intersect": booleans.IntersectOp,
        "fragment": booleans.FragmentOp,
        "fragment_all": booleans.FragmentAllOp,
        "imprint": booleans.ImprintOp,
        "split": booleans.SplitOp,
        "self_intersect": booleans.SelfIntersectOp,
        "xor": booleans.XorOp,
        "section": booleans.SectionOp,
        "hollow": booleans.HollowOp,
        "mesh.generate": mesh.GenerateMeshOp,
        "mesh.refine": mesh.RefineMeshOp,
        "mesh.set_order": mesh.SetOrderOp,
        "mesh.optimize": mesh.OptimizeMeshOp,
        "mesh.recombine": mesh.RecombineOp,
        "mesh.size_from_curvature": mesh.SetSizeFromCurvatureOp,
        "mesh.clear": mesh.ClearMeshOp,
        "reorient.reverse": reorient.ReverseOp,
        "reorient.reverse_elements": reorient.ReverseElementsOp,
        "reorient.set_outward": reorient.SetOutwardOp,
        "reorient.reclassify_nodes": reorient.ReclassifyNodesOp,
        "reorient.relocate_nodes": reorient.RelocateNodesOp,
        "reclassify.classify_surfaces": reclassify.ClassifySurfacesOp,
        "reclassify.create_geometry": reclassify.CreateGeometryOp,
        "reclassify.create_topology": reclassify.CreateTopologyOp,
        "physical_group.add": physical_groups.AddPhysicalGroupOp,
        "physical_group.remove": physical_groups.RemovePhysicalGroupOp,
        "remove_entities": geometry.RemoveEntitiesOp,
        "explode": geometry.ExplodeOp,
        "merge_to_solid": geometry.MergeToSolidOp,
        "unify_all": geometry.UnifyAllOp,
    }
    cls = table.get(node.op_type)
    if cls is None:
        return None
    raw = dict(node.parameters or {})
    fields = {f.name for f in _dc.fields(cls)}
    params = {k: v for k, v in raw.items() if k in fields}
    for key in ("objects", "tools", "dim_tags",
                "volume_dim_tags", "open_face_dim_tags"):
        if key in params and isinstance(params[key], list):
            params[key] = tuple(tuple(int(x) for x in t) for t in params[key])
    for key in ("entity_tags", "element_tags"):
        if key in params and isinstance(params[key], list):
            params[key] = tuple(int(x) for x in params[key])
    for key in ("point", "normal"):
        if key in params and isinstance(params[key], list):
            params[key] = tuple(float(x) for x in params[key])
    return cls(**params)


def record(doc: GeometryDocument,
           *,
           op_type: str,
           parameters: Mapping[str, Any],
           rebuild_geometry: bool = True,
           rebuild_mesh: bool = False,
           input_uuids: tuple[str, ...] = (),
           produced_dim_tags: Optional[Iterable[tuple[int, int]]] = None,
           ) -> GeometryDocument:
    """Produce the next :class:`GeometryDocument` after an operation.

    ``rebuild_geometry`` requeries entities from gmsh; ``rebuild_mesh``
    refreshes the ``MeshSnapshot``. ``produced_dim_tags`` lets the op
    mark its outputs exactly (needed for fragment / cut / fuse /
    intersect, which recycle OCC tags).
    """
    entities = doc.entities
    op = OperationNode.new(
        op_type=op_type,
        inputs=input_uuids,
        parameters=parameters,
        output_uuids=(),
    )
    if rebuild_geometry:
        entities = tuple(rebuild_entities(
            lineage_op_id=op.op_id,
            op_type=op_type,
            pre_doc=doc,
            produced_dim_tags=produced_dim_tags,
        ))
        op = OperationNode(
            op_id=op.op_id,
            op_type=op.op_type,
            inputs=op.inputs,
            parameters=op.parameters,
            output_uuids=tuple(e.uuid for e in entities),
        )

    new_doc = doc.with_entities(entities).with_history(doc.history.append(op))
    if rebuild_mesh:
        new_doc = new_doc.with_mesh(build_mesh_snapshot())
    return new_doc
