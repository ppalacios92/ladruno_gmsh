# ladruno_gmsh

Geometry and mesh broker on top of [gmsh](https://gmsh.info), with an
interactive PyVista/Qt viewer aimed at finite-element pre-processing.

`ladruno_gmsh` does not implement geometric algebra or meshing. Its
job is to orchestrate gmsh, keep an immutable domain model with a
reproducible history, and provide a viewer in which the user composes
operations (booleans, repair, meshing, reorientation, diagnostics)
with direct visual feedback.

## Primary use case

Models exported from Revit (STEP/IGES) that arrive with duplicated
faces, sub-tolerance gaps, and non-conformal volumes at the
intersections. The application repairs them, fragments them
conformally, meshes them, evaluates quality and exports for FEM.

## Target API

```python
from ladruno_gmsh import open_model

session = open_model("01_ATLAS.stp", units="mm", tolerance="auto")

session.heal()                          # healShapes with automatic tolerance
session.fragment_all()                  # conformal interfaces between all volumes
session.mesh(size=0.5, order=2)         # 3D mesh, second order
report = session.diagnostics.report()   # orphans, quality, non-manifold, normals

session.export("clean_model.step")
session.export("clean_model.msh")

session.show()                          # optional Qt viewer
```

## Structure

- `kernel/` single boundary with gmsh
- `model/` immutable domain (Document, Entity, MeshSnapshot, History)
- `operations/` command pattern for a reproducible timeline
- `diagnostics/` FEM checks
- `bridge/` bridge to PyVista/VTK
- `viewer/` Qt layer with domain-specific panels
- `workers/` worker thread isolating gmsh from the UI
- `io/` reproducible project format

Details in [docs/architecture.md](docs/architecture.md) and the
capability map in [docs/gmsh_capabilities.md](docs/gmsh_capabilities.md).

## Installation

```
pip install -e ".[viewer,dev]"
```

## Status

Initial skeleton. Implementations are delivered in the phases defined
in `docs/architecture.md`.
