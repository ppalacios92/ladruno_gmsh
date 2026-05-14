"""Load a STEP file and open the viewer."""

from ladruno_gmsh import open_model

# session = open_model(r"C:\Users\ppala\Desktop\New folder (2)\01.step",
#                      units="mm",
#                      tolerance="auto")

# from ladruno_gmsh.io.project import load
from ladruno_gmsh import open_model

# session = open_model(r"C:\Users\ppala\Desktop\New folder (2)\01_01.ladruno")




session = open_model(r"C:\Users\ppala\Desktop\New folder\ALICE_01.stp",
                     units="mm",
                     tolerance="auto"

                     )


# for entity in session.entities:
#     print(entity.dim_tag, entity.name, entity.mass)

session.show()
