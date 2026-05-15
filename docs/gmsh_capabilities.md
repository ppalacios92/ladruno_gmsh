# gmsh capabilities — full map for `ladruno_gmsh`

Exhaustive reference of the gmsh Python API (`gmsh-master/api/gmsh.py`,
~700 public functions) organized by FEM workflow phase. Each function
carries its status in our broker:

- ✅ **Wrapped** in `kernel/` or exposed via `Session` / `operations`.
- 🟡 **Partial** — the call exists but parameters or a matching
  operation in `Session` are missing.
- 🔴 **Pending** — not touched yet.
- ➖ **Not planned** — out of current scope (e.g. ONELAB, the `.geo`
  parser).

This document does NOT replace the official documentation. It is a
map for prioritizing which gmsh functions we surface in the viewer
and why.

---

## 0. Session and lifecycle

| gmsh | Status | Wrapper |
|---|---|---|
| `initialize(argv, readConfigFiles, run, interruptible)` | ✅ | `kernel.session.GmshSession.initialize` |
| `isInitialized()` | ✅ | `GmshSession.initialized` |
| `finalize()` | ✅ | `GmshSession.finalize` |
| `clear()` | 🔴 | (clear the whole context) |
| `model.add(name)` | ✅ | `GmshSession.add_model` |
| `model.remove()` | ✅ | `GmshSession.remove_model` |
| `model.list()` | ✅ | `GmshSession.list_models` |
| `model.setCurrent(name)` | ✅ | `GmshSession.set_current` |
| `model.getCurrent()` | ✅ | `GmshSession.current_model` |
| `model.getFileName()` / `setFileName(s)` | 🔴 | (bind a file to a model) |
| `model.getDimension()` | 🔴 | trivial |

---

## 1. Import and B-Rep repair

### Import

| gmsh | Status | Wrapper |
|---|---|---|
| `gmsh.open(file)` | ✅ | `kernel.io.import_shapes` (for `.stl`, `.msh`) |
| `gmsh.merge(file)` | ✅ | `Session.merge` + `MergeOp` (delegates to `kernel.io.import_shapes`) |
| `model.occ.importShapes(file, highestDimOnly, format)` | ✅ | `kernel.io.import_shapes` |
| `model.occ.importShapesNativePointer(shape, highestDimOnly)` | 🔴 | requires an OCCT pointer |
| `model.mesh.importStl()` | 🔴 | read STL as a discrete mesh |

### OCC repair

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.healShapes(dimTags, tolerance, fixDegenerated, fixSmallEdges, fixSmallFaces, sewFaces, makeSolids)` | ✅ | `kernel.healing.heal` + `HealOp` |
| `model.occ.removeAllDuplicates()` | ✅ | `kernel.healing.remove_all_duplicates` + `RemoveAllDuplicatesOp` |
| `model.occ.convertToNURBS(dimTags)` | ✅ | `kernel.healing.convert_to_nurbs` |
| `model.geo.removeAllDuplicates()` | 🔴 | built-in kernel variant |
| (in-house: sew faces and rebuild a solid) | ✅ | `Session.merge_to_solid` + `MergeToSolidOp` (composite over `occ.healShapes` with `sewFaces=True`, `makeSolids=True`) |
| (in-house composite: heal + remove_all_duplicates + fragment_all) | ✅ | `Session.clean_revit` (no dedicated Op — each step records its own timeline node) |

### Write

| gmsh | Status | Wrapper |
|---|---|---|
| `gmsh.write(file)` (inferred by extension) | ✅ | `kernel.io.write` + `Session.export` / `Session.export_many` + `ExportOp` |

---

## 2. Geometry construction

Two kernels are available: **built-in (`model.geo`)** oriented toward
`.geo` files and compatibility, and **OpenCASCADE (`model.occ`)**
which is what we use. Here we prioritize `occ`.

### 2.1 OCC — 0D/1D/2D primitives

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.addPoint(x, y, z, meshSize, tag)` | 🔴 | build points from Python |
| `model.occ.addLine(p0, p1, tag)` | 🔴 | |
| `model.occ.addCircleArc(s, m, e, tag, center)` | 🔴 | |
| `model.occ.addCircle(x, y, z, r, tag, angle1, angle2, zAxis, xAxis)` | 🔴 | |
| `model.occ.addEllipseArc / addEllipse` | 🔴 | |
| `model.occ.addSpline(points, tag, tangents)` | 🔴 | |
| `model.occ.addBSpline(points, ..., degree, weights, knots, multiplicities)` | 🔴 | low-level NURBS |
| `model.occ.addBezier / addPolyline` | 🔴 | |
| `model.occ.addWire(curves, tag, checkClosed)` | 🔴 | |
| `model.occ.addCurveLoop(curves, tag)` | 🔴 | required for surfaces |
| `model.occ.addRectangle(x, y, z, dx, dy, tag, roundedRadius)` | 🔴 | useful for sketches |
| `model.occ.addDisk(xc, yc, zc, rx, ry, tag, zAxis, xAxis)` | 🔴 | |
| `model.occ.addPlaneSurface(wireTags, tag)` | 🔴 | |
| `model.occ.addSurfaceFilling(...)` | 🔴 | surface over a 3D wire |
| `model.occ.addBSplineFilling / addBezierFilling` | 🔴 | |
| `model.occ.addBSplineSurface / addBezierSurface` | 🔴 | |
| `model.occ.addTrimmedSurface(surfaceTag, wireTags, ...)` | 🔴 | |
| `model.occ.addSurfaceLoop(surfaces, tag, sewing)` | 🔴 | |
| `model.occ.addVolume(shells, tag)` | 🔴 | |

### 2.2 OCC — 3D solid primitives

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.addSphere(xc, yc, zc, r, tag, angle1, angle2, angle3)` | 🔴 | |
| `model.occ.addBox(x, y, z, dx, dy, dz, tag)` | ✅ (internal use) | used in synthetic tests |
| `model.occ.addCylinder(x, y, z, dx, dy, dz, r, tag, angle)` | 🔴 | |
| `model.occ.addCone(x, y, z, dx, dy, dz, r1, r2, tag, angle)` | 🔴 | |
| `model.occ.addWedge(x, y, z, dx, dy, dz, tag, ltx, zAxis)` | 🔴 | |
| `model.occ.addTorus(x, y, z, r1, r2, tag, angle, zAxis)` | 🔴 | |

### 2.3 OCC — advanced constructive operations

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.addThruSections(wires, tag, makeSolid, makeRuled, ...)` | 🔴 | loft between wires |
| `model.occ.addThickSolid(volumeTag, excludeSurfaceTags, offset, tag)` | 🔴 | thicken from a surface |
| `model.occ.addPipe(dimTags, wireTag, trihedron)` | 🔴 | sweep |

### 2.4 OCC — extrusions and revolutions

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.extrude(dimTags, dx, dy, dz, numElements, heights, recombine)` | 🔴 | |
| `model.occ.revolve(dimTags, x, y, z, ax, ay, az, angle, ...)` | 🔴 | |
| `model.geo.extrude / revolve / twist / extrudeBoundaryLayer` | 🔴 | built-in kernel equivalent |

### 2.5 `geo` (built-in CAD) — only when needed

For our priority case (Revit STEP → FEM) `geo` is NOT used. Should we
ever need to author geometry in Python without OCC, every equivalent
primitive exists in `model.geo.*`. Global status: 🔴 (not prioritized).

---

## 3. OCC geometric modifiers

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.fillet(volumeTags, curveTags, radii, removeVolume)` | 🔴 | edge rounds on solids |
| `model.occ.chamfer(volumeTags, curveTags, surfaceTags, distances, removeVolume)` | 🔴 | chamfer |
| `model.occ.defeature(volumeTags, surfaceTags, removeVolume)` | 🔴 | feature removal (important for Revit cleanup) |
| `model.occ.fillet2D(edge1, edge2, radius, tag, pointTag, reverse)` | 🔴 | 2D round |
| `model.occ.chamfer2D(edge1, edge2, d1, d2, tag)` | 🔴 | |
| `model.occ.offsetCurve(curveLoopTag, offset)` | 🔴 | 2D offset |

### OCC transformations

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.translate(dimTags, dx, dy, dz)` | 🔴 | |
| `model.occ.rotate(dimTags, x, y, z, ax, ay, az, angle)` | 🔴 | |
| `model.occ.dilate(dimTags, x, y, z, a, b, c)` | 🔴 | non-uniform scale |
| `model.occ.mirror(dimTags, a, b, c, d)` | 🔴 | mirror over a plane |
| `model.occ.symmetrize(dimTags, a, b, c, d)` | 🔴 | mirror + merge |
| `model.occ.affineTransform(dimTags, affine)` | 🔴 | generic 4x4 matrix |
| `model.occ.copy(dimTags)` | 🔴 | clone entities |
| `model.occ.remove(dimTags, recursive)` | ✅ | `kernel.geometry.remove` + `RemoveEntitiesOp` |
| (in-house: replace entity with its boundary) | ✅ | `Session.explode` + `ExplodeOp` |

---

## 4. Boolean operations (OCC)

### Primitives (1:1 with gmsh)

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.fuse(objects, tools, tag, removeObject, removeTool)` | ✅ | `kernel.boolean.fuse` + `FuseOp` |
| `model.occ.cut(objects, tools, tag, removeObject, removeTool)` | ✅ | `kernel.boolean.cut` + `CutOp` |
| `model.occ.intersect(objects, tools, tag, removeObject, removeTool)` | ✅ | `kernel.boolean.intersect` + `IntersectOp` |
| `model.occ.fragment(objects, tools, tag, removeObject, removeTool)` | ✅ | `kernel.boolean.fragment` + `FragmentOp` |
| `fragment_all` (over every volume) | ✅ | `kernel.boolean.fragment_all` + `FragmentAllOp` |
| `Session.unify_all_solids(*, dim=3)` (exhaustive fuse) | ✅ | `UnifyAllOp` |

### Derived (composed from the primitives + standard CAD vocabulary)

These are not new gmsh calls — they orchestrate the primitives above
with the parameter / composition patterns expected from a CAD
boolean menu. Each one is a single timeline node.

| Operation | Status | Wrapper | gmsh recipe |
|---|---|---|---|
| Imprint (mark shared interface, keep both sides) | ✅ | `kernel.boolean.imprint` + `ImprintOp` | `fragment(objects, tools, removeObject=False, removeTool=False)` |
| Split (cut and keep every piece) | ✅ | `SplitOp` | `fragment(...)` with both `remove*=False`, distinct in the timeline so the user can edit it without affecting an imprint |
| Self-intersect (resolve auto-intersections) | ✅ | `kernel.boolean.self_intersect` + `SelfIntersectOp` | `fragment(objects, [])` |
| XOR / Symmetric difference (A ⊕ B) | ✅ | `kernel.boolean.xor` + `XorOp` | `fuse(copy(A), copy(B))` then `intersect(copy(A), copy(B))` then `cut(union, inter)` then `remove(A, B)` |
| Section (slice volumes with a plane) | ✅ | `kernel.boolean.section` + `SectionOp` | `addDisk(point, normal, auto-extent)` then `intersect(volumes, [disk], removeObject=False, removeTool=True)` |
| Hollow / Shell (thick-shell from a volume) | ✅ | `kernel.boolean.hollow` + `HollowOp` | `addThickSolid(volume, excludeSurfaceTags=open_faces, offset=thickness)` |

---

## 5. Geometric queries

### Entities

| gmsh | Status | Wrapper |
|---|---|---|
| `model.getEntities(dim)` | ✅ | `kernel.geometry.list_entities` |
| `model.setEntityName / getEntityName / removeEntityName` | ✅ | `kernel.geometry.entity_name` |
| `model.getEntitiesInBoundingBox(...)` | 🔴 | spatial filter |
| `model.getBoundingBox(dim, tag)` | ✅ | `kernel.geometry.bbox` |
| `model.occ.getBoundingBox(dim, tag)` | ✅ | preferred for OCC trim |
| `model.getEntityType(dim, tag)` | 🔴 | "Line"/"BSpline"/etc. |
| `model.getType(dim, tag)` (integer) | 🔴 | |
| `model.getEntityProperties(dim, tag)` | 🔴 | extended metadata |
| `model.getParent(dim, tag)` | 🔴 | post-boolean hierarchy |
| `model.addDiscreteEntity(dim, tag, boundary)` | 🔴 | create a discrete entity by hand |
| `model.removeEntities(dimTags, recursive)` | ✅ | `kernel.geometry.remove` |

### Topology

| gmsh | Status | Wrapper |
|---|---|---|
| `model.getBoundary(dimTags, combined, oriented, recursive)` | ✅ | `kernel.geometry.boundary` + `Session.boundary_of` |
| `model.getAdjacencies(dim, tag)` | ✅ | `kernel.geometry.adjacencies` |
| `model.isEntityOrphan(dim, tag)` | ✅ | `kernel.geometry.is_orphan` |

### OCC mass and inertia

| gmsh | Status | Wrapper |
|---|---|---|
| `model.occ.getMass(dim, tag)` | ✅ | `kernel.geometry.mass` |
| `model.occ.getCenterOfMass(dim, tag)` | ✅ | `kernel.geometry.center_of_mass` |
| `model.occ.getMatrixOfInertia(dim, tag)` | 🔴 | 3x3 inertia tensor |
| `model.occ.getDistance(dim1, tag1, dim2, tag2)` | 🔴 | minimal distance between entities |
| `model.occ.getClosestEntities(x, y, z, dimTags, n)` | 🔴 | OCC spatial KNN |
| `model.occ.getCurveLoops / getSurfaceLoops` | 🔴 | decompose wires/shells |

### Parametric

| gmsh | Status | Wrapper |
|---|---|---|
| `model.getValue(dim, tag, parametricCoord)` | 🔴 | point on a curve/surface |
| `model.getDerivative / getSecondDerivative` | 🔴 | tangents and curvatures |
| `model.getCurvature / getPrincipalCurvatures` | 🔴 | useful for manual "size from curvature" |
| `model.getNormal(tag, parametricCoord)` | 🔴 | normal on a surface |
| `model.getParametrization(dim, tag, coord)` | 🔴 | inverse point → parameter |
| `model.getParametrizationBounds(dim, tag)` | 🔴 | parametric range |
| `model.isInside(dim, tag, coord, parametric)` | 🔴 | containment test |
| `model.getClosestPoint(dim, tag, coord)` | 🔴 | snap to entity |
| `model.reparametrizeOnSurface(dim, tag, parametricCoord, surfaceTag, which)` | 🔴 | curve embedded on a surface |

### Display

| gmsh | Status | Wrapper |
|---|---|---|
| `model.setVisibility / getVisibility / setVisibilityPerWindow` | 🔴 | hide entities in FLTK |
| `model.setColor / getColor` (in gmsh) | 🔴 | our viewer handles this in VTK |
| `model.setCoordinates(tag, x, y, z)` | 🔴 | move points |
| `model.setAttribute / getAttribute / removeAttribute` | 🔴 | per-entity metadata |

---

## 6. Meshing — generation and refinement

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.generate(dim)` | ✅ | `kernel.mesh.generate` + `GenerateMeshOp` |
| `model.mesh.refine()` | ✅ | `kernel.mesh.refine` + `RefineMeshOp` |
| `model.mesh.recombine()` | ✅ | `kernel.mesh.recombine` + `RecombineOp` |
| `model.mesh.setOrder(order)` | ✅ | `kernel.mesh.set_order` + `SetOrderOp` |
| `model.mesh.optimize(method, force, niter, dimTags, quality)` | ✅ | `kernel.mesh.optimize` + `OptimizeMeshOp` |
| `model.mesh.splitQuadrangles(quality, tag)` | 🟡 | `kernel.mesh.split_quadrangles` (no `Op`) |
| `model.mesh.clear(dimTags)` | ✅ | `kernel.mesh.clear_mesh` + `ClearMeshOp` |
| `model.mesh.removeElements(dim, tag, elementTags)` | 🔴 | remove loose elements |
| `model.mesh.affineTransform(affine, dimTags)` | 🔴 | transform a mesh |

**Algorithms** (via `option.setNumber("Mesh.Algorithm", N)` and `Mesh.Algorithm3D`)

| 2D algorithm | Code | Notes |
|---|---|---|
| MeshAdapt | 1 | conservative |
| Automatic | 2 | default |
| Delaunay | 5 | fast |
| Frontal-Delaunay | 6 | best quality |
| Frontal-Delaunay-Quads | 8 | quads |
| Packing | 9 | quads |
| Quasi-Structured-Quad | 11 | aligned quads |

| 3D algorithm | Code | Notes |
|---|---|---|
| Delaunay | 1 | default |
| Frontal | 4 | |
| HXT | 10 | parallel, recommended |
| MMG3D | 7 | adaptive |

**`optimize` methods** (string):
`""` (default), `"Netgen"`, `"HighOrder"`, `"HighOrderElastic"`,
`"HighOrderFastCurving"`, `"Laplace2D"`, `"Relocate2D"`,
`"Relocate3D"`, `"QuadQuasiStructured"`, `"UntangleMeshGeometry"`.

---

## 7. Size control

### Global size

| gmsh | Status | Wrapper |
|---|---|---|
| `option.setNumber("Mesh.MeshSizeMin", X)` | ✅ | `kernel.mesh.set_size_global` |
| `option.setNumber("Mesh.MeshSizeMax", X)` | ✅ | `kernel.mesh.set_size_global` |
| `option.setNumber("Mesh.MeshSizeFactor", X)` | ✅ | inside `reset_size_options` |
| `option.setNumber("Mesh.MeshSizeFromCurvature", N)` | ✅ | `kernel.mesh.set_size_from_curvature` |
| `option.setNumber("Mesh.MeshSizeFromPoints", 0/1)` | ✅ | forced by `set_size_global` |
| `option.setNumber("Mesh.MeshSizeFromParametricPoints", 0/1)` | ✅ | inside `reset_size_options` |
| `option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0/1)` | ✅ | inside `reset_size_options` |

### Per-entity size

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.setSize(dimTags, size)` | ✅ | `kernel.mesh.set_size_on_entities` |
| `model.mesh.getSizes(dimTags)` | 🔴 | read assigned sizes |
| `model.mesh.setSizeAtParametricPoints(dim, tag, parametricCoord, sizes)` | 🔴 | |
| `model.mesh.setSizeCallback(callback)` | 🔴 | size as a Python function |
| `model.mesh.removeSizeCallback()` | 🔴 | |
| `model.mesh.setSizeFromBoundary(dim, tag, val)` | 🔴 | |

### Transfinite (structured meshes)

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.setTransfiniteCurve(tag, nPoints, type, coef)` | 🔴 | n nodes per curve with bias |
| `model.mesh.setTransfiniteSurface(tag, arrangement, corners)` | 🔴 | structured quads |
| `model.mesh.setTransfiniteVolume(tag, corners)` | 🔴 | structured hexes |
| `model.mesh.setTransfiniteAutomatic(dimTags, cornerAngle, recombine)` | 🔴 | automatic detection |

### Other controls

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.setRecombine(dim, tag, angle)` | 🔴 | quads/hexes per entity |
| `model.mesh.setSmoothing(dim, tag, val)` | 🔴 | Laplace iterations |
| `model.mesh.setReverse(dim, tag, val)` | 🔴 | flip orientation |
| `model.mesh.setAlgorithm(dim, tag, val)` | 🔴 | algorithm per entity |
| `model.mesh.setCompound(dim, tags)` | 🔴 | merge entities for meshing |
| `model.mesh.embed(dim, tags, inDim, inTag)` | 🔴 | embed curves into a surface |
| `model.mesh.removeEmbedded / getEmbedded` | 🔴 | |
| `model.mesh.removeConstraints(dimTags)` | 🔴 | drop all constraints |

---

## 8. Size fields (`model.mesh.field`)

| gmsh | Status | Wrapper |
|---|---|---|
| `field.add(type, tag)` | ✅ | `kernel.mesh.add_size_field` |
| `field.remove(tag)` | 🔴 | |
| `field.list()` | 🔴 | |
| `field.getType(tag)` | 🔴 | |
| `field.setNumber / getNumber` | ✅ | `kernel.mesh.set_field_number` |
| `field.setString / getString` | 🔴 | |
| `field.setNumbers / getNumbers` | ✅ | `kernel.mesh.set_field_numbers` |
| `field.setAsBackgroundMesh(tag)` | ✅ | `kernel.mesh.set_background_field` |
| `field.setAsBoundaryLayer(tag)` | ✅ | `kernel.mesh.boundary_layer` |

**Available field types** (string in `field.add`):

| Type | Use |
|---|---|
| `Constant` | fixed size inside a region |
| `Box` | size A inside a box, B outside |
| `Ball` | sphere version |
| `Cylinder` | cylinder version |
| `Frustum` | truncated cone |
| `Distance` | distance to points/curves/surfaces |
| `Threshold` | sigmoid curve over a distance field |
| `Attractor` | alias of `Distance` |
| `AttractorAnisoCurve` | anisotropic distance to a curve |
| `MathEval` | math expression in (x,y,z) |
| `MathEvalAniso` | 3x3 tensor with MathEval |
| `Min` / `Max` | combine multiple fields |
| `MinAniso` / `IntersectAniso` | anisotropic combination |
| `Mean` / `Laplacian` | smoothing |
| `Restrict` | apply a field only to given entities |
| `Octree` | octree discretization |
| `Curvature` | from geometric curvature |
| `Gradient` | gradient of a PostView |
| `PostView` | read size from a post-processing view |
| `Param` | parametric size |
| `Structured` | regular 3D table |
| `LonLat` | geographic projection |
| `BoundaryLayer` | boundary layer |
| `MaxEigenHessian` | metric from a Hessian |
| `Extend` | extend a field |
| `ExternalProcess` | size via STDIN/STDOUT to another process |
| `AutomaticMeshSizeField` | automatic sizing (experimental in gmsh) |

The priority for the viewer: **Distance + Threshold** (refine near
points/edges) and **Box / Ball** (refine inside a region). On the
roadmap.

---

## 9. Reorientation and reclassification

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.reverse(dimTags)` | ✅ | `kernel.reorient.reverse` + `ReverseOp` |
| `model.mesh.reverseElements(elementTags)` | ✅ | `kernel.reorient.reverse_elements` + `ReverseElementsOp` |
| `model.mesh.setOutwardOrientation(tag)` | ✅ | `kernel.reorient.set_outward` + `SetOutwardOp` |
| (set outward over every volume) | ✅ | `SetAllOutwardOp` (`session.reorient.set_all_outward()`) |
| `model.mesh.reclassifyNodes()` | ✅ | `ReclassifyNodesOp` |
| `model.mesh.relocateNodes(dim, tag)` | ✅ | `RelocateNodesOp` |
| `model.mesh.classifySurfaces(angle, boundary, forReparametrization, curveAngle, exportDiscrete)` | ✅ | `ClassifySurfacesOp` |
| `model.mesh.createGeometry(dimTags)` | ✅ | `CreateGeometryOp` |
| `model.mesh.createTopology(makeSimplyConnected, exportDiscrete)` | ✅ | `CreateTopologyOp` |

### Renumbering

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.computeRenumbering(method, elementTags)` | 🟡 | `kernel.reorient.compute_renumbering` (no `Op`) |
| `model.mesh.renumberNodes(oldTags, newTags)` | 🟡 | `kernel.reorient.renumber_nodes` |
| `model.mesh.renumberElements(oldTags, newTags)` | 🟡 | `kernel.reorient.renumber_elements` |
| `model.mesh.reorderElements(elementType, tag, ordering)` | 🔴 | |

`computeRenumbering` methods: `"RCMK"` (Reverse Cuthill-McKee),
`"Hilbert"` (Hilbert curve), `"Boundary"` (boundary first).

---

## 10. Quality and diagnostics

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.getElementQualities(tags, metric, task, numTasks)` | ✅ | `kernel.quality.element_qualities` |
| `model.mesh.getJacobians(elementType, localCoord, tag, task, numTasks)` | 🔴 | bulk jacobians |
| `model.mesh.getJacobian(elementTag, localCoord)` | ✅ | `kernel.quality.jacobian` |
| `model.mesh.getBarycenters(elementType, tag, fast, primary, task, numTasks)` | 🔴 | per-element centroids |
| `model.mesh.getDuplicateNodes(dimTags)` | ✅ | `kernel.connectivity.get_duplicate_nodes` |
| `model.mesh.removeDuplicateNodes(dimTags)` | ✅ | `kernel.connectivity.remove_duplicate_nodes` |
| `model.mesh.removeDuplicateElements(dimTags)` | ✅ | `kernel.connectivity.remove_duplicate_elements` |
| `model.mesh.getLastEntityError()` | ✅ | `kernel.mesh.get_last_entity_error` |
| `model.mesh.getLastNodeError()` | ✅ | `kernel.mesh.get_last_node_error` |

Valid metrics for `getElementQualities`:
`"minSICN"`, `"minSIGE"`, `"minSJ"`, `"gamma"`, `"eta"`,
`"innerRadius"`, `"outerRadius"`, `"volume"`.

---

## 11. Connectivity and elements

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.getNodes(dim, tag, includeBoundary, returnParametricCoord)` | ✅ | `kernel.connectivity.get_nodes` |
| `model.mesh.getNodesByElementType(elementType, tag, returnParametricCoord)` | 🔴 | |
| `model.mesh.getNode(nodeTag)` | 🔴 | |
| `model.mesh.setNode(nodeTag, coord, parametricCoord)` | 🔴 | |
| `model.mesh.addNodes(dim, tag, nodeTags, coord, parametricCoord)` | 🔴 | |
| `model.mesh.getNodesForPhysicalGroup(dim, tag)` | ✅ | `kernel.physical_groups.nodes_for_group` |
| `model.mesh.getMaxNodeTag()` | 🔴 | |
| `model.mesh.rebuildNodeCache(onlyIfNecessary)` | ✅ | `kernel.connectivity.rebuild_caches` |

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.getElements(dim, tag)` | ✅ | `kernel.connectivity.get_elements` |
| `model.mesh.getElement(elementTag)` | 🔴 | |
| `model.mesh.getElementByCoordinates(x, y, z, dim, strict)` | 🔴 | picking |
| `model.mesh.getElementsByCoordinates(x, y, z, dim, strict)` | 🔴 | |
| `model.mesh.getLocalCoordinatesInElement(elementTag, x, y, z)` | 🔴 | barycentrics |
| `model.mesh.getElementTypes(dim, tag)` | 🔴 | |
| `model.mesh.getElementType(family, order, serendip)` | 🔴 | |
| `model.mesh.getElementProperties(elementType)` | ✅ | `kernel.connectivity.get_element_properties` |
| `model.mesh.getElementsByType(elementType, tag, task, numTasks)` | 🔴 | |
| `model.mesh.getMaxElementTag()` | 🔴 | |
| `model.mesh.addElements(dim, tag, types, tags, nodeTags)` | 🔴 | |
| `model.mesh.addElementsByType(tag, type, tags, nodeTags)` | 🔴 | |
| `model.mesh.rebuildElementCache(onlyIfNecessary)` | ✅ | `rebuild_caches` |

### Edges / faces

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.getEdges(nodeTags)` | 🔴 | |
| `model.mesh.getFaces(faceType, nodeTags)` | 🔴 | |
| `model.mesh.createEdges(dimTags)` | 🔴 | |
| `model.mesh.createFaces(dimTags)` | 🔴 | |
| `model.mesh.getAllEdges()` | 🔴 | |
| `model.mesh.getAllFaces(faceType)` | 🔴 | |
| `model.mesh.addEdges(tags, nodes)` | 🔴 | |
| `model.mesh.addFaces(type, tags, nodes)` | 🔴 | |
| `model.mesh.getElementEdgeNodes(type, tag, primary, task, numTasks)` | ✅ | `kernel.connectivity.get_element_edge_nodes` |
| `model.mesh.getElementFaceNodes(type, faceType, tag, primary, task, numTasks)` | ✅ | `kernel.connectivity.get_element_face_nodes` |

### Visibility

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.setVisibility(elementTags, value)` | 🔴 | |
| `model.mesh.getVisibility(elementTags)` | 🔴 | |

---

## 12. Shape functions and quadrature

For FEM use (matrix assembly) — not a viewer priority but useful in
the future.

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.getIntegrationPoints(elementType, integrationType)` | 🔴 | Gauss points |
| `model.mesh.getBasisFunctions(elementType, localCoord, functionSpaceType, wantedOrientations)` | 🔴 | |
| `model.mesh.getBasisFunctionsOrientation(elementType, functionSpaceType, tag, task, numTasks)` | 🔴 | |
| `model.mesh.getBasisFunctionsOrientationForElement(elementTag, functionSpaceType)` | 🔴 | |
| `model.mesh.getNumberOfOrientations(elementType, functionSpaceType)` | 🔴 | |
| `model.mesh.getKeys(elementType, functionSpaceType, tag, returnCoord)` | 🔴 | |
| `model.mesh.getKeysForElement(elementTag, functionSpaceType, returnCoord)` | 🔴 | |
| `model.mesh.getKeysInformation(typeKeys, entityKeys, elementType, functionSpaceType)` | 🔴 | |
| `model.mesh.getNumberOfKeys(elementType, functionSpaceType)` | 🔴 | |

`functionSpaceType`: `"Lagrange"`, `"GradLagrange"`, `"H1Legendre"`,
`"HcurlLegendre"`, etc.

---

## 13. Physical groups (materials / BCs)

| gmsh | Status | Wrapper |
|---|---|---|
| `model.addPhysicalGroup(dim, tags, tag, name)` | ✅ | `kernel.physical_groups.add` + `AddPhysicalGroupOp` |
| `model.removePhysicalGroups(dimTags)` | ✅ | `RemovePhysicalGroupOp` |
| `model.getPhysicalGroups(dim)` | ✅ | `kernel.physical_groups.list_groups` |
| `model.getPhysicalGroupsEntities(dim)` | 🔴 | |
| `model.getEntitiesForPhysicalGroup(dim, tag)` | ✅ | used internally |
| `model.getEntitiesForPhysicalName(name)` | 🔴 | shortcut by name |
| `model.getPhysicalGroupsForEntity(dim, tag)` | 🔴 | inverse |
| `model.setPhysicalName(dim, tag, name)` | ✅ | `kernel.physical_groups.set_name` |
| `model.getPhysicalName(dim, tag)` | ✅ | used internally |
| `model.removePhysicalName(name)` | 🔴 | |
| `model.setTag(dim, tag, newTag)` | 🔴 | renumber entity |
| `model.mesh.getNodesForPhysicalGroup(dim, tag)` | ✅ | `kernel.physical_groups.nodes_for_group` |

---

## 14. Partitioning

Useful when the FEM problem will be solved in parallel / MPI.

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.partition(numPart, elementTags, partitions)` | 🔴 | partition the mesh |
| `model.mesh.createOverlaps(layers, createBoundaries)` | 🔴 | ghost layers between partitions |
| `model.mesh.getPartitionEntities(dim, tag, partition)` | 🔴 | |
| `model.mesh.getOverlapBoundary(dim, tag, partition)` | 🔴 | |
| `model.mesh.getBoundaryOverlapParent(dim, tag)` | 🔴 | |
| `model.mesh.unpartition()` | 🔴 | |
| `model.getNumberOfPartitions()` | 🔴 | |
| `model.getPartitions(dim, tag)` | 🔴 | |
| `model.mesh.getGhostElements(dim, tag)` | 🔴 | |

---

## 15. Periodicity

Periodic meshes (homogenization, RVE, etc.).

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.setPeriodic(dim, tags, tagsMaster, affineTransform)` | 🔴 | |
| `model.mesh.getPeriodic(dim, tags)` | 🔴 | |
| `model.mesh.getPeriodicNodes(dim, tag, includeHighOrderNodes)` | 🔴 | |
| `model.mesh.getPeriodicKeys(elementType, functionSpaceType, tag, returnCoord)` | 🔴 | |

---

## 16. Advanced topology

| gmsh | Status | Wrapper |
|---|---|---|
| `model.mesh.addHomologyRequest(type, domainTags, subdomainTags, dims)` | 🔴 | |
| `model.mesh.clearHomologyRequests()` | 🔴 | |
| `model.mesh.computeHomology()` | 🔴 | homology groups |
| `model.mesh.computeCrossField()` | 🔴 | cross fields for quad meshing |

---

## 17. Views (post-processing)

| gmsh | Status | Wrapper |
|---|---|---|
| `view.add(name, tag)` | 🔴 | create a post-processing view |
| `view.remove(tag)` | 🔴 | |
| `view.getIndex(tag) / getTags()` | 🔴 | |
| `view.addModelData(tag, step, modelName, dataType, tags, data, time, numComponents, partition)` | 🔴 | per-node / per-element data |
| `view.addHomogeneousModelData(...)` | 🔴 | optimized version |
| `view.getModelData / getHomogeneousModelData` | 🔴 | |
| `view.addListData(tag, dataType, numEle, data)` | 🔴 | loose data (lines, points) |
| `view.getListData(tag, returnAdaptive)` | 🔴 | |
| `view.addListDataString(tag, coord, data, style)` | 🔴 | scene labels |
| `view.getListDataStrings(tag, dim)` | 🔴 | |
| `view.setInterpolationMatrices(tag, type, d, coef, exp, dGeo, coefGeo, expGeo)` | 🔴 | |
| `view.addAlias(refTag, copyOptions, tag)` | 🔴 | |
| `view.combine(what, how, remove, copyOptions)` | 🔴 | merge views |
| `view.probe(tag, x, y, z, step, numComp, gradient, distanceMax, ...)` | 🔴 | sample at a point |
| `view.write(tag, file, append)` | 🔴 | |
| `view.option` (subclass) | 🔴 | per-view options |

**Future priority**: once we integrate FEM results (displacements,
stresses), all of this is the natural channel to show them on the
mesh in PyVista — gmsh `view`s already speak the node/element
language.

---

## 18. Plugins (post-processing and utilities)

`gmsh.plugin.setNumber/setString/run` invokes any of the 65 built-in
plugins. The ones relevant to our use case:

### Cuts and extractions (visualization)

| Plugin | Use |
|---|---|
| `CutPlane` | cut by an implicit plane |
| `CutSphere` | cut by a sphere |
| `CutBox` | cut by a box |
| `CutGrid` | grid of cuts |
| `CutMesh` | cut that preserves the mesh |
| `CutParametric` | parametric cut |
| `Isosurface` | isovalue over a scalar view |
| `Skin` | extract the skin (boundary) |
| `ExtractEdges` | edges by angle |
| `ExtractElements` | filter by threshold |
| `Crack` | create a crack by duplicating nodes |
| `Triangulate` | re-triangulate |
| `Tetrahedralize` | tetrahedralize |

### Data operations (views)

| Plugin | Use |
|---|---|
| `MathEval` | apply a math expression component-wise |
| `MathEvalFieldAniso` | anisotropic tensor |
| `Gradient` / `Divergence` / `Curl` | differential operators |
| `Eigenvalues` / `Eigenvectors` | of a tensor view |
| `ModifyComponents` | rewrite components |
| `ModulusPhase` | split into magnitude/phase |
| `HarmonicToTime` | inverse FFT |
| `Integrate` | integral over a view |
| `MinMax` | extrema |
| `Summation` | sum multiple views |
| `Mean` | average |
| `Smooth` | smoothing |
| `Probe` | value at a point |
| `Distance` | distance to entity |
| `Curl` / `Gradient` / `Divergence` | vector calculus |

### Meshing / quality

| Plugin | Use |
|---|---|
| `AnalyseMeshQuality` | detailed quality |
| `DiscretizationError` | estimated error |
| `Levelset` | cut by level-set |
| `MeshSubEntities` | edges/faces as views |
| `MeshVolume` | total volume |
| `Remove` | drop elements from a view |
| `Particles` | particles in a field |
| `StreamLines` | streamlines |
| `Warp` | deform a mesh by a field (visualize displacements) |

### Geometric / utility

| Plugin | Use |
|---|---|
| `Annotate` | scene text |
| `NewView` | empty view |
| `Transform` | rotate/translate a view |
| `LongitudeLatitude` | geographic projection |
| `BoundaryAngles` | analyze angles on a boundary |
| `BoundaryLayer` | boundary layer (alternative to the field) |
| `Bubbles` | spheres in empty regions |
| `CVTRemesh` | CVT remesh |
| `CurvedBndDist` | distance to curved boundaries |
| `Lambda2` | vortex criterion |
| `MakeSimplex` | decompose hexes/prisms into tets |
| `NearestNeighbor` | data at points -> nearest element |
| `NearToFarField` | electromagnetism |
| `SpanningTree` | spanning tree |
| `SphericalRaise` | projection to a sphere |
| `VoroMetal` | Voronoi tessellation |
| `MeshSizeFieldView` | export a field as a view |
| `FieldFromAmplitudePhase` | A·e^(iφ) → view |
| `Invisible` | hide elements |
| `GaussPoints` | view at Gauss points |
| `HomologyComputation` / `HomologyPostProcessing` | homology |
| `Scal2Tens` / `Scal2Vec` | regroup components |
| `ShowNeighborElements` | neighbors |
| `SimplePartition` | simple partitioning |

For our viewer, the immediate wins are **`Warp`** (show
displacements) and **`CutPlane`** (interactive cuts). On the roadmap.

---

## 19. Standalone algorithms

Triangulation/tetrahedralization of point clouds without associated
geometry. Useful for meshes built straight from raw coordinates.

| gmsh | Status | Wrapper |
|---|---|---|
| `algorithm.triangulate(coords, edges)` | 🔴 | 2D Delaunay on points |
| `algorithm.tetrahedralize(coords, triangles)` | 🔴 | constrained 3D Delaunay |

---

## 20. Key global options

`gmsh.option.setNumber/getNumber/setString/getString/setColor/getColor`
plus `restoreDefaults`. The options we touch **the most**:

### Mesh
- `Mesh.Algorithm` (2D), `Mesh.Algorithm3D`
- `Mesh.MeshSizeMin`, `Mesh.MeshSizeMax`, `Mesh.MeshSizeFactor`
- `Mesh.MeshSizeFromCurvature`
- `Mesh.MeshSizeFromPoints`, `Mesh.MeshSizeFromParametricPoints`
- `Mesh.MeshSizeExtendFromBoundary`
- `Mesh.RecombineAll`, `Mesh.Recombine3DAll`
- `Mesh.ElementOrder`
- `Mesh.OptimizeNetgen`, `Mesh.OptimizeThreshold`
- `Mesh.SaveAll`, `Mesh.SaveGroupsOfNodes`, `Mesh.SaveParametric`
- `Mesh.NbThreads`, `Mesh.Partitioner`
- `Mesh.AngleToleranceFacetOverlap`

### Geometry
- `Geometry.OCCBooleanPreserveNumbering`
- `Geometry.OCCFixDegenerated`, `Geometry.OCCFixSmallEdges/Faces`
- `Geometry.OCCSewFaces`, `Geometry.OCCMakeSolids`
- `Geometry.OCCFastUnbind`
- `Geometry.ScalingFactor`
- `Geometry.Tolerance`, `Geometry.ToleranceBoolean`

### General / FLTK
- `General.Terminal` (silence output)
- `General.Verbosity` (0..99)
- `General.AbortOnError`
- `General.NumThreads`

### Print / View
- `Print.Format`, `Print.Width`, `Print.Height`
- dozens of options per `View` (color, range, components, etc.)

Today we touch only a subset. The rest stays reachable via
`gmsh.option.*` directly but is NOT documented as recommended.

---

## 21. FLTK (gmsh native GUI)

NOT used by our app (we have PyVista/Qt). Listed for completeness.
Global status: ➖.

`fltk.initialize / finalize / wait / update / awake / lock / unlock /
run / isAvailable / selectEntities / selectElements / selectViews /
splitCurrentWindow / setCurrentWindow / setStatusMessage /
showContextWindow / openTreeItem / closeTreeItem`.

---

## 22. `.geo` parser and ONELAB

➖ Out of scope. Listed only for reference:

**Parser** (variables of the `.geo` language):
`getNames, setNumber, setString, getNumber, getString, clear, parse`.

**ONELAB** (coupling protocol with external solvers):
`set, get, getNames, setNumber, setString, getNumber, getString,
getChanged, setChanged, clear, run`.

---

## 23. Logger and process diagnostics

| gmsh | Status | Wrapper |
|---|---|---|
| `logger.write(message, level)` | 🔴 | |
| `logger.start() / stop()` | ✅ | `GmshSession.initialize / finalize` |
| `logger.get()` | ✅ | `GmshSession.drain_log` |
| `logger.getWallTime() / getCpuTime()` | 🔴 | profiling |
| `logger.getMemory() / getTotalMemory()` | 🔴 | RAM usage |
| `logger.getLastError()` | 🔴 | |

---

## 24. Session-level helpers (not 1:1 to gmsh)

These exist only at the `Session` layer and have no direct gmsh
counterpart — they orchestrate one or more gmsh calls under the hood
but make the user's life easier from the viewer or the API.

| Helper | Status | Note |
|---|---|---|
| `Session.undo()` | ✅ | meta-operation; rewinds the timeline and replays. No `Op` because it does not append a node. |
| `Session.boundary_of(entities, recursive)` | ✅ | thin wrapper over `kernel.geometry.boundary`. Pure query, no `Op`. |
| `Session.explode(entities)` / `Session.explode_selection(entities)` | ✅ | `ExplodeOp` — replaces an entity with its boundary. |
| `Session.merge_to_solid(entities, tolerance)` | ✅ | `MergeToSolidOp` — sew faces and build a solid (composite over `occ.healShapes`). |
| `Session.clean_revit(tolerance, make_solids)` | ✅ | composite recipe: `heal` → `remove_all_duplicates` → `fragment_all`. No `Op`; each step writes its own timeline node. |
| `Session.select_by_name / by_uuid / by_dim_tag` | ✅ | pure document queries (no gmsh call). |
| `Session.show(blocking)` | ✅ | launches `viewer.launch`. |
| `Session.export(path)` / `Session.export_many(paths)` | ✅ | `ExportOp` + `kernel.io.write`. |

---

## Appendix A — consolidated wrapper status

### Covered (✅)

- Session and models.
- STEP/IGES/BREP/STL/MSH import.
- Repair (`heal`, `remove_all_duplicates`).
- Full booleans (primitives + derived):
  `fuse`, `cut`, `intersect`, `fragment`, `fragment_all`,
  `imprint`, `split`, `self_intersect`, `xor`, `section`, `hollow`.
- Meshing: `generate`, `refine`, `recombine`, `setOrder`, `optimize`,
  `clear`, global and per-entity size control, bbox validation.
- Reorientation: `reverse`, `set_outward`, `set_all_outward`,
  `reclassifyNodes`, `relocateNodes`.
- Reconstruction: `classifySurfaces`, `createGeometry`, `createTopology`.
- Quality: `element_qualities`, `jacobian`, duplicates.
- Connectivity: nodes, elements, properties, element edges/faces.
- Physical groups: add/list/remove/set_name + nodes_for_group.
- Export: STEP/IGES/BREP/STL/MSH/VTU.
- Manipulation operations: `RemoveEntitiesOp`, `UnifyAllOp`,
  `ExplodeOp`, `MergeToSolidOp`, `MergeOp`, `ExportOp`.
- FEM diagnostics: orphans, duplicates, quality, manifoldness,
  interference, normals, consolidated report.
- Reproducible project `.lgmsh` / `.ladruno` (save + replay).
- Session-level helpers: `undo`, `clean_revit`, `boundary_of`,
  `explode`, `merge_to_solid`, `merge`, `export`/`export_many`,
  `show`, selection helpers.

### High-value pending (🔴 prioritize)

| Family | Block | Impact |
|---|---|---|
| **Size fields** | `field.add Distance/Threshold/Box/Ball/Restrict/Min/Max` + `setAsBackgroundMesh` (already wrapped at low level; missing UI). | Focused refinement at cracks, contacts, critical points. |
| **Transfinite** | `setTransfiniteCurve/Surface/Volume/Automatic` + `setRecombine`. | Structured meshes (beams, regular slabs). |
| **Modifiers** | `fillet`, `chamfer`, `defeature`. | Cleanup of unnecessary detail before meshing. |
| **Transformations** | `translate`, `rotate`, `mirror`, `copy`, `affineTransform`. | Positioning of submodels and assemblies. |
| **OCC primitives** | `addBox`, `addCylinder`, `addSphere`, `addCone`, `addTorus`. | Build support geometry from Python without external CAD. |
| **Boundary layer** | `extrudeBoundaryLayer` + `BoundaryLayerField`. | Thin layers on surfaces (CFD). |
| **`getEntityType` / `getType` / `getEntityProperties`** | Extended per-entity metadata. | Classify surfaces (planar, cylindrical, NURBS) in the Model tree. |
| **`getClosestPoint`, `getNormal`, `getCurvature`** | Parametric queries. | Smart picking, snaps, normal computation for BCs. |
| **`addElements`, `setNode`, `addNodes`** | Build a mesh by hand. | Import external meshes. |
| **Views + Warp** | `view.addModelData` + plugin `Warp`. | Show FEM results (displacements, stresses) in PyVista. |

### Medium-value pending (🟡 nice-to-have)

- Per-entity recombine, per-entity smoothing.
- `embed` (curves embedded in surfaces).
- Partitioning (MPI).
- Periodicity.
- RCMK / Hilbert renumbering (better solver cache locality).
- Plugins `CutPlane`, `Isosurface`, `Skin`.

### Low / out-of-scope pending (➖)

- Shape functions / quadrature — only if we ship our own solver.
- Homology / cross fields.
- FLTK GUI.
- `.geo` parser.
- ONELAB.
- Exotic plugins (`SphericalRaise`, `LonLat`, `NearToFarField`, ...).

---

## Appendix B — proposed roadmap from here

| Iteration | Block | Visible output |
|---|---|---|
| **I9** | **Size fields with UI**: a "Mesh sizing" dock that builds `Distance` + `Threshold` from user selections and sets them as the background mesh. | Focused refinement drawable without writing Python. |
| **I10** | **Transfinite automatic**: a "Detect structured" button that calls `setTransfiniteAutomatic` and highlights volumes mappable to hex. | Structured meshes for regular parts. |
| **I11** | **OCC modifiers**: `fillet`, `chamfer`, `defeature` from a context menu over selected edges. | Strip detail before meshing. |
| **I12** | **Post-FEM views**: `bridge.results_adapter` that takes nodes + scalars/vectors and builds a `pv.UnstructuredGrid` with `point_data`. `Warp` for displacements. | Visualize FEM results in the same viewer. |
| **I13** | **Plugin CutPlane** integrated: dock with an interactive plane. | Inspect the inside of a mesh. |
| **I14** | **OCC primitives from UI**: Sphere/Box/Cylinder dialog + boolean compose. | Build support geometry (cylinders for cutouts, etc.). |
| **I15** | **Entity metadata**: `getEntityType / getEntityProperties` in the PropertiesDock to display "Planar surface", "BSpline", radius, etc. | Identify critical surfaces. |
| **I16** | **Worker thread**: move gmsh into the `KernelWorker` so that `mesh.generate(3)` does not freeze the UI. | Long, cancelable operations. |

I9–I12 deliver the most value on top of the current viewer.

---

## Appendix C — code conventions

- Anything we need from gmsh **is wrapped in `kernel/`**. No other
  package may import `gmsh`.
- Wrappers return domain types (dataclasses, numpy arrays,
  namedtuples) — never raw gmsh structures.
- Every user-facing operation follows the `Operation` pattern
  (dataclass + `apply(doc) -> doc`) so it is serializable and
  replayable from `.ladruno`.
- Validations (size, tolerance, modifiers) live in
  `Operation.apply()` and write a note to
  `OperationNode.parameters["note"]`.

When you add a new function:

1. Wrapper in `kernel/<family>.py` (thin, translates types).
2. Matching `Operation` in `operations/<family>.py`.
3. If the user should be able to call it, expose a method on
   `Session` or in a namespace (`session.reorient.X`,
   `session.diagnostics.X`).
4. Dialog or button in `viewer/docks/<family>.py`.
5. Test in `tests/integration/test_<family>.py`.
