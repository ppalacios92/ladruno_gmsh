"""Physical groups: creation, assignment and lookup by name."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import gmsh

from .session import session


DimTagPair = tuple[int, int]


@dataclass(frozen=True)
class PhysicalGroup:
    dim: int
    tag: int
    name: str
    entity_tags: tuple[int, ...]


def add(dim: int,
        entity_tags: Iterable[int],
        *,
        tag: int = -1,
        name: str = "") -> int:
    session().ensure()
    tags = [int(t) for t in entity_tags]
    new_tag = int(gmsh.model.addPhysicalGroup(int(dim), tags, tag=tag, name=name))
    if name and new_tag >= 0:
        gmsh.model.setPhysicalName(int(dim), new_tag, name)
    return new_tag


def remove(dim_tags: Optional[Iterable[DimTagPair]] = None) -> None:
    session().ensure()
    arg = [] if dim_tags is None else [(int(d), int(t)) for d, t in dim_tags]
    gmsh.model.removePhysicalGroups(arg)


def list_groups(dim: int = -1) -> list[PhysicalGroup]:
    session().ensure()
    raw = gmsh.model.getPhysicalGroups(int(dim))
    out: list[PhysicalGroup] = []
    for d, t in raw:
        name = gmsh.model.getPhysicalName(int(d), int(t)) or ""
        ents = tuple(int(x) for x in
                     gmsh.model.getEntitiesForPhysicalGroup(int(d), int(t)))
        out.append(PhysicalGroup(dim=int(d), tag=int(t),
                                 name=name, entity_tags=ents))
    return out


def set_name(dim: int, tag: int, name: str) -> None:
    session().ensure()
    gmsh.model.setPhysicalName(int(dim), int(tag), name)


def nodes_for_group(dim: int, tag: int) -> list[int]:
    session().ensure()
    try:
        node_tags, _coords = gmsh.model.mesh.getNodesForPhysicalGroup(int(dim),
                                                                      int(tag))
        return [int(n) for n in node_tags]
    except Exception:
        return []
