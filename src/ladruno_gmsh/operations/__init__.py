"""High-level operations (command pattern) acting on GeometryDocument."""
from .base import Operation
from .booleans import (
    CutOp,
    FragmentAllOp,
    FragmentOp,
    FuseOp,
    HollowOp,
    ImprintOp,
    IntersectOp,
    SectionOp,
    SelfIntersectOp,
    SplitOp,
    XorOp,
)
from .exports import ExportOp
from .geometry import ExplodeOp, MergeToSolidOp, RemoveEntitiesOp, UnifyAllOp
from .healing import HealOp, RemoveAllDuplicatesOp
from .imports import ImportOp, MergeOp
from .mesh import (
    ClearMeshOp,
    GenerateMeshOp,
    OptimizeMeshOp,
    RecombineOp,
    RefineMeshOp,
    SetOrderOp,
    SetSizeFromCurvatureOp,
)
from .physical_groups import AddPhysicalGroupOp, RemovePhysicalGroupOp
from .reclassify import (
    ClassifySurfacesOp,
    CreateGeometryOp,
    CreateTopologyOp,
)
from .reorient import (
    ReclassifyNodesOp,
    RelocateNodesOp,
    ReverseElementsOp,
    ReverseOp,
    SetAllOutwardOp,
    SetOutwardOp,
)

__all__ = [
    "Operation",
    "ImportOp",
    "MergeOp",
    "CutOp",
    "FuseOp",
    "IntersectOp",
    "FragmentOp",
    "FragmentAllOp",
    "ImprintOp",
    "SplitOp",
    "SelfIntersectOp",
    "XorOp",
    "SectionOp",
    "HollowOp",
    "HealOp",
    "RemoveAllDuplicatesOp",
    "GenerateMeshOp",
    "RefineMeshOp",
    "SetOrderOp",
    "OptimizeMeshOp",
    "RecombineOp",
    "SetSizeFromCurvatureOp",
    "ClearMeshOp",
    "ReverseOp",
    "ReverseElementsOp",
    "SetOutwardOp",
    "SetAllOutwardOp",
    "ReclassifyNodesOp",
    "RelocateNodesOp",
    "ClassifySurfacesOp",
    "CreateGeometryOp",
    "CreateTopologyOp",
    "AddPhysicalGroupOp",
    "RemovePhysicalGroupOp",
    "ExportOp",
    "RemoveEntitiesOp",
    "ExplodeOp",
    "MergeToSolidOp",
    "UnifyAllOp",
]
