"""Units, conversion and detection from a source file."""
from __future__ import annotations

from enum import Enum


class Units(str, Enum):
    MILLIMETER = "mm"
    CENTIMETER = "cm"
    METER = "m"
    INCH = "in"
    FOOT = "ft"

    @classmethod
    def parse(cls, value: "str | Units") -> "Units":
        if isinstance(value, Units):
            return value
        v = str(value).strip().lower()
        for u in cls:
            if u.value == v:
                return u
        raise ValueError(f"Unknown unit: {value!r}")

    def to_meters(self, magnitude: float) -> float:
        return magnitude * _TO_METERS[self]

    def from_meters(self, magnitude: float) -> float:
        return magnitude / _TO_METERS[self]


_TO_METERS: dict[Units, float] = {
    Units.MILLIMETER: 1.0e-3,
    Units.CENTIMETER: 1.0e-2,
    Units.METER: 1.0,
    Units.INCH: 0.0254,
    Units.FOOT: 0.3048,
}
