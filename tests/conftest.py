"""Shared fixtures and pytest configuration."""
from __future__ import annotations

from pathlib import Path

import pytest

from ladruno_gmsh.kernel.session import session as _session


REPO_FIXTURES = Path(r"C:\Dropbox\01. Brain\11. GitHub\geometria")


@pytest.fixture(scope="session", autouse=True)
def _gmsh_lifecycle():
    """Initialize gmsh once per test session and finalize at the end."""
    s = _session()
    s.ensure()
    yield s
    s.finalize()


@pytest.fixture
def atlas_step() -> Path:
    p = REPO_FIXTURES / "01_ATLAS.stp"
    if not p.exists():
        pytest.skip(f"Fixture not available: {p}")
    return p


@pytest.fixture
def step_01() -> Path:
    p = REPO_FIXTURES / "01.step"
    if not p.exists():
        pytest.skip(f"Fixture not available: {p}")
    return p


@pytest.fixture
def two_boxes_step(tmp_path) -> Path:
    """Synthetic STEP with two overlapping cubes for boolean tests."""
    import uuid

    import gmsh

    from ladruno_gmsh.kernel.io import _silence_stdout

    s = _session()
    s.ensure()
    name = f"_boxes_{uuid.uuid4().hex[:6]}"
    s.add_model(name)
    try:
        gmsh.model.occ.addBox(0.0, 0.0, 0.0, 2.0, 2.0, 2.0)
        gmsh.model.occ.addBox(1.0, 1.0, 1.0, 2.0, 2.0, 2.0)
        gmsh.model.occ.synchronize()
        out = tmp_path / "two_boxes.step"
        with _silence_stdout():
            gmsh.write(str(out))
    finally:
        try:
            s.remove_model()
        except Exception:
            pass
    return out
