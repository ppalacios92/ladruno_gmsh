"""File imports as a versioned operation."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ..kernel import io as _io
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


@dataclass(frozen=True)
class ImportOp(Operation):
    """Read a geometry or mesh file into the active model."""

    OP_TYPE: ClassVar[str] = "import"

    path: str = ""
    highest_dim_only: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _io.import_shapes(Path(self.path),
                          highest_dim_only=self.highest_dim_only)
        return record(
            document,
            op_type=self.OP_TYPE,
            parameters={
                "path": self.path,
                "highest_dim_only": self.highest_dim_only,
            },
        )


@dataclass(frozen=True)
class MergeOp(Operation):
    """Import a second file on top of the existing model."""

    OP_TYPE: ClassVar[str] = "merge"

    path: str = ""
    highest_dim_only: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _io.import_shapes(Path(self.path),
                          highest_dim_only=self.highest_dim_only)
        return record(
            document,
            op_type=self.OP_TYPE,
            parameters={
                "path": self.path,
                "highest_dim_only": self.highest_dim_only,
            },
        )
