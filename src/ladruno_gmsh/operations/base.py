"""Operation: apply/undo/serialize contract and reproducibility."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields, is_dataclass
from typing import Any, ClassVar

from ..model.document import GeometryDocument


@dataclass(frozen=True)
class Operation:
    """Base for operations acting on :class:`GeometryDocument`.

    Subclasses:

    1. Must be ``@dataclass(frozen=True)``.
    2. Must set the class variable :attr:`OP_TYPE`.
    3. Implement :meth:`apply` producing the next document.

    Serialization comes for free through :func:`dataclasses.asdict`.
    """

    OP_TYPE: ClassVar[str] = "unknown"

    def apply(self, document: GeometryDocument) -> GeometryDocument:
        raise NotImplementedError

    def parameters(self) -> dict[str, Any]:
        if not is_dataclass(self):
            return {}
        return {f.name: getattr(self, f.name) for f in fields(self)}

    def to_dict(self) -> dict[str, Any]:
        return {"op_type": self.OP_TYPE, "parameters": asdict(self)}
