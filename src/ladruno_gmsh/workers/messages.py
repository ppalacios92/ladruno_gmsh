"""Immutable messages exchanged with the worker."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Command:
    """Request sent to the worker."""
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(frozen=True)
class Result:
    """Response emitted by the worker after running a command."""
    request_id: str
    kind: str
    ok: bool
    data: Any = None
    error: Optional[str] = None
