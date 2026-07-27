"""Pure-Python helpers for loading and searching offline gazetteers."""

from __future__ import annotations

import csv
import os
import re
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from .match_utils import normalise_name, token_similarity

_FIELD_ALIASES = {
    "record_id": ("place_id", "location_id", "site_id", "id", "uuid", "code"),
    "official_name": (
        "official_name", "name", "place_name", "site_name", "facility_name",
        "location", "label", "settlement", "village", "locality",
    ),
    "alternative_names": (
        "alternative_names", "alternate_names", "alt_names", "aliases", "alias",
        "other_names", "name_alt", "name_variants",
    ),
    "place_type": ("place_type", "type", "category", "feature_type", "site_type"),
    "pcode": ("pcode", "p_code", "pcodes", "admin_code", "geocode", "location_code"),
    "latitude": ("latitude", "lat", "y", "gps_latitude"),
    "longitude": ("longitude", "lon", "lng", "long", "x", "gps_longitude"),
    "country": ("country", "country_name", "adm0_name", "admin0"),
    "province": ("province", "state", "region", "adm1_name", "admin1"),
    "district": ("district", "county", "adm2_name", "admin2"),
    "admin_post": ("admin_post", "administrative_post", "adm3_name", "admin3"),
    "locality": ("locality", "bairro", "neighbourhood", "neighborhood", "adm4_name", "admin4"),
    "source": ("source", "data_source", "provider"),
    "source_date": ("source_date", "date", "updated_at", "reference_date"),
}
_SPLIT_ALIASES = re.compile(r"\s*[;|]\s*")


def detect_columns(fieldnames: Iterable[object]) -> Dict[str, str]:
    """Map canonical gazetteer fields to detected source column names."""
    names = [str(name or "").strip() for name in fieldnames]
    by_normalised = {normalise_name(name).replace(" ", "_"): name for name in names if name}
    mapping: Dict[str, str] = {}
    for canonical, aliases in _FIELD_ALIASES.items():
        for alias in aliases:
            key = normalise_name(alias).replace(" ", "_")
            if key in by_normalised:
                mapping[canonical] = by_normalised[key]
                break
    return mapping


def parse_aliases(value: object) -> List[str]:
    """Split semicolon/pipe-delimited alternative names and remove duplicates."""
    text = str(value or "").strip()
    if not text:
        return []
    values = [item.strip() for item in _SPLIT_ALIASES.split(text) if item.strip()]
    seen = set()
    output = []
    for value in values:
        key = normalise_name(value)
        if key and key not in seen:
            seen.add(key)
            output.append(value)
    return output


def _value(row: Mapping[str, object], mapping: Mapping[str, str], field: str) -> str:
    column = mapping.get(field, "")
    return str(row.get(column, "") or "").strip() if column else ""


def _coordinate(value: object, minimum: float, maximum: float) -> Optional[float]:
    try:
        number = float(str(value or "").strip().replace(",", "."))
    except (TypeError, ValueError):
        return None
    return number if minimum <= number <= maximum else None


def normalise_record(
    row: Mapping[str, object],
    mapping: Mapping[str, str],
    source_name: str,
    row_number: int,
    coordinates: Optional[Tuple[float, float]] = None,
) -> Optional[Dict[str, object]]:
    """Convert a CSV/layer record to the plugin's stable gazetteer schema."""
    name = _value(row, mapping, "official_name")
    pcode = _value(row, mapping, "pcode")
    if not name and not pcode:
        return None

    if coordinates is None:
        lat = _coordinate(_value(row, mapping, "latitude"), -90.0, 90.0)
        lon = _coordinate(_value(row, mapping, "longitude"), -180.0, 180.0)
    else:
        lat, lon = coordinates
        lat = _coordinate(lat, -90.0, 90.0)
        lon = _coordinate(lon, -180.0, 180.0)
    if lat is None or lon is None:
        return None

    aliases = parse_aliases(_value(row, mapping, "alternative_names"))
    record_id = _value(row, mapping, "record_id") or pcode or f"row-{row_number}"
    admin_parts = [
        _value(row, mapping, field)
        for field in ("country", "province", "district", "admin_post", "locality")
    ]
    admin_label = ", ".join(part for part in admin_parts if part)
    return {
        "record_id": record_id,
        "official_name": name or pcode,
        "alternative_names": aliases,
        "place_type": _value(row, mapping, "place_type") or "place",
        "pcode": pcode,
        "lat": float(lat),
        "lon": float(lon),
        "country": _value(row, mapping, "country"),
        "province": _value(row, mapping, "province"),
        "district": _value(row, mapping, "district"),
        "admin_post": _value(row, mapping, "admin_post"),
        "locality": _value(row, mapping, "locality"),
        "admin_label": admin_label,
        "source": _value(row, mapping, "source") or source_name,
        "source_date": _value(row, mapping, "source_date"),
        "source_name": source_name,
    }


def load_csv_gazetteer(path: str) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Load a UTF-8/UTF-8-BOM CSV gazetteer with automatic field detection."""
    records: List[Dict[str, object]] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        mapping = detect_columns(reader.fieldnames or [])
        missing = [field for field in ("official_name", "latitude", "longitude") if field not in mapping]
        if missing:
            raise ValueError("Missing required gazetteer columns: " + ", ".join(missing))
        source_name = os.path.basename(path)
        for row_number, row in enumerate(reader, start=2):
            record = normalise_record(row, mapping, source_name, row_number)
            if record is not None:
                records.append(record)
    metadata = gazetteer_metadata(records, os.path.basename(path), mapping)
    metadata["path"] = os.path.abspath(path)
    metadata["format"] = "CSV"
    return records, metadata


def gazetteer_metadata(
    records: Sequence[Mapping[str, object]],
    source_name: str,
    mapping: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Summarise a loaded gazetteer for the user interface."""
    types = sorted({str(item.get("place_type", "") or "place") for item in records})
    return {
        "source_name": source_name,
        "record_count": len(records),
        "types": types,
        "mapping": dict(mapping or {}),
    }


def _record_score(query: str, record: Mapping[str, object]) -> float:
    normalised_query = normalise_name(query)
    if not normalised_query:
        return 0.5
    pcode = normalise_name(record.get("pcode", ""))
    if pcode and normalised_query == pcode:
        return 1.0
    names = [record.get("official_name", "")] + list(record.get("alternative_names", []) or [])
    scores = [token_similarity(query, value) for value in names if str(value or "").strip()]
    best = max(scores, default=0.0)
    official = normalise_name(record.get("official_name", ""))
    if official.startswith(normalised_query):
        best = max(best, 0.92)
    elif normalised_query in official:
        best = max(best, 0.82)
    if pcode and normalised_query in pcode:
        best = max(best, 0.88)
    return min(1.0, best)


def search_gazetteer(
    records: Sequence[Mapping[str, object]],
    query: str,
    place_type: str = "",
    limit: int = 100,
    minimum_score: float = 0.25,
) -> List[Dict[str, object]]:
    """Search official names, aliases and P-codes in a loaded gazetteer."""
    requested_type = normalise_name(place_type)
    results: List[Dict[str, object]] = []
    for item in records:
        if requested_type and normalise_name(item.get("place_type", "")) != requested_type:
            continue
        score = _record_score(query, item)
        if query.strip() and score < minimum_score:
            continue
        result = dict(item)
        result["search_score"] = round(score, 4)
        results.append(result)
    results.sort(
        key=lambda item: (
            -float(item.get("search_score", 0.0) or 0.0),
            str(item.get("official_name", "")).casefold(),
            str(item.get("pcode", "")).casefold(),
        )
    )
    return results[: max(1, int(limit))]
