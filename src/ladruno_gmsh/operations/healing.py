"""Heal and RemoveAllDuplicates as operations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

from ..kernel import healing as _heal
from ..model.document import GeometryDocument
from ._helpers import record
from .base import Operation


@dataclass(frozen=True)
class HealOp(Operation):
    """Run ``healShapes`` on the whole model (or the given subset).

    When ``tolerance`` is ``None`` or ``<= 0`` it is derived as
    ``max(1e-6, bbox_diagonal * 1e-5)``.
    """

    OP_TYPE: ClassVar[str] = "heal"

    tolerance: Optional[float] = None
    fix_degenerated: bool = True
    fix_small_edges: bool = True
    fix_small_faces: bool = True
    sew_faces: bool = True
    make_solids: bool = True

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        tol = self.tolerance
        if tol is None or tol <= 0:
            diag = document.bbox_diagonal()
            tol = max(1.0e-6, diag * 1.0e-5)
        _heal.heal(
            tolerance=tol,
            fix_degenerated=self.fix_degenerated,
            fix_small_edges=self.fix_small_edges,
            fix_small_faces=self.fix_small_faces,
            sew_faces=self.sew_faces,
            make_solids=self.make_solids,
        )
        return record(document, op_type=self.OP_TYPE,
                      parameters={"tolerance": tol,
                                  "fix_degenerated": self.fix_degenerated,
                                  "fix_small_edges": self.fix_small_edges,
                                  "fix_small_faces": self.fix_small_faces,
                                  "sew_faces": self.sew_faces,
                                  "make_solids": self.make_solids})


@dataclass(frozen=True)
class RemoveAllDuplicatesOp(Operation):
    OP_TYPE: ClassVar[str] = "remove_all_duplicates"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        _heal.remove_all_duplicates()
        return record(document, op_type=self.OP_TYPE, parameters={})
