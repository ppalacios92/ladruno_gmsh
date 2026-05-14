# Architecture

## Guiding principle

Every geometry or mesh manipulation crosses a single boundary: the
`kernel/` package. No other package imports `gmsh`. This restriction
upholds three guarantees:

1. A single thread drives gmsh (it is neither reentrant nor thread-safe).
2. Every call is recorded on the document's timeline.
3. Capture of `gmsh.logger`, `getLastEntityError` and
   `getLastNodeError` is uniform.

## Layers

### 1. `kernel/`

Thin wrappers over gmsh, organized by functional family. They accept
domain types (`DimTag`, `Tolerance`, `EntityRef`) and return typed
results. They capture OCC errors and re-emit them as typed exceptions
(`BooleanFailed`, `HealingIncomplete`, `MeshFailed`).

- `session` context lifecycle.
- `io` file read/write.
- `boolean` cut, fuse, intersect, fragment.
- `healing` healShapes, removeAllDuplicates, sewing.
- `geometry` queries (entities, boundary, bbox, mass).
- `mesh` generation, refinement, order, optimization, fields.
- `reorient` reverse, reverseElements, setOutwardOrientation, reclassifyNodes.
- `reclassify` classifySurfaces, createGeometry, createTopology
  (B-Rep reconstruction from a mesh).
- `connectivity` nodes, elements, edges, faces, duplicates.
- `quality` getElementQualities, jacobians.
- `physical_groups` physical groups.

### 2. `model/`

Immutable domain model. No gmsh or Qt dependencies.

- `GeometryDocument` complete state (entities, mesh, history).
- `Entity` stable identity with UUID and derivation lineage. Lets the
  timeline survive operations that reassign OCC tags.
- `MeshSnapshot` immutable view of the mesh.
- `OperationGraph` DAG of operations, replayable and serializable.
- `Tolerance`, `Units` explicit policies.

### 3. `operations/`

Command objects. Each operation is serializable; applied to a
`GeometryDocument` it produces the next one, is persisted in the
timeline, and can be replayed with different parameters. Operations
query the `kernel/` but never touch it directly from the viewer.

### 4. `diagnostics/`

FEM analysis over `MeshSnapshot` and `GeometryDocument`.

- `orphans` unreferenced nodes, isolated entities (`isEntityOrphan`).
- `duplicates` detection via `getDuplicateNodes` and a KDTree.
- `quality` histograms and threshold filters `minSICN`, `minSJ`,
  `gamma`, `eta`.
- `manifoldness` free edges and non-manifold edges.
- `interference` residual overlaps (checked via a copy and `intersect`).
- `normals` orientation consistency.
- `report` consolidated report.

### 5. `bridge/`

Bridge between the domain and PyVista/VTK.

- `tessellator` triangulates each OCC entity and produces a
  `pv.PolyData` with `cell_data["entity_uuid"]` and
  `cell_data["dim_tag"]`. Identity is preserved, so picking returns
  the real entity.
- `mesh_adapter` converts the volumetric mesh to a
  `pv.UnstructuredGrid` with metrics as `cell_data`.
- `picker` bidirectional VTK <-> dim_tag/element_tag mapping.
- `snapshot` materialized view consumed by the viewer.

### 6. `workers/`

A `QThread` that hosts the gmsh context. Message queue with immutable
replies. Cooperative cancellation via `gmsh.logger`. Progress
diagnostics by parsing logs.

### 7. `viewer/`

In-house Qt + PyVista layer. It borrows the ParaView dock pattern but
with domain-specific panels.

- `model_tree` tree of volumes, surfaces and meshes.
- `history` operation timeline with parameter editing.
- `boolean` compositor with two slots and tolerance.
- `healing`, `mesh`, `reorient`, `quality`, `diagnostics`,
  `physical_groups`, `console`, `export` — one dock per family.

### 8. `io/`

`.lgmsh` format: a zip with the source files, a JSON manifest of
operations, and thumbnails. Replayable.

## Control thread

The viewer (UI thread) posts a `Command` to the worker queue. The
worker runs against gmsh, produces a new `GeometryDocument` and
`MeshSnapshot`, and emits them via signal. The UI thread receives the
signal and refreshes the tree and the scene.

## Reproducibility

Each `Operation` carries inputs, parameters and an explicit tolerance.
Changing an upstream parameter replays the chain. The document hash
depends only on the operation graph, not on its execution order.

## Entity identity

OCC reassigns `tag` after booleans. The domain assigns its own UUID
and maintains `lineage` (origin operation + index). On replay the
correspondence is rebuilt by centroid and bbox proximity when the
`tag` changes.

## Conformal meshing (the Revit case)

Canonical chained recipe:

1. `import` preserving OCC names.
2. `heal` with `tolerance = max(1e-6, 1e-5 * diag_bbox)`.
3. `fragment` over every volume.
4. `removeAllDuplicates`.
5. Relabel by centroid proximity.
6. `mesh.generate(3)`.
7. `diagnostics.report()`.

Every step lands in the timeline; the user can edit `tolerance` and
the chain replays.

## Reorientation

`reverse` flips normals/tangents on 2D/1D entities.
`setOutwardOrientation` forces a face to point outside the containing
solid. `reclassifyNodes` and `relocateNodes` re-align nodes to CAD
entities after booleans. These operations land in the timeline just
like booleans.

## Roadmap

| Phase | Deliverable |
|---|---|
| F0 | Skeleton + STEP loader + tree + tessellation. |
| F1 | Heal + fragment + editable timeline. |
| F2 | 3D meshing + diagnostics (orphans, quality, non-manifold). |
| F3 | Manual booleans (cut/fuse/intersect) with a compositor. |
| F4 | Normal reorientation and surface reclassification. |
| F5 | Interactive physical groups + export (STEP/IGES/STL/MSH/VTU). |
| F6 | Reproducible `.lgmsh` project. |
| F7 | Mesh size fields and boundary layers. |
