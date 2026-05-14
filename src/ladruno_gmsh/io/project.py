"""Format .lgmsh: zip with sources, an operations manifest and thumbnails."""
from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..api import Session, open_model
from ..model.units import Units


MANIFEST_NAME = "manifest.json"
SOURCES_DIR = "sources"


@dataclass(frozen=True)
class ProjectManifest:
    version: str = "1"
    units: str = Units.MILLIMETER.value
    sources: tuple[str, ...] = ()
    operations: tuple[dict, ...] = ()
    tolerance_linear: float = 0.0
    tolerance_angular: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "units": self.units,
            "sources": list(self.sources),
            "operations": list(self.operations),
            "tolerance_linear": self.tolerance_linear,
            "tolerance_angular": self.tolerance_angular,
        }


VALID_SUFFIXES = (".lgmsh", ".ladruno")


def save(session: Session, path: str | Path) -> Path:
    """Package the session as ``.lgmsh`` or ``.ladruno``."""
    target = Path(path)
    if target.suffix.lower() not in VALID_SUFFIXES:
        target = target.with_suffix(".ladruno")
    target.parent.mkdir(parents=True, exist_ok=True)

    history = session.history
    operations: list[dict] = []
    for node in history.nodes:
        operations.append({
            "op_id": node.op_id,
            "op_type": node.op_type,
            "inputs": list(node.inputs),
            "parameters": dict(node.parameters),
            "output_uuids": list(node.output_uuids),
        })

    source_paths = [Path(p) for p in session.document.source_files]
    manifest = ProjectManifest(
        units=session.units.value,
        sources=tuple(p.name for p in source_paths),
        operations=tuple(operations),
        tolerance_linear=session.tolerance.linear,
        tolerance_angular=session.tolerance.angular,
    )

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / SOURCES_DIR).mkdir()
        for sp in source_paths:
            if sp.exists():
                shutil.copy2(sp, tmp_path / SOURCES_DIR / sp.name)
        (tmp_path / MANIFEST_NAME).write_text(
            json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
            for item in tmp_path.rglob("*"):
                if item.is_file():
                    zf.write(item, item.relative_to(tmp_path).as_posix())
    return target


def load(path: str | Path,
         *,
         replay: bool = True,
         destination: Optional[str | Path] = None) -> Session:
    """Restore a session from an ``.lgmsh`` file.

    When ``replay`` is ``True`` every operation is re-executed in
    order. When ``False``, only the first source file is loaded
    (useful for quick inspection).
    """
    src = Path(path)
    if not src.exists():
        raise FileNotFoundError(str(src))

    dest = Path(destination) if destination else Path(tempfile.mkdtemp(
        prefix="ladruno_gmsh_"
    ))
    dest.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(src, "r") as zf:
        zf.extractall(dest)

    manifest_data = json.loads((dest / MANIFEST_NAME).read_text(encoding="utf-8"))
    units = manifest_data.get("units", Units.MILLIMETER.value)
    sources = manifest_data.get("sources", [])
    operations = manifest_data.get("operations", [])
    if not sources:
        raise ValueError("Project with no source files.")

    first = dest / SOURCES_DIR / sources[0]
    session = open_model(first, units=units)

    if not replay:
        return session

    for raw in operations[1:]:  # operations[0] is the initial import
        _replay_operation(session, raw)
    return session


def _replay_operation(session: Session, raw: dict) -> None:
    """Replay a serialized operation on the session.

    Delegates to :func:`operations._helpers.op_from_node`, the same
    op_type -> class table used by ``undo``. Previously this module
    had its own duplicate table and it drifted out of sync when new
    ops were added (explode, remove_entities, unify_all...).
    """
    from ..model.history import OperationNode
    from ..operations._helpers import op_from_node

    node = OperationNode(
        op_id=raw.get("op_id", ""),
        op_type=raw.get("op_type", ""),
        inputs=tuple(raw.get("inputs", ())),
        parameters=dict(raw.get("parameters", {})),
        output_uuids=tuple(raw.get("output_uuids", ())),
    )
    op = op_from_node(node)
    if op is None:
        return  # unknown type, ignore it
    session._apply(op)
