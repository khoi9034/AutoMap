"""Deterministic request planning helpers for AutoMap composer requests."""

from __future__ import annotations

import re
from typing import Any


TYPO_REPLACEMENTS = {
    "zonign": "zoning",
    "aorund": "around",
    "bearny": "nearby",
    "commerical": "commercial",
    "parcles": "parcels",
    "conord": "concord",
    "kannaplis": "kannapolis",
}

PHRASE_REPLACEMENTS = {
    "flood plane": "floodplain",
    "flood plains": "floodplains",
}

COMMERCIAL_ZONING_LABELS = [
    "commercial",
    "business",
    "general commercial",
    "highway commercial",
    "neighborhood commercial",
    "retail",
    "office",
]


def normalize_request_text(prompt: str) -> dict[str, Any]:
    """Normalize safe GIS/place-name typos without changing request meaning."""
    original = str(prompt or "")
    text = original.lower()
    corrections: list[dict[str, str]] = []
    for source, target in PHRASE_REPLACEMENTS.items():
        if source in text:
            text = text.replace(source, target)
            corrections.append({"from": source, "to": target})
    for source, target in TYPO_REPLACEMENTS.items():
        pattern = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE)
        if pattern.search(text):
            text = pattern.sub(target, text)
            corrections.append({"from": source, "to": target})
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "raw_text": original,
        "normalized_text": text,
        "corrections": corrections,
        "corrected": bool(corrections),
    }


def _relationship(text: str) -> str | None:
    if re.search(r"\b(intersecting|intersect|overlap|in the|inside|within)\b", text):
        return "intersecting"
    if re.search(r"\b(around|near|nearby|close to|adjacent)\b", text):
        return "around"
    return None


def _output_mode(text: str, requested_output_type: str | None) -> str:
    if requested_output_type == "table" or re.search(r"\b(table|list|csv|spreadsheet|records)\b", text):
        return "table"
    if re.search(r"\b(report|print|pdf|export)\b", text):
        return "report"
    if re.search(r"\b(route|nearest line|driving|road route)\b", text):
        return "route"
    return "map"


def _request_type(parsed_request: dict[str, Any], output_mode: str) -> str:
    topics = set(parsed_request.get("topics") or [])
    text = str(parsed_request.get("normalized_prompt") or "")
    if output_mode == "table":
        return "table_request"
    if "nearest" in text and ("station" in text or "facility" in text or "line" in text):
        return "proximity"
    if "zoning" in topics:
        return "zoning_context"
    if {"parcel", "flood"}.issubset(topics):
        return "floodplain_screening"
    if "development" in topics:
        return "development_activity"
    if "suitab" in text or "opportunit" in text:
        return "suitability"
    if parsed_request.get("historical_year") or "historical" in (parsed_request.get("time_references") or []):
        return "historical_lookup"
    if topics:
        return "general_map"
    return "unsupported"


def build_request_plan(prompt: str, parsed_request: dict[str, Any]) -> dict[str, Any]:
    """Build a compact user-facing parameter model from the parsed request."""
    normalized = normalize_request_text(prompt)
    text = str(parsed_request.get("normalized_prompt") or normalized["normalized_text"])
    topics = list(parsed_request.get("topics") or [])
    details = parsed_request.get("topic_details") or {}
    geographies = parsed_request.get("geography_terms") or []
    geography = geographies[0].get("name") if geographies and isinstance(geographies[0], dict) else None
    zoning_modifiers = details.get("zoning_modifiers") or []
    output_mode = _output_mode(text, parsed_request.get("requested_output_type"))
    subtype: list[str] = []
    if "commercial" in zoning_modifiers or "business" in text:
        subtype.append("commercial zoning")
    if details.get("flood_frequency"):
        subtype.append(str(details["flood_frequency"]).replace("_", "-"))
    if "major roads" in text or "nearby major roads" in text:
        subtype.append("major roads")
    missing: list[str] = []
    if "zoning" in topics and not geography:
        missing.append("geography")
    confidence = 0.86
    if normalized["corrected"]:
        confidence -= 0.05
    if missing:
        confidence -= 0.2
    request_type = _request_type(parsed_request, output_mode)
    return {
        "request_type": request_type,
        "parameters": {
            "geography": geography,
            "feature_type": topics,
            "subtype_filter": subtype,
            "spatial_relationship": _relationship(text),
            "output_mode": output_mode,
            "time_period": parsed_request.get("historical_year") or (parsed_request.get("time_references") or [None])[0],
            "confidence": round(max(confidence, 0.1), 2),
            "missing_parameters": missing,
            "safety_scope": "Cabarrus County, NC only",
        },
        "normalized_prompt": text,
        "normalization": normalized,
        "zoning_category": "commercial" if "commercial zoning" in subtype else None,
        "commercial_zoning_terms": COMMERCIAL_ZONING_LABELS if "commercial zoning" in subtype else [],
        "context_layers": ["roads"] if "transportation" in topics or "roads" in text else [],
        "status": "interpreted" if request_type != "unsupported" else "unsupported",
    }
