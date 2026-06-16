"""Catalog-backed layer matching for AutoMap map recipes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.development_intelligence import (
    allows_development_proxy,
    is_development_pressure_request,
    is_planning_case_request,
    is_permit_specific_request,
    planning_case_source_matches_geography,
    selected_planning_case_supports_request,
)
from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import sort_layer_candidates
from app.request_explainer import (
    intent_reasons_for_layer,
    rejected_layer_reason,
    review_notes_for_layer,
    why_not_legacy,
    why_selected,
)


TOPIC_CATEGORIES = {
    "parcel": {"parcel"},
    "zoning": {"zoning"},
    "flood": {"flood"},
    "schools": {"schools"},
    "transportation": {"transportation"},
    "traffic": {"transportation", "traffic", "transportation_projects"},
    "transportation_projects": {"transportation_projects"},
    "development": {
        "development",
        "planning",
        "permit",
        "permits",
        "planning_cases",
        "development_activity_proxy",
    },
    "addresses": {"address"},
    "environmental": {"environmental"},
    "terrain": {"terrain"},
    "civic": {"civic"},
    "public_facilities": {"public_facilities"},
    "jurisdiction": {"jurisdiction", "boundary"},
    "utility": {"utility", "infrastructure"},
}

ROLE_BY_TOPIC = {
    "parcel": "base_layer",
    "jurisdiction": "jurisdiction_filter",
    "flood": "constraint_overlay",
    "zoning": "constraint_overlay",
    "schools": "school_boundary_layer",
    "transportation": "transportation_layer",
    "traffic": "transportation_layer",
    "transportation_projects": "transportation_layer",
    "development": "development_activity_layer",
    "addresses": "reference_layer",
    "environmental": "environmental_layer",
    "terrain": "reference_layer",
    "civic": "reference_layer",
    "public_facilities": "reference_layer",
    "utility": "reference_layer",
}

TOPIC_SEARCH_TERMS = {
    "parcel": ["parcel", "parcels", "tax parcel", "property"],
    "zoning": ["zoning"],
    "flood": ["flood", "floodplain", "floodway"],
    "schools": ["school", "district"],
    "transportation": ["road", "street", "centerline"],
    "traffic": ["traffic", "aadt"],
    "transportation_projects": ["stip", "planned road", "road project", "transportation project", "road improvement"],
    "development": ["permit", "permits", "planning case", "planning cases", "development", "plan review", "subdivision"],
    "addresses": ["address", "addresses"],
    "environmental": ["hydrology", "stream", "creek", "water"],
    "terrain": ["contour", "elevation", "terrain"],
    "civic": ["polling", "voting", "precinct"],
    "public_facilities": ["facilities", "government buildings"],
    "jurisdiction": ["municipal", "municipality", "jurisdiction", "etj", "boundary"],
    "utility": ["utility", "utilities", "infrastructure", "water", "sewer", "capacity"],
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


def _split_intelligence(intelligence: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    if not intelligence:
        return {}, {}
    if "request_intelligence" in intelligence or "analysis_plan" in intelligence:
        return intelligence.get("request_intelligence") or {}, intelligence.get("analysis_plan") or {}
    return intelligence, intelligence.get("analysis_plan") or {}


def _candidate_matches_topic(record: dict[str, Any], topic: str) -> bool:
    approval_status = record.get("approval_status") or "approved"
    if approval_status == "needs_review":
        return False
    if approval_status == "candidate" and not record.get("is_verified"):
        return False
    categories = TOPIC_CATEGORIES.get(topic, {topic})
    if record.get("category") in categories or record.get("canonical_topic") in categories:
        return True
    fields = ["layer_name", "service_name", "aliases"]
    if topic not in {"development", "traffic"}:
        fields.extend(["description", "planning_use_cases"])
    blob = _text_blob(record, fields)
    return any(_contains(blob, term) for term in TOPIC_SEARCH_TERMS.get(topic, [topic]))


def _topic_satisfied_by_selected(topic: str, selected_layers: list[dict[str, Any]]) -> bool:
    categories = TOPIC_CATEGORIES.get(topic, {topic})
    return any(
        layer.get("matched_topic") == topic
        or layer.get("category") in categories
        or layer.get("canonical_topic") in categories
        for layer in selected_layers
    )


def _score_record(
    record: dict[str, Any],
    parsed_request: dict[str, Any],
    topic: str,
    request_intelligence: dict[str, Any] | None = None,
) -> tuple[float, list[str]]:
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
    intelligence, analysis_plan = _split_intelligence(request_intelligence)
    required_layers = set(analysis_plan.get("required_layers") or [])
    optional_layers = set(analysis_plan.get("optional_layers") or [])

    if record.get("category") in TOPIC_CATEGORIES.get(topic, {topic}):
        score += 60
        reasons.append(f"category matches {topic}")
    if record.get("canonical_topic") in TOPIC_CATEGORIES.get(topic, {topic}):
        score += 30
        reasons.append(f"canonical topic matches {topic}")

    if topic in required_layers or record.get("category") in required_layers:
        score += 25
        reasons.append(f"required by request intent: {topic}")
    elif topic in optional_layers or record.get("category") in optional_layers:
        score += 10
        reasons.append(f"supports request intent: {topic}")

    if intelligence.get("detected_intents"):
        category = record.get("category")
        constraints = intelligence.get("extracted_constraints") or []
        opportunities = intelligence.get("extracted_opportunities") or []
        if category in {"flood", "environmental", "zoning"} and constraints:
            score += 8
            reasons.append("matches detected constraint context")
        if category in {"parcel", "zoning", "transportation"} and opportunities:
            score += 8
            reasons.append("matches detected opportunity context")

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
    approval_status = record.get("approval_status") or "approved"
    source_status = str(record.get("source_status") or "")
    if approval_status == "approved":
        score += 5
        reasons.append("approved source")
    elif approval_status == "candidate" and record.get("is_verified"):
        score -= 5
        reasons.append("verified candidate source; review-labeled use only")
    else:
        score -= 200
        reasons.append("candidate source requires review")
    if source_status == "proxy":
        score -= 20
        reasons.append("proxy/context source")
    elif source_status == "reference":
        score -= 10
        reasons.append("reference/context source")
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

    if topic == "development" and record.get("category") == "development_activity_proxy":
        if not allows_development_proxy(parsed_request):
            score -= 180
            reasons.append("proxy plan-review source is not an official current permit layer")
        elif is_permit_specific_request(parsed_request):
            score -= 90
            reasons.append("permit-specific request still needs official permit source")
        elif is_development_pressure_request(parsed_request):
            score += 80
            reasons.append("development pressure can use verified proxy activity as context")

    if record.get("category") == "planning_cases" and not planning_case_source_matches_geography(record, parsed_request):
        score -= 220
        reasons.append("limited planning case source does not match requested geography")
    if topic == "development" and record.get("category") == "planning_cases" and not is_planning_case_request(parsed_request):
        if is_permit_specific_request(parsed_request):
            score -= 260
            reasons.append("planning case source is not an official current permit layer")
        else:
            score -= 60
            reasons.append("planning case source is secondary unless cases are requested")

    return score, reasons


def _match_topic(
    parsed_request: dict[str, Any],
    catalog_records: list[dict[str, Any]],
    topic: str,
    limit: int = 1,
    request_intelligence: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scored: list[dict[str, Any]] = []
    intelligence, analysis_plan = _split_intelligence(request_intelligence)
    for record in catalog_records:
        if not _candidate_matches_topic(record, topic):
            continue
        score, reasons = _score_record(record, parsed_request, topic, request_intelligence)
        if score <= 0:
            continue
        candidate = {**deepcopy(record), "confidence_score": min(score / 200, 0.99), "raw_score": score, "match_score": round(score, 1), "match_reasons": reasons, "role": ROLE_BY_TOPIC.get(topic, "reference_layer"), "matched_topic": topic}
        candidate["intent_reasons"] = intent_reasons_for_layer(candidate, topic, intelligence, analysis_plan)
        candidate["why_selected"] = why_selected(candidate, topic, intelligence)
        candidate["why_not_legacy"] = why_not_legacy(candidate, intelligence)
        candidate["review_notes"] = review_notes_for_layer(candidate, topic)
        if candidate.get("source_status") == "proxy":
            candidate["review_notes"] = [
                *candidate.get("review_notes", []),
                "Proxy/context layer only; do not treat as official permit, planning approval, development approval, or capacity.",
            ]
            candidate["role"] = "reference_layer"
        scored.append(candidate)

    scored = sort_layer_candidates(scored)
    scored = sorted(scored, key=lambda item: item.get("raw_score", 0), reverse=True)
    return scored[:limit], scored[limit:limit + 5]


def _select_school_layers(
    parsed_request: dict[str, Any],
    catalog_records: list[dict[str, Any]],
    request_intelligence: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    levels = parsed_request.get("topic_details", {}).get("school_levels") or ["elementary", "middle", "high"]
    selected: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    used_keys: set[str] = set()
    for level in levels:
        level_records = [
            record for record in catalog_records
            if _candidate_matches_topic(record, "schools") and level in str(record.get("layer_name", "")).lower()
        ]
        topic_selected, topic_rejected = _match_topic(parsed_request, level_records, "schools", 1, request_intelligence)
        for item in topic_selected:
            if item["layer_key"] not in used_keys:
                selected.append(item)
                used_keys.add(item["layer_key"])
        rejected.extend(topic_rejected)
    return selected, rejected


def _select_zoning_layers(
    parsed_request: dict[str, Any],
    catalog_records: list[dict[str, Any]],
    request_intelligence: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    geography_names = {geo["name"].lower() for geo in parsed_request.get("geography_terms", [])}
    selected, rejected = _match_topic(parsed_request, catalog_records, "zoning", 1, request_intelligence)
    if geography_names:
        geography_records = [
            record for record in catalog_records
            if _candidate_matches_topic(record, "zoning")
            and any(geo_name in str(record.get("layer_name", "")).lower() for geo_name in geography_names)
        ]
        geo_selected, geo_rejected = _match_topic(parsed_request, geography_records, "zoning", 1, request_intelligence)
        if geo_selected:
            selected = geo_selected
            rejected.extend(geo_rejected)
        county_records = [
            record for record in catalog_records
            if _candidate_matches_topic(record, "zoning")
            and "county zoning" in str(record.get("layer_name", "")).lower()
        ]
        county_selected, county_rejected = _match_topic(parsed_request, county_records, "zoning", 1, request_intelligence)
        selected_keys = {item["layer_key"] for item in selected}
        selected.extend(item for item in county_selected if item["layer_key"] not in selected_keys)
        rejected.extend(county_rejected)
    return selected, rejected


def _target_topics(parsed_request: dict[str, Any], request_intelligence: dict[str, Any] | None = None) -> list[str]:
    topics = list(parsed_request.get("topics", []))
    _, analysis_plan = _split_intelligence(request_intelligence)
    for topic in analysis_plan.get("required_layers") or []:
        topics.append(topic)
    if parsed_request.get("geography_terms") and any(
        geo["type"] not in {"county", "countywide"} for geo in parsed_request["geography_terms"]
    ):
        topics.append("jurisdiction")
    try:
        from app.transportation_intelligence import transportation_topics_for_request

        topics.extend(transportation_topics_for_request(parsed_request))
    except Exception:
        pass
    detected_intents = set((request_intelligence or {}).get("request_intelligence", {}).get("detected_intents", []))
    detected_intents.update((request_intelligence or {}).get("detected_intents", []))
    prompt_text = str(parsed_request.get("normalized_prompt") or "")
    if "growth_suitability" in detected_intents and ("opportunit" in prompt_text or "suitab" in prompt_text or "avoid" in prompt_text):
        topics.append("flood")
    seen: set[str] = set()
    return [topic for topic in topics if not (topic in seen or seen.add(topic))]


def match_layers(
    parsed_request: dict[str, Any],
    layer_catalog: list[dict[str, Any]] | None = None,
    request_intelligence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Match parsed request topics to trusted AutoMap catalog layers."""
    catalog_records = layer_catalog if layer_catalog is not None else load_catalog_records()
    topics = _target_topics(parsed_request, request_intelligence)
    selected_layers: list[dict[str, Any]] = []
    rejected_layers: list[dict[str, Any]] = []
    missing_data_needed: list[str] = []
    selected_keys: set[str] = set()

    for topic in topics:
        if topic == "schools":
            topic_selected, topic_rejected = _select_school_layers(parsed_request, catalog_records, request_intelligence)
        elif topic == "zoning":
            topic_selected, topic_rejected = _select_zoning_layers(parsed_request, catalog_records, request_intelligence)
        elif topic == "flood" and parsed_request.get("topic_details", {}).get("flood_frequency"):
            topic_selected, topic_rejected = _match_topic(parsed_request, catalog_records, topic, 1, request_intelligence)
        else:
            limit = 3 if topic == "flood" else 1
            topic_selected, topic_rejected = _match_topic(parsed_request, catalog_records, topic, limit, request_intelligence)

        new_items = [item for item in topic_selected if item["layer_key"] not in selected_keys]
        if not new_items and not _topic_satisfied_by_selected(topic, selected_layers):
            if not (topic == "development" and parsed_request.get("topic_details", {}).get("development_terms")):
                missing_data_needed.append(topic)
        for item in new_items:
            selected_layers.append(item)
            selected_keys.add(item["layer_key"])
        rejected_layers.extend(item for item in topic_rejected if item["layer_key"] not in selected_keys)

    development_terms = parsed_request.get("topic_details", {}).get("development_terms") or []
    if "development" in topics:
        official_parts: list[str] = []
        for layer in selected_layers:
            if layer.get("source_status") in {"proxy", "reference"}:
                continue
            if (layer.get("approval_status") or "approved") != "approved":
                continue
            official_parts.append(
                _text_blob(
                    layer,
                    [
                        "layer_name",
                        "service_name",
                        "category",
                        "aliases",
                        "description",
                        "planning_use_cases",
                        "canonical_topic",
                    ],
                )
            )
        official_blob = " ".join(official_parts)
        for term in development_terms:
            if (
                term == "planning_cases"
                and "planning" not in official_blob
                and not selected_planning_case_supports_request(selected_layers, parsed_request)
            ):
                missing_data_needed.append("planning cases")
            if term == "permits" and "permit" not in official_blob:
                missing_data_needed.append("permits")
            if term in {"subdivision_activity", "development_pipeline"} and "subdivision" not in official_blob and "development" not in official_blob:
                missing_data_needed.append("subdivision activity" if term == "subdivision_activity" else "development")
            if term == "construction_activity" and "construction" not in official_blob and "permit" not in official_blob:
                missing_data_needed.append("permits")

    rejected_layers = sorted(
        rejected_layers,
        key=lambda item: item.get("raw_score", 0),
        reverse=True,
    )[:12]
    for item in rejected_layers:
        item.update(rejected_layer_reason(item, selected_layers))

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
