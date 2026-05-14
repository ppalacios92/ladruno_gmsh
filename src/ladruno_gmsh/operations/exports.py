"""Export to STEP, IGES, BREP, STL, MSH, VTU."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ..kernel import io as _io
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


@dataclass(frozen=True)
class ExportOp(Operation):
    """Write the current model. Does not modify entities but is recorded in the timeline."""

    OP_TYPE: ClassVar[str] = "export"

    path: str = ""

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        written = _io.write(Path(self.path))
        return record(document, op_type=self.OP_TYPE,
                      parameters={"path": str(written)},
                      rebuild_geometry=False)
