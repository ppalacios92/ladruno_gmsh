"""Auxiliary layers: normals, tangents, IDs, axes, labels."""
from __future__ import annotations

from typing import Optional

from ..bridge.snapshot import SceneSnapshot


def show_bbox(plotter, snapshot: SceneSnapshot,
              *, color: str = "#4a9eff") -> Optional[object]:
    if not snapshot.geometry:
        return None
    bounds = None
    for poly in snapshot.geometry.values():
        b = poly.bounds
        if bounds is None:
            bounds = list(b)
        else:
            bounds[0] = min(bounds[0], b[0]); bounds[1] = max(bounds[1], b[1])
            bounds[2] = min(bounds[2], b[2]); bounds[3] = max(bounds[3], b[3])
            bounds[4] = min(bounds[4], b[4]); bounds[5] = max(bounds[5], b[5])
    if bounds is None:
        return None
    try:
        actor = plotter.add_bounding_box(
            color=color, line_width=1.5, render=False, name="overlay_bbox",
        )
    except Exception:
        actor = None
    return actor


def show_normals(plotter, snapshot: SceneSnapshot,
                 *, factor: float = 0.1) -> list:
    actors: list = []
    for uuid, poly in snapshot.geometry.items():
        try:
            arrows = poly.compute_normals(
                cell_normals=True, point_normals=False,
            )
            glyph = arrows.glyph(
                orient="Normals", scale=False, factor=factor,
            )
            a = plotter.add_mesh(glyph, color="#f3b23f",
                                 name=f"overlay_normals_{uuid}")
            actors.append(a)
        except Exception:
            continue
    return actors
