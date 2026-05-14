"""Full integration: booleans, mesh, diagnostics, project, viewer."""
from __future__ import annotations

from pathlib import Path

import pytest

from ladruno_gmsh import open_model


def test_fragment_all_creates_conformal_volumes(two_boxes_step: Path) -> None:
    with open_model(two_boxes_step, units="m") as s:
        assert len(s.volumes) == 2
        s.fragment_all(dim=3)
        s.remove_all_duplicates()
        assert len(s.volumes) >= 3


def test_cut_removes_intersection(two_boxes_step: Path) -> None:
    with open_model(two_boxes_step, units="m") as s:
        a, b = s.volumes[0], s.volumes[1]
        s.cut(object=[a], tool=[b], remove_object=True, remove_tool=True)
        assert len(s.volumes) >= 1
        op = s.history.nodes[-1]
        assert op.op_type == "cut"


def test_intersect_keeps_only_overlap(two_boxes_step: Path) -> None:
    with open_model(two_boxes_step, units="m") as s:
        a, b = s.volumes[0], s.volumes[1]
        s.intersect(object=[a], tool=[b])
        vols = s.volumes
        assert len(vols) == 1
        if vols[0].mass is not None:
            assert abs(vols[0].mass - 1.0) < 1e-6


def test_mesh_3d_and_quality(two_boxes_step: Path) -> None:
    with open_model(two_boxes_step, units="m") as s:
        s.fragment_all(dim=3)
        s.remove_all_duplicates()
        s.mesh(size=0.4, dim=3, algorithm_3d="HXT")
        snap = s.mesh_snapshot
        assert not snap.is_empty
        assert snap.max_dim == 3
        q = s.diagnostics.quality(metric="minSICN")
        assert q.count > 0
        assert q.count == snap.n_elements or q.count > 0


def test_diagnostics_report_runs(two_boxes_step: Path) -> None:
    with open_model(two_boxes_step, units="m") as s:
        s.fragment_all(dim=3)
        s.remove_all_duplicates()
        s.mesh(size=0.5, dim=3)
        rep = s.diagnostics.report()
        text = rep.as_markdown()
        assert "FEM Diagnostics" in text
        assert isinstance(rep.ok, bool)


def test_orphans_check_without_mesh(two_boxes_step: Path) -> None:
    with open_model(two_boxes_step, units="m") as s:
        r = s.diagnostics.orphans()
        assert r.total_node_count == 0
        assert r.isolated_node_count == 0


def test_heal_no_crash_on_real_step(step_01: Path) -> None:
    with open_model(step_01, units="mm") as s:
        n_before = len(s.entities)
        s.heal(make_solids=True)
        assert len(s.entities) > 0
        assert any(node.op_type == "heal" for node in s.history.nodes)


def test_export_msh_after_mesh(two_boxes_step: Path, tmp_path: Path) -> None:
    out = tmp_path / "boxes.msh"
    with open_model(two_boxes_step, units="m") as s:
        s.fragment_all(dim=3)
        s.remove_all_duplicates()
        s.mesh(size=0.5, dim=3)
        s.export(out)
    assert out.exists() and out.stat().st_size > 0


def test_project_save_load_roundtrip(two_boxes_step: Path,
                                     tmp_path: Path) -> None:
    from ladruno_gmsh.io.project import load, save

    with open_model(two_boxes_step, units="m") as s:
        s.fragment_all(dim=3)
        s.remove_all_duplicates()
        proj_path = save(s, tmp_path / "proj.lgmsh")
    assert proj_path.exists()

    s2 = load(proj_path)
    try:
        op_types = [n.op_type for n in s2.history.nodes]
        assert "import" in op_types
        assert "fragment_all" in op_types
        assert "remove_all_duplicates" in op_types
        assert len(s2.volumes) >= 3
    finally:
        s2.close()


def test_physical_group_creation(two_boxes_step: Path) -> None:
    with open_model(two_boxes_step, units="m") as s:
        s.physical_groups.add(name="concrete", entities=list(s.volumes))
        groups = s.physical_groups.list()
        assert any(g.name == "concrete" for g in groups)


def test_tessellation_produces_polydata(two_boxes_step: Path) -> None:
    import pyvista as pv

    from ladruno_gmsh.bridge import TessellationParameters, tessellate
    with open_model(two_boxes_step, units="m") as s:
        tess = tessellate(s.document, TessellationParameters(target_size=0.5))
        assert len(tess) > 0
        any_poly = next(iter(tess.values()))
        assert isinstance(any_poly, pv.PolyData)
        assert "entity_uuid" in any_poly.cell_data
        assert "dim" in any_poly.cell_data


def test_mesh_to_unstructured_grid(two_boxes_step: Path) -> None:
    from ladruno_gmsh.bridge import mesh_to_unstructured_grid

    with open_model(two_boxes_step, units="m") as s:
        s.fragment_all(dim=3)
        s.remove_all_duplicates()
        s.mesh(size=0.5, dim=3)
        grid = mesh_to_unstructured_grid()
        assert grid.n_cells > 0
        assert grid.n_points > 0
        assert "element_tag" in grid.cell_data
