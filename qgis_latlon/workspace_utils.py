"""Pure-Python helpers for the GeoClick Location Verification Workspace."""

from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import os
import re
import statistics
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

WORKSPACE_STATUSES = ("Draft", "In review", "Verified", "Rejected")

_SOURCE_TRUST = {
    "institutional": 98.0,
    "gazetteer": 95.0,
    "qgis_layer": 90.0,
    "existing_qgis": 90.0,
    "survey": 88.0,
    "gps": 88.0,
    "manual": 75.0,
    "nominatim": 72.0,
    "openstreetmap": 72.0,
    "coordinate": 70.0,
    "map_url": 65.0,
    "unknown": 55.0,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def normalise_text(value: object) -> str:
    text = str(value or "").casefold().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def safe_float(value: object) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def valid_lat_lon(lat: object, lon: object) -> bool:
    latitude = safe_float(lat)
    longitude = safe_float(lon)
    return bool(
        latitude is not None
        and longitude is not None
        and -90.0 <= latitude <= 90.0
        and -180.0 <= longitude <= 180.0
    )


def candidate_id() -> str:
    return uuid.uuid4().hex[:12]


def workspace_id() -> str:
    return f"LVW-{datetime.now(timezone.utc):%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"


def source_kind(source: object, input_format: object = "") -> str:
    text = f"{source} {input_format}".casefold()
    if any(token in text for token in ("institution", "official", "authority")):
        return "institutional"
    if "gazetteer" in text or "p-code" in text or "pcode" in text:
        return "gazetteer"
    if "existing qgis" in text or "existing_feature" in text:
        return "existing_qgis"
    if "qgis" in text or "geopackage" in text or "postgis" in text:
        return "qgis_layer"
    if "gps" in text:
        return "gps"
    if "survey" in text or "field" in text:
        return "survey"
    if "nominatim" in text:
        return "nominatim"
    if "openstreetmap" in text or " osm" in f" {text}":
        return "openstreetmap"
    if "google_maps_url" in text or "openstreetmap_url" in text or "map_url" in text:
        return "map_url"
    if "decimal_coordinates" in text or "coordinate" in text:
        return "coordinate"
    if "manual" in text:
        return "manual"
    return "unknown"


def source_trust_score(kind: object) -> float:
    return float(_SOURCE_TRUST.get(str(kind or "unknown"), _SOURCE_TRUST["unknown"]))


def normalise_candidate(
    raw: Mapping[str, object],
    *,
    default_source: str = "Unknown source",
    default_kind: str = "",
) -> Dict[str, object]:
    """Return one JSON-safe candidate with validated coordinates."""
    lat = safe_float(raw.get("lat", raw.get("latitude")))
    lon = safe_float(raw.get("lon", raw.get("longitude")))
    if lat is None or lon is None or not valid_lat_lon(lat, lon):
        raise ValueError("Candidate latitude/longitude are invalid")

    label = str(
        raw.get("label")
        or raw.get("display_name")
        or raw.get("official_name")
        or raw.get("candidate_label")
        or "Unnamed location"
    ).strip()
    source = str(raw.get("source") or raw.get("provider") or default_source).strip()
    kind = str(raw.get("source_kind") or default_kind or source_kind(source, raw.get("input_format"))).strip()
    source_id = str(
        raw.get("source_id")
        or raw.get("provider_result_id")
        or raw.get("record_id")
        or raw.get("feature_id")
        or ""
    ).strip()

    candidate = {
        "candidate_id": str(raw.get("candidate_id") or candidate_id()),
        "label": label,
        "source": source,
        "source_kind": kind or "unknown",
        "source_id": source_id,
        "source_url": str(raw.get("source_url") or raw.get("url") or "").strip(),
        "source_date": str(raw.get("source_date") or "").strip(),
        "lat": round(float(lat), 10),
        "lon": round(float(lon), 10),
        "geometry_type": str(raw.get("geometry_type") or "Point").strip() or "Point",
        "geometry_wkt": str(raw.get("geometry_wkt") or "").strip(),
        "admin": str(raw.get("admin") or raw.get("admin_label") or "").strip(),
        "notes": str(raw.get("notes") or raw.get("note") or "").strip(),
        "input_format": str(raw.get("input_format") or "").strip(),
        "trust_score": round(
            float(raw.get("trust_score") or source_trust_score(kind or "unknown")), 2
        ),
    }
    extra = raw.get("attributes")
    candidate["attributes"] = dict(extra) if isinstance(extra, Mapping) else {}
    return candidate


def haversine_distance_m(
    lat1: object, lon1: object, lat2: object, lon2: object
) -> float:
    values = [safe_float(value) for value in (lat1, lon1, lat2, lon2)]
    if any(value is None for value in values):
        raise ValueError("Distance coordinates are invalid")
    latitude1, longitude1, latitude2, longitude2 = [float(value) for value in values]
    radius = 6_371_008.8
    phi1 = math.radians(latitude1)
    phi2 = math.radians(latitude2)
    delta_phi = math.radians(latitude2 - latitude1)
    delta_lambda = math.radians(longitude2 - longitude1)
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    return radius * 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))


def _agreement_from_distance(distance_m: float) -> float:
    # 100 at the same point; smoothly decreases to 0 at 5 km.
    return max(0.0, 100.0 * (1.0 - min(max(distance_m, 0.0), 5000.0) / 5000.0))


def compare_candidates(
    candidates: Sequence[Mapping[str, object]], preferred_id: str = ""
) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    """Score candidates and return a transparent workspace comparison summary."""
    items = [normalise_candidate(item) for item in candidates]
    preferred = next(
        (item for item in items if item["candidate_id"] == preferred_id), None
    )
    pair_distances: List[float] = []
    all_distances: Dict[str, List[float]] = {str(item["candidate_id"]): [] for item in items}

    for index, first in enumerate(items):
        for second in items[index + 1 :]:
            distance = haversine_distance_m(
                first["lat"], first["lon"], second["lat"], second["lon"]
            )
            pair_distances.append(distance)
            all_distances[str(first["candidate_id"])].append(distance)
            all_distances[str(second["candidate_id"])].append(distance)

    scored: List[Dict[str, object]] = []
    for item in items:
        distances = all_distances[str(item["candidate_id"])]
        median_distance = statistics.median(distances) if distances else 0.0
        agreement = 100.0 if len(items) <= 1 else _agreement_from_distance(median_distance)
        trust = float(item.get("trust_score", source_trust_score(item.get("source_kind"))))
        recommendation = 0.55 * trust + 0.45 * agreement
        distance_to_preferred = (
            haversine_distance_m(
                item["lat"], item["lon"], preferred["lat"], preferred["lon"]
            )
            if preferred is not None
            else None
        )
        enriched = dict(item)
        enriched.update(
            {
                "median_distance_m": round(median_distance, 2),
                "agreement_score": round(agreement, 2),
                "recommendation_score": round(recommendation, 2),
                "distance_to_preferred_m": (
                    round(distance_to_preferred, 2)
                    if distance_to_preferred is not None
                    else None
                ),
                "is_preferred": bool(item["candidate_id"] == preferred_id),
            }
        )
        scored.append(enriched)

    scored.sort(
        key=lambda item: (
            not bool(item.get("is_preferred")),
            -float(item.get("recommendation_score", 0.0)),
            str(item.get("label", "")).casefold(),
        )
    )

    spread = max(pair_distances) if pair_distances else 0.0
    if len(items) <= 1:
        consensus = "Single source"
    elif spread <= 50.0:
        consensus = "Strong"
    elif spread <= 250.0:
        consensus = "Moderate"
    elif spread <= 1000.0:
        consensus = "Weak"
    else:
        consensus = "Divergent"

    recommended = max(
        scored,
        key=lambda item: float(item.get("recommendation_score", 0.0)),
        default=None,
    )
    summary = {
        "candidate_count": len(items),
        "source_count": len({str(item.get("source", "")) for item in items}),
        "source_spread_m": round(spread, 2),
        "mean_pair_distance_m": round(statistics.mean(pair_distances), 2)
        if pair_distances
        else 0.0,
        "consensus_level": consensus,
        "recommended_candidate_id": str(recommended.get("candidate_id", ""))
        if recommended
        else "",
        "recommended_label": str(recommended.get("label", "")) if recommended else "",
        "preferred_candidate_id": preferred_id,
        "preferred_agreement_score": round(
            float(preferred.get("agreement_score", 0.0)), 2
        )
        if preferred and "agreement_score" in preferred
        else next(
            (
                float(item.get("agreement_score", 0.0))
                for item in scored
                if item.get("candidate_id") == preferred_id
            ),
            0.0,
        ),
        "geometry_types": sorted(
            {str(item.get("geometry_type", "Point")) for item in items}
        ),
    }
    return scored, summary


def candidates_are_duplicate(first: Mapping[str, object], second: Mapping[str, object]) -> bool:
    first_source_id = (
        normalise_text(first.get("source")),
        normalise_text(first.get("source_id")),
    )
    second_source_id = (
        normalise_text(second.get("source")),
        normalise_text(second.get("source_id")),
    )
    if first_source_id[1] and first_source_id == second_source_id:
        return True
    try:
        distance = haversine_distance_m(
            first.get("lat"), first.get("lon"), second.get("lat"), second.get("lon")
        )
    except ValueError:
        return False
    return distance <= 0.5 and normalise_text(first.get("label")) == normalise_text(
        second.get("label")
    )


def upsert_candidate(
    candidates: Sequence[Mapping[str, object]], candidate: Mapping[str, object]
) -> Tuple[List[Dict[str, object]], str]:
    normalised = normalise_candidate(candidate)
    output = [normalise_candidate(item) for item in candidates]
    for index, existing in enumerate(output):
        if candidates_are_duplicate(existing, normalised):
            normalised["candidate_id"] = existing["candidate_id"]
            output[index] = normalised
            return output, "updated"
    output.append(normalised)
    return output, "added"


def file_sha256(path: str, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def evidence_record(
    kind: str,
    value: str,
    *,
    label: str = "",
    note: str = "",
    added_by: str = "",
    timestamp: str = "",
) -> Dict[str, object]:
    evidence_kind = str(kind or "reference").strip().casefold()
    value = str(value or "").strip()
    if not value:
        raise ValueError("Evidence value is empty")
    record: Dict[str, object] = {
        "evidence_id": uuid.uuid4().hex[:12],
        "kind": evidence_kind,
        "label": str(label or Path(value).name or evidence_kind.title()),
        "value": value,
        "note": str(note or "").strip(),
        "added_by": str(added_by or "").strip(),
        "added_at": timestamp or utc_now(),
        "sha256": "",
        "size_bytes": 0,
        "exists": True,
    }
    if evidence_kind == "file":
        path = os.path.abspath(os.path.expanduser(value))
        record["value"] = path
        record["exists"] = os.path.isfile(path)
        if record["exists"]:
            record["size_bytes"] = os.path.getsize(path)
            record["sha256"] = file_sha256(path)
    return record


def parse_workspace_payload(value: object) -> Dict[str, object]:
    if isinstance(value, Mapping):
        payload = dict(value)
    else:
        text = str(value or "").strip()
        if not text:
            return {}
        payload = json.loads(text)
        if not isinstance(payload, Mapping):
            raise ValueError("Workspace payload must be a JSON object")
        payload = dict(payload)
    payload.setdefault("schema_version", "2.0")
    payload.setdefault("metadata", {})
    payload.setdefault("candidates", [])
    payload.setdefault("evidence", [])
    if not isinstance(payload["metadata"], Mapping):
        payload["metadata"] = {}
    if not isinstance(payload["candidates"], list):
        payload["candidates"] = []
    if not isinstance(payload["evidence"], list):
        payload["evidence"] = []
    payload["metadata"] = dict(payload["metadata"])
    payload["candidates"] = [
        normalise_candidate(item)
        for item in payload["candidates"]
        if isinstance(item, Mapping)
    ]
    payload["evidence"] = [
        dict(item) for item in payload["evidence"] if isinstance(item, Mapping)
    ]
    return payload


def new_workspace_payload() -> Dict[str, object]:
    timestamp = utc_now()
    return {
        "schema_version": "2.0",
        "metadata": {
            "workspace_id": workspace_id(),
            "place_name": "",
            "status": "Draft",
            "verifier": "",
            "rationale": "",
            "preferred_candidate_id": "",
            "created_at": timestamp,
            "updated_at": timestamp,
        },
        "candidates": [],
        "evidence": [],
        "summary": {},
    }


def update_workspace_payload(payload: Mapping[str, object]) -> Dict[str, object]:
    workspace = parse_workspace_payload(payload)
    metadata = workspace["metadata"]
    metadata.setdefault("workspace_id", workspace_id())
    metadata.setdefault("created_at", utc_now())
    metadata["updated_at"] = utc_now()
    status = str(metadata.get("status", "Draft"))
    metadata["status"] = status if status in WORKSPACE_STATUSES else "Draft"
    preferred_id = str(metadata.get("preferred_candidate_id", ""))
    candidates, summary = compare_candidates(workspace["candidates"], preferred_id)
    workspace["candidates"] = candidates
    workspace["summary"] = summary
    workspace["metadata"] = metadata
    return workspace


def _csv_value(row: Mapping[str, object], names: Iterable[str]) -> str:
    normalised = {normalise_text(key).replace(" ", "_"): value for key, value in row.items()}
    for name in names:
        value = normalised.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def load_candidate_csv(path: str) -> Tuple[List[Dict[str, object]], Dict[str, object]]:
    records: List[Dict[str, object]] = []
    invalid_rows: List[int] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames:
            raise ValueError("Candidate CSV has no header row")
        for row_number, row in enumerate(reader, start=2):
            raw = {
                "label": _csv_value(row, ("label", "name", "official_name", "place_name")),
                "lat": _csv_value(row, ("lat", "latitude", "y")),
                "lon": _csv_value(row, ("lon", "longitude", "long", "x")),
                "source": _csv_value(row, ("source", "provider", "dataset")) or Path(path).stem,
                "source_id": _csv_value(row, ("source_id", "record_id", "id", "pcode")),
                "source_url": _csv_value(row, ("source_url", "url", "link")),
                "source_date": _csv_value(row, ("source_date", "date", "updated_at")),
                "geometry_type": _csv_value(row, ("geometry_type", "geom_type")) or "Point",
                "admin": _csv_value(row, ("admin", "administration", "district", "province")),
                "notes": _csv_value(row, ("notes", "note", "comment")),
                "source_kind": _csv_value(row, ("source_kind", "kind")),
            }
            try:
                records.append(normalise_candidate(raw))
            except ValueError:
                invalid_rows.append(row_number)
    return records, {
        "path": os.path.abspath(path),
        "record_count": len(records),
        "invalid_rows": invalid_rows,
    }


def _safe_filename(value: object, fallback: str = "file") -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._")
    return text or fallback


def render_workspace_html(payload: Mapping[str, object]) -> str:
    workspace = update_workspace_payload(payload)
    metadata = workspace["metadata"]
    summary = workspace["summary"]
    candidates = workspace["candidates"]
    evidence = workspace["evidence"]

    def h(value: object) -> str:
        return html.escape(str(value or ""))

    candidate_rows = "".join(
        "<tr>"
        f"<td>{'✓' if item.get('is_preferred') else ''}</td>"
        f"<td>{h(item.get('label'))}</td>"
        f"<td>{h(item.get('source'))}</td>"
        f"<td>{h(item.get('source_id'))}</td>"
        f"<td>{float(item.get('lat', 0.0)):.7f}</td>"
        f"<td>{float(item.get('lon', 0.0)):.7f}</td>"
        f"<td>{float(item.get('agreement_score', 0.0)):.0f}</td>"
        f"<td>{float(item.get('recommendation_score', 0.0)):.0f}</td>"
        f"<td>{h(item.get('geometry_type'))}</td>"
        "</tr>"
        for item in candidates
    ) or '<tr><td colspan="9">No candidates</td></tr>'

    evidence_rows = "".join(
        "<tr>"
        f"<td>{h(item.get('kind'))}</td>"
        f"<td>{h(item.get('label'))}</td>"
        f"<td>{h(item.get('value'))}</td>"
        f"<td><code>{h(item.get('sha256'))}</code></td>"
        f"<td>{h(item.get('note'))}</td>"
        "</tr>"
        for item in evidence
    ) or '<tr><td colspan="5">No evidence</td></tr>'

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>Location Verification — {h(metadata.get('place_name') or metadata.get('workspace_id'))}</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;color:#1f2933}}h1,h2{{color:#176b6b}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}}
.card{{border:1px solid #d5dde3;border-radius:8px;padding:12px;background:#f8fafb}}
table{{width:100%;border-collapse:collapse;margin:12px 0 28px}}th,td{{border:1px solid #d5dde3;padding:7px;text-align:left;font-size:13px}}th{{background:#e8f3f2}}
code{{font-size:11px;word-break:break-all}}.muted{{color:#5f6b73}}.status{{font-weight:bold;color:#b45309}}
</style></head><body>
<h1>Location Verification Workspace</h1>
<p class="muted">Generated by GeoClick Capture 2.0.0</p>
<div class="grid">
<div class="card"><b>Workspace</b><br>{h(metadata.get('workspace_id'))}</div>
<div class="card"><b>Place</b><br>{h(metadata.get('place_name'))}</div>
<div class="card"><b>Status</b><br><span class="status">{h(metadata.get('status'))}</span></div>
<div class="card"><b>Verifier</b><br>{h(metadata.get('verifier'))}</div>
<div class="card"><b>Sources</b><br>{h(summary.get('source_count'))}</div>
<div class="card"><b>Maximum spread</b><br>{float(summary.get('source_spread_m', 0.0)):.1f} m — {h(summary.get('consensus_level'))}</div>
</div>
<h2>Verification rationale</h2><p>{h(metadata.get('rationale')) or '—'}</p>
<h2>Source candidates</h2>
<table><thead><tr><th>Preferred</th><th>Label</th><th>Source</th><th>Source ID</th><th>Latitude</th><th>Longitude</th><th>Agreement</th><th>Recommendation</th><th>Geometry</th></tr></thead><tbody>{candidate_rows}</tbody></table>
<h2>Evidence</h2>
<table><thead><tr><th>Type</th><th>Label</th><th>Reference</th><th>SHA-256</th><th>Note</th></tr></thead><tbody>{evidence_rows}</tbody></table>
<p class="muted">Created {h(metadata.get('created_at'))}; updated {h(metadata.get('updated_at'))}.</p>
</body></html>"""


def export_workspace_bundle(path: str, payload: Mapping[str, object]) -> Dict[str, object]:
    workspace = update_workspace_payload(payload)
    output_path = str(path)
    if not output_path.lower().endswith(".zip"):
        output_path += ".zip"
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)

    candidates = workspace["candidates"]
    evidence = workspace["evidence"]
    copied_files: List[str] = []
    missing_files: List[str] = []

    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "workspace.json",
            json.dumps(workspace, ensure_ascii=False, indent=2),
        )
        archive.writestr("report.html", render_workspace_html(workspace))

        candidate_columns = (
            "candidate_id", "is_preferred", "label", "source", "source_kind",
            "source_id", "source_url", "source_date", "lat", "lon",
            "geometry_type", "admin", "agreement_score", "recommendation_score",
            "distance_to_preferred_m", "notes",
        )
        candidate_lines: List[str] = []
        from io import StringIO
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=candidate_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(candidates)
        archive.writestr("candidates.csv", "\ufeff" + stream.getvalue())

        evidence_columns = (
            "evidence_id", "kind", "label", "value", "note", "added_by",
            "added_at", "sha256", "size_bytes", "exists",
        )
        stream = StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=evidence_columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(evidence)
        archive.writestr("evidence.csv", "\ufeff" + stream.getvalue())

        used_names = set()
        for item in evidence:
            if item.get("kind") != "file":
                continue
            source_path = str(item.get("value", ""))
            if not os.path.isfile(source_path):
                missing_files.append(source_path)
                continue
            base_name = _safe_filename(os.path.basename(source_path), "evidence")
            candidate_name = base_name
            counter = 2
            while candidate_name in used_names:
                stem, extension = os.path.splitext(base_name)
                candidate_name = f"{stem}_{counter}{extension}"
                counter += 1
            used_names.add(candidate_name)
            archive.write(source_path, f"attachments/{candidate_name}")
            copied_files.append(candidate_name)

        manifest = {
            "workspace_id": workspace["metadata"].get("workspace_id", ""),
            "generated_at": utc_now(),
            "candidate_count": len(candidates),
            "evidence_count": len(evidence),
            "copied_attachments": copied_files,
            "missing_attachments": missing_files,
        }
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))

    return {
        "path": os.path.abspath(output_path),
        "candidate_count": len(candidates),
        "evidence_count": len(evidence),
        "copied_attachments": copied_files,
        "missing_attachments": missing_files,
    }


def import_workspace_file(path: str) -> Dict[str, object]:
    if str(path).lower().endswith(".zip"):
        with zipfile.ZipFile(path, "r") as archive:
            try:
                text = archive.read("workspace.json").decode("utf-8")
            except KeyError as exc:
                raise ValueError("Bundle does not contain workspace.json") from exc
    else:
        with open(path, "r", encoding="utf-8-sig") as stream:
            text = stream.read()
    workspace = parse_workspace_payload(text)
    return update_workspace_payload(workspace)
