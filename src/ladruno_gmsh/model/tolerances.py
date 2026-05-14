"""Linear and angular tolerances with an auto policy derived from the bbox."""
from __future__ import annotations

from dataclasses import dataclass
from math import pi


@dataclass(frozen=True)
class Tolerance:
    """Explicit geometric tolerance.

    ``linear`` is interpreted in the document's units. ``angular`` is
    in radians.
    """

    linear: float
    angular: float = 1.0e-4

    @classmethod
    def auto(cls, bbox_diagonal: float) -> "Tolerance":
        linear = max(1.0e-6, bbox_diagonal * 1.0e-5)
        return cls(linear=linear)

    @classmethod
    def resolve(cls,
                value: "Tolerance | str | float",
                bbox_diagonal: float) -> "Tolerance":
        if isinstance(value, Tolerance):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v == "auto":
                return cls.auto(bbox_diagonal)
            raise ValueError(f"Unknown tolerance: {value!r}")
        if isinstance(value, (int, float)):
            return cls(linear=float(value))
        raise TypeError(f"Invalid tolerance type: {type(value).__name__}")

    @property
    def angular_degrees(self) -> float:
        return self.angular * 180.0 / pi
