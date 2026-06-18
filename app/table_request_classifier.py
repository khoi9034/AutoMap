"""Classify plain-English table/data/export requests."""

from __future__ import annotations

import re
from typing import Any


TABLE_KEYWORDS = {
    "table",
    "list",
    "spreadsheet",
    "csv",
    "export",
    "data",
    "records",
    "attribute table",
    "rows",
    "fields",
    "columns",
    "download",
    "parcel list",
    "permit list",
}

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")


def classify_table_request(prompt: str) -> dict[str, Any]:
    text = prompt.lower()
    matched = sorted(keyword for keyword in TABLE_KEYWORDS if keyword in text)
    year_match = YEAR_RE.search(text)
    has_historical_hint = bool(year_match) or any(word in text for word in ("historical", "archive", "old", "past"))
    has_record_subject = any(word in text for word in ("permit", "parcel", "planning", "case", "rezoning", "zoning", "records"))
    has_table_intent = bool(matched) or (has_historical_hint and has_record_subject and "map" not in text)
    intents: list[str] = []
    if has_table_intent:
        intents.append("table_request")
    if any(word in text for word in ("export", "csv", "download", "spreadsheet")):
        intents.append("data_export")
    if "map" in text and has_table_intent:
        intents.append("map_and_table_request")
    if "parcel" in text or "pin" in text:
        intents.append("parcel_table")
    if "permit" in text:
        intents.append("permit_table")
    if "planning" in text or "case" in text or "rezoning" in text:
        intents.append("planning_case_table")
    if "zoning" in text or "zone" in text:
        intents.append("zoning_table")
    if has_historical_hint:
        intents.append("historical_table")
    if "attribute table" in text or "fields" in text or "columns" in text:
        intents.append("attribute_table")
    if not intents:
        intents.append("unsupported_table_request")
    primary = next((intent for intent in intents if intent.endswith("_table") and intent != "historical_table"), intents[0])
    return {
        "table_requested": has_table_intent,
        "intents": list(dict.fromkeys(intents)),
        "primary_intent": primary,
        "matched_keywords": matched,
        "historical_year": int(year_match.group(0)) if year_match else None,
        "map_and_table": "map_and_table_request" in intents,
    }


def is_table_request(prompt: str) -> bool:
    return bool(classify_table_request(prompt).get("table_requested"))
