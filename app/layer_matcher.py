"""Catalog-backed layer matching for AutoMap map recipes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import sort_layer_candidates


TOPIC_CATEGORIES = {
    "parcel": {"parcel"},
    "zoning": {"zoning"},
    "flood": {"flood"},
    "schools": {"schools"},
    "transportation": {"transportation"},
    "traffic": {"transportation", "traffic"},
    "development": {"development", "planning", "permit"},
    "addresses": {"address"},
    "environmental": {"environmental"},
    "terrain": {"terrain"},
    "civic": {"civic"},
    "public_facilities": {"public_facilities"},
    "jurisdiction": {"jurisdiction", "boundary"},
}

ROLE_BY_TOPIC = {
    "parcel": "base_layer",
    "jurisdiction": "jurisdiction_filter",
    "flood": "constraint_overlay",
    "zoning": "constraint_overlay",
    "schools": "school_boundary_layer",
    "transportation": "transportation_layer",
    "traffic": "transportation_layer",
    "development": "development_activity_layer",
    "addresses": "reference_layer",
    "environmental": "environmental_layer",
    "terrain": "reference_layer",
    "civic": "reference_layer",
    "public_facilities": "reference_layer",
}

TOPIC_SEARCH_TERMS = {
    "parcel": ["parcel", "parcels", "tax parcel", "property"],
    "zoning": ["zoning"],
    "flood": ["flood", "floodplain", "floodway"],
    "schools": ["school", "district"],
    "transportation": ["road", "street", "centerline"],
    "traffic": ["traffic", "aadt"],
    "development": ["permit", "permits", "planning case", "planning cases", "development"],
    "addresses": ["address", "addresses"],
    "environmental": ["hydrology", "stream", "creek", "water"],
    "terrain": ["contour", "elevation", "terrain"],
    "civic": ["polling", "voting", "precinct"],
    "public_facilities": ["facilities", "government buildings"],
    "jurisdiction": ["municipal", "municipality", "jurisdiction", "etj", "boundary"],
}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _text_blob(record: dict[str, Any], fields: list[str]) -> str:
    parts: list[str] = []
    for field in fields:
        value = record.get(field)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts).lower()


def _contains(text: str, term: str) -> bool:
    return term.lower() in text


def _candidate_matches_topic(record: dict[str, Any], topic: str) -> bool:
    categories = TOPIC_CATEGORIES.get(topic, {topic})
    if record.get("category") in categories or record.get("canonical_topic") in categories:
        return True
    fields = ["layer_name", "service_name", "aliases"]
    if topic not in {"development", "traffic"}:
        fields.extend(["description", "planning_use_cases"])
    blob = _text_blob(record, fields)
    return any(_contains(blob, term) for term in TOPIC_SEARCH_TERMS.get(topic, [topic]))


def _score_record(record: dict[str, Any], parsed_request: dict[str, Any], topic: str) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []
    prompt_text = parsed_request["normalized_prompt"]
    topic_details = parsed_request.get("topic_details", {})
    historical_year = parsed_request.get("historical_year")
    wants_history = historical_year is not None or "historical" in parsed_request.get("time_references", [])
    layer_name = str(record.get("layer_name") or "").lower()
    service_name = str(record.get("service_name") or "").lower()
    description = str(record.get("description") or "").lower()
    use_cases = " ".join(str(item).lower() for item in _as_list(record.get("planning_use_cases")))
    aliases = [str(alias).lower() for alias in _as_list(record.get("aliases"))]

    if record.get("category") in TOPIC_CATEGORIES.get(topic, {topic}):
        score += 60
        reasons.append(f"category matches {topic}")
    if record.get("canonical_topic") in TOPIC_CATEGORIES.get(topic, {topic}):
        score += 30
        reasons.append(f"canonical topic matches {topic}")

    for alias in aliases:
        if alias and alias in prompt_text:
            score += 70
            reasons.append(f"alias match: {alias}")
            break

    for term in TOPIC_SEARCH_TERMS.get(topic, [topic]):
        if term in layer_name:
            score += 55
            reasons.append(f"layer name match: {term}")
            break
    for term in TOPIC_SEARCH_TERMS.get(topic, [topic]):
        if term in service_name:
            score += 35
            reasons.append(f"service name match: {term}")
            break
    for term in TOPIC_SEARCH_TERMS.get(topic, [topic]):
        if term in description or term in use_cases:
            score += 25
            reasons.append(f"description/use case match: {term}")
            break

    if record.get("is_verified"):
        score += 15
        reasons.append("verified REST layer")
    if int(record.get("source_priority") or 999) == 1:
        score += 15
        reasons.append("new OpenData priority")
    elif str(record.get("source_status") or "").startswith("legacy"):
        score -= 10
        reasons.append("legacy fallback penalty")

    if record.get("is_group_layer") and not record.get("is_feature_layer"):
        score -= 35
        reasons.append("group layer penalty")
    elif record.get("is_feature_layer"):
        score += 10
        reasons.append("feature layer")

    if wants_history:
        if historical_year is not None and record.get("historical_year") == historical_year:
            score += 90
            reasons.append(f"historical year match: {historical_year}")
        elif record.get("is_historical"):
            score += 25
            reasons.append("historical layer")
        else:
            score -= 30
            reasons.append("current layer penalty for historical request")
    elif record.get("is_historical"):
        score -= 200
        reasons.append("historical layer excluded from current request")

    flood_frequency = topic_details.get("flood_frequency")
    if topic == "flood" and flood_frequency:
        if flood_frequency == "100_year" and ("100" in layer_name or "100year" in layer_name):
            score += 80
            reasons.append("100-year floodplain requested")
        elif flood_frequency == "500_year" and ("500" in layer_name or "500year" in layer_name):
            score += 80
            reasons.append("500-year floodplain requested")
        else:
            score -= 35
            reasons.append("different flood recurrence")

    school_levels = topic_details.get("school_levels") or []
    if topic == "schools" and school_levels:
        if any(level in layer_name for level in school_levels):
            score += 55
            reasons.append("requested school level")

    geography_names = [geo["name"].lower() for geo in parsed_request.get("geography_terms", [])]
    for geography_name in geography_names:
        if geography_name in layer_name or geography_name in service_name:
            score += 30
            reasons.append(f"geography match: {geography_name}")
            break

    if topic == "jurisdiction":
        if any(geo["type"] in {"municipality", "municipal_boundary"} for geo in parsed_request.get("geography_terms", [])):
            if "municipal" in layer_name or "municipal" in service_name:
                score += 45
                reasons.append("municipal boundary requested")
        if any(geo["type"] == "planning_jurisdiction" for geo in parsed_request.get("geography_terms", [])):
            if "etj" in layer_name or "etj" in service_name:
                score += 55
                reasons.append("ETJ boundary requested")

    if topic == "zoning" and "commercial" in (topic_details.get("zoning_modifiers") or []):
        score += 5
        reasons.append("commercial zoning modifier requires attribute review")

    return score, reasons


def _match_topic(
    parsed_request: dict[str, Any],
    catalog_records: list[dict[str, Any]],
    topic: str,
    limit: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored: list[dict[str, Any]] = []
    for record in catalog_records:
        if not _candidate_matches_topic(record, topic):
            continue
        score, reasons = _score_record(record, parsed_request, topic)
        if score <= 0:
            continue
        scored.append({**deepcopy(record), "confidence_score": min(score / 200, 0.99), "raw_score": score, "match_reasons": reasons, "role": ROLE_BY_TOPIC.get(topic, "reference_layer"), "matched_topic": topic})

    scored = sort_layer_candidates(scored)
    scored = sorted(scored, key=lambda item: item.get("raw_score", 0), reverse=True)
    return scored[:limit], scored[limit:limit + 5]


def _select_school_layers(parsed_request: dict[str, Any], catalog_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    levels = parsed_request.get("topic_details", {}).get("school_levels") or ["elementary", "middle", "high"]
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    used_keys: set[str] = set()
    for level in levels:
        level_records = [
            record for record in catalog_records
            if _candidate_matches_topic(record, "schools") and level in str(record.get("layer_name", "")).lower()
        ]
        topic_selected, topic_rejected = _match_topic(parsed_request, level_records, "schools", 1)
        for item in topic_selected:
            if item["layer_key"] not in used_keys:
                selected.append(item)
                used_keys.add(item["layer_key"])
        rejected.extend(topic_rejected)
    return selected, rejected


def _select_zoning_layers(parsed_request: dict[str, Any], catalog_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    geography_names = {geo["name"].lower() for geo in parsed_request.get("geography_terms", [])}
    selected, rejected = _match_topic(parsed_request, catalog_records, "zoning", 1)
    if geography_names:
        geography_records = [
            record for record in catalog_records
            if _candidate_matches_topic(record, "zoning")
            and any(geo_name in str(record.get("layer_name", "")).lower() for geo_name in geography_names)
        ]
        geo_selected, geo_rejected = _match_topic(parsed_request, geography_records, "zoning", 1)
        if geo_selected:
            selected = geo_selected
            rejected.extend(geo_rejected)
        county_records = [
            record for record in catalog_records
            if _candidate_matches_topic(record, "zoning")
            and "county zoning" in str(record.get("layer_name", "")).lower()
        ]
        county_selected, county_rejected = _match_topic(parsed_request, county_records, "zoning", 1)
        selected_keys = {item["layer_key"] for item in selected}
        selected.extend(item for item in county_selected if item["layer_key"] not in selected_keys)
        rejected.extend(county_rejected)
    return selected, rejected


def _target_topics(parsed_request: dict[str, Any]) -> list[str]:
    topics = list(parsed_request.get("topics", []))
    if parsed_request.get("geography_terms") and any(
        geo["type"] not in {"county", "countywide"} for geo in parsed_request["geography_terms"]
    ):
        topics.append("jurisdiction")
    seen: set[str] = set()
    return [topic for topic in topics if not (topic in seen or seen.add(topic))]


def match_layers(parsed_request: dict[str, Any], layer_catalog: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Match parsed request topics to trusted AutoMap catalog layers."""
    catalog_records = layer_catalog if layer_catalog is not None else load_catalog_records()
    topics = _target_topics(parsed_request)
    selected_layers: list[dict[str, Any]] = []
    rejected_layers: list[dict[str, Any]] = []
    missing_data_needed: list[str] = []
    selected_keys: set[str] = set()

    for topic in topics:
        if topic == "schools":
            topic_selected, topic_rejected = _select_school_layers(parsed_request, catalog_records)
        elif topic == "zoning":
            topic_selected, topic_rejected = _select_zoning_layers(parsed_request, catalog_records)
        elif topic == "flood" and parsed_request.get("topic_details", {}).get("flood_frequency"):
            topic_selected, topic_rejected = _match_topic(parsed_request, catalog_records, topic, 1)
        else:
            limit = 3 if topic == "flood" else 1
            topic_selected, topic_rejected = _match_topic(parsed_request, catalog_records, topic, limit)

        new_items = [item for item in topic_selected if item["layer_key"] not in selected_keys]
        if not new_items:
            missing_data_needed.append(topic)
        for item in new_items:
            selected_layers.append(item)
            selected_keys.add(item["layer_key"])
        rejected_layers.extend(item for item in topic_rejected if item["layer_key"] not in selected_keys)

    development_terms = parsed_request.get("topic_details", {}).get("development_terms") or []
    if "development" in topics:
        selected_blob = _text_blob({"selected": [layer["layer_name"] for layer in selected_layers]}, ["selected"])
        for term in development_terms:
            if term == "planning_cases" and "planning" not in selected_blob:
                missing_data_needed.append("planning cases")
            if term == "permits" and "permit" not in selected_blob:
                missing_data_needed.append("permits")

    rejected_layers = sorted(
        rejected_layers,
        key=lambda item: item.get("raw_score", 0),
        reverse=True,
    )[:12]

    confidence = 0.0
    if selected_layers:
        confidence = sum(layer["confidence_score"] for layer in selected_layers) / len(selected_layers)
        confidence = max(0.0, min(confidence - 0.08 * len(set(missing_data_needed)), 0.99))

    return {
        "selected_layers": selected_layers,
        "rejected_layers": rejected_layers,
        "missing_data_needed": sorted(set(missing_data_needed)),
        "confidence_score": round(confidence, 3),
    }
