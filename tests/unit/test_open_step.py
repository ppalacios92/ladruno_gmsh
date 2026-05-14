"""Smoke F0: open STEP, list entities, export."""
from __future__ import annotations

from pathlib import Path

import pytest

from ladruno_gmsh import (
    BBox,
    Entity,
    GeometryDocument,
    Session,
    Tolerance,
    Units,
    open_model,
)


def test_open_atlas_returns_session(atlas_step: Path) -> None:
    with open_model(atlas_step, units="mm") as s:
        assert isinstance(s, Session)
        assert isinstance(s.document, GeometryDocument)
        assert s.units is Units.MILLIMETER
        assert len(s) > 0


def test_entities_have_bbox_and_identity(atlas_step: Path) -> None:
    with open_model(atlas_step, units="mm") as s:
        for e in s.entities:
            assert isinstance(e, Entity)
            assert e.bbox is None or isinstance(e.bbox, BBox)
            assert e.uuid
            assert e.dim in (0, 1, 2, 3)


def test_global_bbox_is_finite(atlas_step: Path) -> None:
    with open_model(atlas_step, units="mm") as s:
        b = s.document.global_bbox()
        assert b is not None
        assert b.diagonal > 0.0


def test_tolerance_auto_derives_from_bbox(atlas_step: Path) -> None:
    with open_model(atlas_step, units="mm", tolerance="auto") as s:
        diag = s.document.bbox_diagonal()
        assert s.tolerance.linear >= 1.0e-6
        assert s.tolerance.linear <= max(1.0e-6, diag * 1.0e-5) + 1e-12


def test_tolerance_explicit_float(atlas_step: Path) -> None:
    with open_model(atlas_step, units="mm", tolerance=1e-3) as s:
        assert s.tolerance.linear == pytest.approx(1e-3)


def test_export_step_roundtrip(atlas_step: Path, tmp_path: Path) -> None:
    out = tmp_path / "atlas_out.step"
    with open_model(atlas_step, units="mm") as s:
        written = s.export(out)
    assert written.exists()
    assert written.stat().st_size > 0


def test_close_removes_model() -> None:
    from ladruno_gmsh.kernel.session import session

    p = Path(r"C:\Dropbox\01. Brain\11. GitHub\geometria\01.step")
    if not p.exists():
        pytest.skip(f"Fixture not available: {p}")
    s = open_model(p, units="mm")
    name = s.model_name
    assert name in session().list_models()
    s.close()
    assert name not in session().list_models()


def test_unsupported_format_raises(tmp_path: Path) -> None:
    from ladruno_gmsh import UnsupportedFormat

    fake = tmp_path / "x.xyz"
    fake.write_text("nope")
    with pytest.raises(UnsupportedFormat):
        open_model(fake)


def test_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        open_model(r"C:\does\not\exist.step")
