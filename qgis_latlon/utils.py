"""Pure utility functions for GeoClick Capture."""

from __future__ import annotations

import os
import re
import uuid


def ensure_extension(path: str, extension: str) -> str:
    """Return *path* with the requested extension."""
    extension = extension if extension.startswith(".") else f".{extension}"
    return path if path.lower().endswith(extension.lower()) else f"{path}{extension}"


def to_dms(value: float, coordinate_type: str) -> str:
    """Convert a decimal latitude or longitude to DMS notation."""
    if coordinate_type not in {"lat", "lon"}:
        raise ValueError("coordinate_type must be 'lat' or 'lon'")
    absolute = abs(float(value))
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    directions = {"lat": ("N", "S"), "lon": ("E", "W")}
    direction = directions[coordinate_type][0 if value >= 0 else 1]
    return f'{degrees}°{minutes}\'{seconds:.2f}"{direction}'


def normalise_session_id(value: str) -> str:
    """Return a stable, field-friendly session identifier."""
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", (value or "").strip()).strip("-")
    return cleaned[:64] if cleaned else f"session-{uuid.uuid4().hex[:8]}"


def geocode_cache_key(latitude: float, longitude: float, precision: int = 5) -> str:
    """Create a deterministic cache key for a coordinate pair."""
    return f"{float(latitude):.{precision}f},{float(longitude):.{precision}f}"


def safe_project_name(file_name: str, fallback: str = "Untitled project") -> str:
    """Extract a readable project name from a QGIS project path."""
    if not file_name:
        return fallback
    name = os.path.basename(file_name)
    return os.path.splitext(name)[0] or fallback
