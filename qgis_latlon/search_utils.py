"""Pure-Python parsing helpers for GeoClick Capture search inputs."""

from __future__ import annotations

import math
import re
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qs, unquote, urlparse

_COORDINATE_PAIR = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*[,;\s]\s*"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))\s*$"
)
_GOOGLE_AT = re.compile(
    r"/@([+-]?(?:\d+(?:\.\d*)?|\.\d+)),"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)
_OSM_FRAGMENT = re.compile(
    r"(?:^|[#&])map=\d+(?:\.\d+)?/"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))/"
    r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))"
)


def _valid_lat_lon(lat: float, lon: float) -> bool:
    return (
        math.isfinite(lat)
        and math.isfinite(lon)
        and -90 <= lat <= 90
        and -180 <= lon <= 180
    )


def parse_coordinate_pair(text: str) -> Optional[Tuple[float, float]]:
    """Parse a decimal latitude/longitude pair and return ``(lat, lon)``."""
    match = _COORDINATE_PAIR.match(str(text or ""))
    if not match:
        return None
    lat, lon = float(match.group(1)), float(match.group(2))
    return (lat, lon) if _valid_lat_lon(lat, lon) else None


def parse_map_url(text: str) -> Optional[Tuple[float, float, str]]:
    """Extract coordinates from common OpenStreetMap and Google Maps URLs."""
    raw = str(text or "").strip()
    if not raw.lower().startswith(("http://", "https://")):
        return None

    parsed = urlparse(raw)
    host = parsed.netloc.lower().split(":", 1)[0]
    decoded_path = unquote(parsed.path)
    query = parse_qs(parsed.query)

    if "openstreetmap.org" in host:
        lat_values = query.get("mlat") or query.get("lat")
        lon_values = query.get("mlon") or query.get("lon")
        if lat_values and lon_values:
            lat, lon = float(lat_values[0]), float(lon_values[0])
            if _valid_lat_lon(lat, lon):
                return lat, lon, "openstreetmap_url"
        fragment_match = _OSM_FRAGMENT.search(parsed.fragment)
        if fragment_match:
            lat, lon = float(fragment_match.group(1)), float(fragment_match.group(2))
            if _valid_lat_lon(lat, lon):
                return lat, lon, "openstreetmap_url"

    if "google." in host or "google.com" in host or "goo.gl" in host:
        match = _GOOGLE_AT.search(decoded_path)
        if match:
            lat, lon = float(match.group(1)), float(match.group(2))
            if _valid_lat_lon(lat, lon):
                return lat, lon, "google_maps_url"
        for key in ("query", "q", "ll"):
            for value in query.get(key, []):
                coordinates = parse_coordinate_pair(value)
                if coordinates:
                    return coordinates[0], coordinates[1], "google_maps_url"

    return None


def classify_search_input(text: str) -> Dict[str, object]:
    """Classify user input as coordinates, map URL or free-text search."""
    raw = str(text or "").strip()
    if not raw:
        return {"kind": "empty", "raw": ""}

    coordinates = parse_coordinate_pair(raw)
    if coordinates:
        return {
            "kind": "coordinate",
            "raw": raw,
            "lat": coordinates[0],
            "lon": coordinates[1],
            "input_format": "decimal_coordinates",
        }

    map_url = parse_map_url(raw)
    if map_url:
        return {
            "kind": "coordinate",
            "raw": raw,
            "lat": map_url[0],
            "lon": map_url[1],
            "input_format": map_url[2],
        }

    return {"kind": "text", "raw": raw, "query": raw, "input_format": "text"}


def normalise_nominatim_results(payload: Iterable[object]) -> List[Dict[str, object]]:
    """Return a stable, minimal representation of Nominatim search results."""
    results: List[Dict[str, object]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict):
            continue
        try:
            lat = float(item.get("lat"))
            lon = float(item.get("lon"))
        except (TypeError, ValueError):
            continue
        if not _valid_lat_lon(lat, lon):
            continue

        bounding_box = []
        values = item.get("boundingbox", [])
        for value in values if isinstance(values, list) else []:
            try:
                bounding_box.append(float(value))
            except (TypeError, ValueError):
                bounding_box = []
                break
        if len(bounding_box) != 4:
            bounding_box = []

        importance = item.get("importance", 0.0)
        try:
            importance = float(importance or 0.0)
        except (TypeError, ValueError):
            importance = 0.0

        osm_type = str(item.get("osm_type", "") or "").strip()
        osm_id = str(item.get("osm_id", "") or "").strip()
        result_id = f"{osm_type}:{osm_id}".strip(":") or str(
            item.get("place_id", "") or ""
        )
        display_name = str(item.get("display_name", "") or "").strip()
        if not display_name:
            display_name = f"{lat:.6f}, {lon:.6f}"

        results.append(
            {
                "display_name": display_name,
                "lat": lat,
                "lon": lon,
                "result_type": str(
                    item.get("type", "") or item.get("class", "") or "place"
                ),
                "category": str(
                    item.get("category", "") or item.get("class", "") or ""
                ),
                "importance": importance,
                "osm_type": osm_type,
                "osm_id": osm_id,
                "provider_result_id": result_id,
                "boundingbox": bounding_box,
                "provider": "OpenStreetMap Nominatim",
                "input_format": "text",
            }
        )
    return results
