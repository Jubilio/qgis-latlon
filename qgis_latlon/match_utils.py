"""Pure-Python matching helpers for GeoClick Capture Match & Verify."""

from __future__ import annotations

import math
import re
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Sequence

_WORDS = re.compile(r"[\w]+", flags=re.UNICODE)


def normalise_name(value: object) -> str:
    """Return a lowercase, accent-insensitive, whitespace-normalised place name."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(_WORDS.findall(text.casefold()))


def token_similarity(left: object, right: object) -> float:
    """Return a stable 0..1 similarity using character and token-order scores."""
    first = normalise_name(left)
    second = normalise_name(right)
    if not first or not second:
        return 0.0
    direct = SequenceMatcher(None, first, second).ratio()
    first_tokens = " ".join(sorted(set(first.split())))
    second_tokens = " ".join(sorted(set(second.split())))
    token_score = SequenceMatcher(None, first_tokens, second_tokens).ratio()
    containment = 1.0 if first in second or second in first else 0.0
    return max(
        0.0,
        min(
            1.0,
            (direct * 0.35) + (token_score * 0.55) + (containment * 0.10),
        ),
    )


def best_name_match(query: object, values: Iterable[object]) -> Dict[str, object]:
    """Return the best candidate value and its similarity to *query*."""
    best_value = ""
    best_score = 0.0
    for value in values:
        score = token_similarity(query, value)
        if score > best_score:
            best_score = score
            best_value = str(value or "")
    return {"value": best_value, "score": best_score}


def distance_score(distance_m: float, radius_m: float) -> float:
    """Return a 0..1 score that decays linearly within the analysis radius."""
    distance = max(0.0, float(distance_m or 0.0))
    radius = max(1.0, float(radius_m or 1.0))
    return max(0.0, min(1.0, 1.0 - (distance / radius)))


def match_confidence(name_score: float, distance_m: float, radius_m: float) -> float:
    """Combine semantic and spatial evidence into an explainable 0..100 score."""
    semantic = max(0.0, min(1.0, float(name_score or 0.0)))
    spatial = distance_score(distance_m, radius_m)
    return round(((semantic * 0.65) + (spatial * 0.35)) * 100.0, 1)


def duplicate_risk(name_score: float, distance_m: float, radius_m: float) -> str:
    """Classify duplicate risk using transparent semantic/spatial thresholds."""
    semantic = max(0.0, min(1.0, float(name_score or 0.0)))
    distance = max(0.0, float(distance_m or 0.0))
    radius = max(1.0, float(radius_m or 1.0))
    if distance <= min(25.0, radius * 0.10) and semantic >= 0.80:
        return "High"
    if distance <= radius and semantic >= 0.55:
        return "Medium"
    if distance <= min(50.0, radius * 0.20) and semantic >= 0.35:
        return "Medium"
    return "Low"


def sort_candidates(candidates: Sequence[Dict[str, object]]) -> List[Dict[str, object]]:
    """Sort candidates by risk, confidence, distance and label."""
    order = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(
        (dict(item) for item in candidates),
        key=lambda item: (
            order.get(str(item.get("duplicate_risk", "Low")), 3),
            -float(item.get("confidence_score", 0.0) or 0.0),
            float(item.get("distance_m", math.inf) or math.inf),
            str(item.get("candidate_label", "")).casefold(),
        ),
    )
