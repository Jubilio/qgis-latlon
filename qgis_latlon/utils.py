"""Pure-Python helpers used by the QGIS LatLon plugin."""

from __future__ import annotations

import os
from typing import Literal


CoordinateType = Literal["lat", "lon"]


def to_dms(value: float, coord_type: CoordinateType) -> str:
    """Convert a decimal coordinate to degrees, minutes and seconds."""
    if coord_type not in {"lat", "lon"}:
        raise ValueError("coord_type must be 'lat' or 'lon'")

    is_positive = value >= 0
    absolute = abs(value)
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60, 2)

    if seconds >= 60:
        seconds = 0.0
        minutes += 1
    if minutes >= 60:
        minutes = 0
        degrees += 1

    directions = {"lat": ("N", "S"), "lon": ("E", "W")}
    suffix = directions[coord_type][0 if is_positive else 1]
    return f"{degrees}°{minutes:02d}'{seconds:05.2f}\"{suffix}"


def ensure_extension(path: str, extension: str) -> str:
    """Append an extension when the chosen path has none."""
    extension = extension if extension.startswith(".") else f".{extension}"
    return path if os.path.splitext(path)[1] else f"{path}{extension}"
