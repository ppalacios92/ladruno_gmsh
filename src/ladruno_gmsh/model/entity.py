"""Entity and DimTag: stable identity of OCC entities across operations."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import NamedTuple, Optional

from ..utils.numeric import BBox


class DimTag(NamedTuple):
    dim: int
    tag: int


_KIND_BY_DIM = {0: "point", 1: "curve", 2: "surface", 3: "volume"}


@dataclass(frozen=True)
class Entity:
    uuid: str
    dim_tag: DimTag
    name: str
    bbox: Optional[BBox] = None
    mass: Optional[float] = None
    center_of_mass: Optional[tuple[float, float, float]] = None
    lineage: tuple[str, ...] = field(default_factory=tuple)
    # Type of the operation that created this entity. E.g. "import",
    # "fragment", "fragment_all", "fuse", "cut", "intersect", "explode".
    # Entities preserved by a non-destructive operation (mesh, heal,
    # reorient, ...) keep the origin of the previous step.
    origin: str = ""

    @classmethod
    def new(cls,
            *,
            dim_tag: DimTag,
            name: str,
            bbox: Optional[BBox] = None,
            mass: Optional[float] = None,
            center_of_mass: Optional[tuple[float, float, float]] = None,
            lineage: tuple[str, ...] = (),
            origin: str = "") -> "Entity":
        return cls(
            uuid=uuid.uuid4().hex,
            dim_tag=dim_tag,
            name=name,
            bbox=bbox,
            mass=mass,
            center_of_mass=center_of_mass,
            lineage=lineage,
            origin=origin,
        )

    @property
    def dim(self) -> int:
        return self.dim_tag.dim

    @property
    def tag(self) -> int:
        return self.dim_tag.tag

    @property
    def kind(self) -> str:
        return _KIND_BY_DIM.get(self.dim, "unknown")
