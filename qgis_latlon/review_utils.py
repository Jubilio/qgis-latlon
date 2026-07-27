"""Pure-Python helpers for the GeoClick Capture review workflow."""

from __future__ import annotations

import json
import unicodedata
from typing import Dict, Iterable, List, Mapping, Tuple

REVIEW_STATUSES = ("Pending", "Needs changes", "Approved", "Rejected")


def _normalise_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(text.casefold().split())


def normalise_review_status(value: object, review_required: object = None) -> str:
    """Return one of the supported human-readable review states."""
    key = _normalise_text(value).replace("_", " ").replace("-", " ")
    aliases = {
        "pending": "Pending",
        "unreviewed": "Pending",
        "needs review": "Pending",
        "needs changes": "Needs changes",
        "changes requested": "Needs changes",
        "return": "Needs changes",
        "approved": "Approved",
        "approve": "Approved",
        "verified": "Approved",
        "rejected": "Rejected",
        "reject": "Rejected",
    }
    if key in aliases:
        return aliases[key]
    return "Pending"


def parse_review_history(value: object) -> List[Dict[str, object]]:
    """Read a compact JSON review history, tolerating old or invalid values."""
    if isinstance(value, list):
        payload = value
    else:
        text = str(value or "").strip()
        if not text:
            return []
        try:
            payload = json.loads(text)
        except (TypeError, ValueError):
            return []
    if not isinstance(payload, list):
        return []
    return [dict(item) for item in payload if isinstance(item, Mapping)]


def append_review_history(
    current: object,
    *,
    action: str,
    status: str,
    reviewer: str,
    comment: str,
    timestamp: str,
) -> Tuple[str, int]:
    """Append one immutable review event and return JSON plus iteration count."""
    history = parse_review_history(current)
    iteration = len(history) + 1
    history.append(
        {
            "iteration": iteration,
            "action": str(action or ""),
            "status": normalise_review_status(status),
            "reviewer": str(reviewer or ""),
            "comment": str(comment or ""),
            "timestamp": str(timestamp or ""),
        }
    )
    return json.dumps(history, ensure_ascii=False, separators=(",", ":")), iteration


def record_matches_review_filter(
    record: Mapping[str, object], status_filter: str = "", query: str = ""
) -> bool:
    """Return whether a queue record matches the selected state and text filter."""
    status = normalise_review_status(
        record.get("review_status"), record.get("review_required")
    )
    selected = normalise_review_status(status_filter) if status_filter else ""
    if selected and status != selected:
        return False
    needle = _normalise_text(query)
    if not needle:
        return True
    haystack = " ".join(
        _normalise_text(record.get(key, ""))
        for key in (
            "feature_id",
            "record_id",
            "display_label",
            "location",
            "result_label",
            "gazetteer_name",
            "capture_method",
            "duplicate_risk",
            "review_status",
            "reviewer",
            "review_comment",
        )
    )
    return needle in haystack


def review_status_counts(records: Iterable[Mapping[str, object]]) -> Dict[str, int]:
    """Count records by review state and include a total."""
    counts = {status: 0 for status in REVIEW_STATUSES}
    total = 0
    for record in records:
        status = normalise_review_status(
            record.get("review_status"), record.get("review_required")
        )
        counts[status] = counts.get(status, 0) + 1
        total += 1
    counts["All"] = total
    return counts
