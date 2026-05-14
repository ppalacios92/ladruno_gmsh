"""OperationGraph: replayable, serializable DAG of operations."""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class OperationNode:
    op_id: str
    op_type: str
    inputs: tuple[str, ...]
    parameters: Mapping[str, Any]
    output_uuids: tuple[str, ...]

    @classmethod
    def new(cls,
            op_type: str,
            *,
            inputs: tuple[str, ...] = (),
            parameters: Mapping[str, Any] | None = None,
            output_uuids: tuple[str, ...] = ()) -> "OperationNode":
        return cls(
            op_id=uuid.uuid4().hex,
            op_type=op_type,
            inputs=inputs,
            parameters=dict(parameters or {}),
            output_uuids=output_uuids,
        )


@dataclass(frozen=True)
class OperationGraph:
    nodes: tuple[OperationNode, ...] = field(default_factory=tuple)

    def append(self, node: OperationNode) -> "OperationGraph":
        return OperationGraph(nodes=self.nodes + (node,))

    def to_json(self) -> str:
        return json.dumps([
            {
                "op_id": n.op_id,
                "op_type": n.op_type,
                "inputs": list(n.inputs),
                "parameters": dict(n.parameters),
                "output_uuids": list(n.output_uuids),
            }
            for n in self.nodes
        ], ensure_ascii=False, indent=2)
