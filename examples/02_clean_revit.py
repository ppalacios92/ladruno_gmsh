"""Canonical cleanup recipe for Revit exports."""

from ladruno_gmsh import open_model

session = open_model(r"C:\Dropbox\01. Brain\11. GitHub\geometria\01_ATLAS.stp",
                     units="mm",
                     tolerance="auto")

session.heal(fix_small_edges=True,
             fix_small_faces=True,
             sew_faces=True,
             make_solids=True)

session.fragment_all()
session.remove_all_duplicates()

session.mesh(size=0.5, dim=3)

report = session.diagnostics.report()
print(report.as_markdown())

session.export(r"C:\Dropbox\01. Brain\11. GitHub\geometria\atlas_clean.step")
session.export(r"C:\Dropbox\01. Brain\11. GitHub\geometria\atlas_clean.msh")
