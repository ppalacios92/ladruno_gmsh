"""Manual composition of boolean operations between two files."""

from ladruno_gmsh import open_model

session = open_model(r"C:\Dropbox\01. Brain\11. GitHub\geometria\01.step", units="mm")
session.merge(r"C:\Dropbox\01. Brain\11. GitHub\geometria\02.step")

structure = session.select_by_name("ATLAS/Walls")
slab = session.select_by_name("ATLAS/Slab")

session.cut(object=structure, tool=slab, remove_tool=False)
session.fragment(object=session.entities.volumes, tool=[])

session.show()
