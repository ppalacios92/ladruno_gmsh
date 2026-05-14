"""Normal reorientation and element reversal."""

from ladruno_gmsh import open_model

session = open_model(r"C:\Dropbox\01. Brain\11. GitHub\geometria\03.step", units="mm")
session.heal()
session.mesh.generate(dim=2)

bad = session.diagnostics.normals.find_inconsistent()
session.reorient.reverse(entities=bad)
session.reorient.set_outward(volume=session.entities.volumes[0])
session.reorient.reclassify_nodes()
session.reorient.relocate_nodes()

session.show()
