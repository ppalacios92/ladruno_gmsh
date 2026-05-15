# ladruno_gmsh

A Python broker and interactive Qt/PyVista viewer that exposes the full
power of [gmsh](https://gmsh.info) to finite-element pre-processing
workflows.

> **gmsh does all the work.** Every shape, every triangle, every
> quality metric, every Boolean intersection that this project shows
> comes from gmsh's OpenCASCADE-backed kernel. `ladruno_gmsh` is a
> thin orchestration layer: a typed Python API, an immutable domain
> model, a reproducible timeline, FEM-focused diagnostics, and a
> dockable viewer. Take gmsh out and there is no project left.

---

## What this lets you do (because gmsh lets us)

gmsh ships a complete CAD + mesh ecosystem; its Python API exposes
roughly 700 public functions. Anything in that surface is, in
principle, reachable from this project — today we wrap the busiest
parts directly, the rest is one wrapper away. The full per-function
status is tracked in [`docs/gmsh_capabilities.md`](docs/gmsh_capabilities.md).

**Geometry construction (OpenCASCADE kernel)**

- Primitives 0D / 1D / 2D / 3D: points, lines, arcs, splines, NURBS,
  curve loops, plane surfaces, surface fillings, surface loops,
  volumes.
- Solid primitives: box, sphere, cylinder, cone, wedge, torus.
- Constructive operations: extrude, revolve, thru-sections (loft),
  thick solids, pipes (sweep).
- Modifiers: fillet, chamfer, defeature, offset.
- Transformations: translate, rotate, dilate, mirror, symmetrize,
  affine, copy.

**B-Rep repair**

- `healShapes` (degenerated edges, small edges/faces, sewing,
  solid building).
- Duplicate removal.
- NURBS conversion.
- B-Rep reconstruction from a triangle soup (`classifySurfaces` +
  `createGeometry` + `createTopology`).

**Boolean operations (OCC)**

- Cut, fuse, intersect, fragment. Conformal interfaces between any
  number of volumes.

**Geometric queries**

- Entity listing, naming, bounding boxes, adjacencies, boundaries.
- Mass, center of mass, inertia tensor, mass-property pipeline.
- Distance / nearest entity, point-in-shape tests, parametric
  evaluation, normals, curvature.

**Meshing**

- Algorithms: MeshAdapt, Frontal-Delaunay, Delaunay, HXT, MMG3D,
  packing, quasi-structured quads.
- Mesh generation 1D / 2D / 3D, refinement, recombination, element
  order, optimization (Netgen, HighOrder, Laplace2D, Relocate*,
  UntangleMeshGeometry, ...).
- Per-entity controls: size, recombine, smoothing, algorithm,
  reverse, compound, embed.
- Transfinite meshing (structured): per curve, surface, volume, or
  automatic detection.

**Size fields**

- Distance, Threshold, Box, Ball, Cylinder, Frustum, MathEval (with
  anisotropic variants), Min/Max combinations, Restrict, Octree,
  Curvature, BoundaryLayer, ExternalProcess.
- Background-mesh assignment and boundary-layer attachment.

**Reorientation and reclassification**

- Reverse element / entity orientation, set-outward over volumes,
  reclassify nodes, relocate nodes.
- Reverse Cuthill-McKee and Hilbert renumbering.

**Quality and diagnostics**

- Element-quality metrics: `minSICN`, `minSIGE`, `minSJ`, `gamma`,
  `eta`, inner/outer radius, signed volume.
- Jacobians per element or in bulk.
- Duplicate detection (gmsh + KDTree backup).
- Free / non-manifold edges.
- Orphan entities and nodes.
- Volume interference (bbox + measured overlap).
- Surface normal consistency.

**Physical groups (materials / BCs)**

- Tagging by name, ID-lookup, node enumeration per group.

**Partitioning** (for MPI / parallel FEM)

- N-way partitioning with optional ghost layers, partition-entity
  queries, unpartition.

**Periodic meshing** (for homogenization / RVE)

- Per-entity periodic constraints and key extraction.

**Shape functions and quadrature** (for downstream solvers)

- Integration points, basis functions, orientations, keys,
  hierarchical Lagrange / Legendre / Hcurl spaces.

**Post-processing via gmsh views**

- `view.add` + `view.addModelData` for scalar / vector / tensor data
  on the mesh.
- 65 built-in plugins: `CutPlane`, `Isosurface`, `Skin`,
  `ExtractEdges`, `Crack`, `Warp` (displacement visualization),
  `MathEval`, `Gradient`, `Divergence`, `Curl`, `StreamLines`,
  `Particles`, `Probe`, `AnalyseMeshQuality`, and more.

**Algorithms on bare point clouds**

- Constrained Delaunay triangulation and tetrahedralization
  without an underlying B-Rep.

**I/O**

- Native: `.msh` (every version), `.geo`.
- CAD: STEP, IGES, BREP, STL via OpenCASCADE.
- Mesh: VTU, UNV, MED, INP, STL (mesh), and the rest of gmsh's
  ~30 export formats.

---

## What this project adds on top

gmsh's raw API is wide and stateful. This layer makes it usable
from Python in a way that survives long FEM workflows:

- **Single threading boundary**. gmsh is not reentrant; every call
  goes through `kernel/`, which is the only package allowed to import
  `gmsh`. The rest of the codebase touches typed domain objects.

- **Immutable domain model**. `GeometryDocument`, `Entity`,
  `MeshSnapshot`, `History` capture state by value. Operations
  produce a new document; the previous one stays addressable.

- **Stable entity identity**. OCC reassigns numeric `tag`s after
  Booleans; each entity also carries a UUID and a `lineage`, so the
  timeline survives operations that renumber everything underneath.

- **Reproducible timeline**. Every mutating call is recorded as a
  serializable `Operation`. The full sequence can be replayed with a
  changed parameter (move a tolerance, regenerate the chain) or
  serialized into a `.lgmsh` project archive.

- **FEM diagnostics on top of gmsh queries**. Orphans, duplicates
  (gmsh + KDTree backup), quality (histograms, thresholds), free
  and non-manifold edges, volume interference (bbox screen + measured
  overlap via copy-and-intersect), surface normal consistency,
  consolidated Markdown report.

- **Bridge to PyVista/VTK**. Per-entity tessellation with
  `cell_data["entity_uuid"]`, so picking returns the real entity, not
  just a triangle ID. Volumetric mesh adapter that ships gmsh
  element tags through to VTK cell data.

- **Interactive viewer (Qt + PyVista)**. Dockable panels per family
  (model tree, history, properties, healing, booleans, mesh,
  reorientation, quality, diagnostics, physical groups, console,
  export). Picking, multi-selection (Ctrl/Shift), box-select with
  AutoCAD window-vs-crossing semantics, isolate, hide, explode.

- **Reproducible project archive (`.lgmsh`)**. Zip with source
  files, JSON manifest of operations, and thumbnails. Replays from
  scratch in a clean session.

The thesis: **gmsh has the algorithms; this project has the
ergonomics**. Anything missing from the user-facing surface is a
matter of writing a thin wrapper in `kernel/` and a corresponding
`Operation` — never of implementing geometry or meshing logic.

---

## Primary use case

Models exported from Revit (STEP / IGES) that arrive with duplicated
faces, sub-tolerance gaps, and non-conformal volumes at the
intersections. The canonical recipe:

1. Import preserving OCC names.
2. `heal` with `tolerance = max(1e-6, 1e-5 × bbox_diagonal)`.
3. `fragment_all` over every volume.
4. `removeAllDuplicates`.
5. Relabel by centroid proximity.
6. `mesh.generate(3)`.
7. `diagnostics.report()`.

Every step lands in the timeline. The user edits a parameter (most
commonly the tolerance), the chain replays, and the report updates.

---

## Quick start

```python
from ladruno_gmsh import open_model

with open_model("01_ATLAS.stp", units="mm", tolerance="auto") as session:
    session.heal()
    session.fragment_all()
    session.mesh(size=0.5, order=2)

    report = session.diagnostics.report()
    print(report.as_markdown())

    session.export("clean_model.step")
    session.export("clean_model.msh")

    session.show()   # optional: launch the Qt viewer
```

`Session` is the only entry point users need; everything else
(operations, kernel wrappers, the picker, the docks) is reachable
through it.

---

## Architecture

| Layer | Responsibility |
|---|---|
| `kernel/` | The single boundary with gmsh. Thin wrappers, typed domain inputs, typed exceptions. |
| `model/` | Immutable domain: `GeometryDocument`, `Entity`, `MeshSnapshot`, `History`, `Tolerance`, `Units`. |
| `operations/` | Command pattern. Each `Operation` is a serializable dataclass that maps `(doc, params) -> doc` and records itself in the timeline. |
| `diagnostics/` | FEM checks built on `MeshSnapshot` + `GeometryDocument`: orphans, duplicates, quality, manifoldness, interference, normals, consolidated report. |
| `bridge/` | Adapters into PyVista/VTK: `tessellator`, `mesh_adapter`, `picker`, `snapshot`. |
| `viewer/` | Qt layer: window, toolbars, docks, scene, interaction (click + box-select + ESC). |
| `workers/` | Worker thread that hosts the gmsh context, isolated from the UI loop. |
| `io/` | Reproducible project format (`.lgmsh`) — zip with sources, JSON manifest, thumbnails. |

The invariant: **only `kernel/` imports `gmsh`**. Everything above it
sees typed Python objects. Full description in
[`docs/architecture.md`](docs/architecture.md).

---

## Cross-platform support

`ladruno_gmsh` runs on Windows and Linux out of the box. The viewer
auto-configures Qt to avoid known issues on each platform:

- **Linux + Wayland (Hyprland / Omarchy / KDE-Wayland)**: forces
  `QT_QPA_PLATFORM=xcb` so the viewer routes through XWayland.
  PyVistaQt + VTK draws via X11 GLX; without this Qt picks the
  Wayland-native plugin and VTK crashes with `BadWindow`.
- **Linux + Kvantum**: rewrites `QT_STYLE_OVERRIDE=Fusion` to
  sidestep Kvantum's window-management hooks that trigger the same
  `BadWindow` from the styling side.
- **Windows**: no special handling needed; Qt's defaults work.

You do not need to set these environment variables yourself — the
viewer applies them before `QApplication` is created. The behaviour
mirrors the pattern already shipping in our sibling repositories
`ShakerMakerResults` and `ShakerMaker.sw4_exporter`.

---

## Installation

```bash
# core only (CLI / scripted use, no viewer)
pip install -e .

# core + Qt/PyVista viewer
pip install -e ".[viewer]"

# everything (viewer + dev tools: pytest, ruff)
pip install -e ".[viewer,dev]"
```

Requirements:

- Python ≥ 3.10
- `gmsh ≥ 4.12` (ships with binary wheels on PyPI for Linux,
  macOS, Windows)
- `numpy`, `scipy`
- For the viewer: `pyvista ≥ 0.43`, `vtk ≥ 9.2`, `pyvistaqt ≥ 0.11`,
  `qtpy ≥ 2.4`, and a Qt binding (`PyQt5 ≥ 5.15` recommended).

---

## Status and roadmap

The codebase ships with a working pipeline for the primary use case:
STEP/IGES/BREP/STL/MSH import, full B-Rep repair, complete OCC
Booleans, 3D meshing with size control, quality and FEM diagnostics,
physical groups, reproducible projects, and an interactive viewer.

What is wrapped today vs. pending vs. out of scope is tracked
function-by-function against gmsh's API in
[`docs/gmsh_capabilities.md`](docs/gmsh_capabilities.md). The
high-value pending items (size fields with UI, transfinite
automatic, OCC modifiers like `fillet` / `chamfer` / `defeature`,
post-FEM views via `Warp`, plugin `CutPlane`) are listed in
appendix B of that document.

---

## Acknowledgments

[**gmsh**](https://gmsh.info) — Christophe Geuzaine and
Jean-François Remacle and contributors — is the engine this project
depends on. If you use `ladruno_gmsh` in research, please cite
**gmsh**:

> Geuzaine, C. and Remacle, J.-F. (2009). Gmsh: a three-dimensional
> finite element mesh generator with built-in pre- and post-
> processing facilities. *International Journal for Numerical
> Methods in Engineering* 79(11), 1309–1331.

The viewer is built on
[**PyVista**](https://pyvista.org),
[**VTK**](https://vtk.org),
[**pyvistaqt**](https://github.com/pyvista/pyvistaqt) and
[**Qt**](https://www.qt.io) via [**qtpy**](https://github.com/spyder-ide/qtpy).
Spatial search uses [**SciPy**](https://scipy.org); numerics rely on
[**NumPy**](https://numpy.org).

This project would not exist without any of them. We ship a layer;
they ship the actual capability.

---

## License

MIT. See [`LICENSE`](LICENSE).
