"""Reconstruct a B-Rep from an STL so it can take part in booleans."""

from ladruno_gmsh import open_model

session = open_model("model.stl")

session.reclassify.classify_surfaces(angle=40.0,
                                     boundary=True,
                                     for_reparametrization=True,
                                     curve_angle=180.0)
session.reclassify.create_geometry()
session.reclassify.create_topology(make_simply_connected=True)

session.fragment_all()
session.mesh.generate(dim=3)
session.export("model_reconstructed.step")
