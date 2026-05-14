"""Controlled meshing and quality evaluation."""

from ladruno_gmsh import open_model

session = open_model(r"C:\Dropbox\01. Brain\11. GitHub\geometria\01_ATLAS.stp", units="mm")
session.heal()
session.fragment_all()

session.mesh.set_algorithm(dim=2, value="Frontal-Delaunay")
session.mesh.set_algorithm(dim=3, value="HXT")
session.mesh.set_size_global(0.5)
session.mesh.generate(dim=3)
session.mesh.optimize(method="Netgen", niter=3)
session.mesh.set_order(2)

quality = session.diagnostics.quality(metric="minSICN")
print(quality.histogram(bins=20))
print("elements with SICN < 0.1:", quality.count_below(0.1))

session.show()
