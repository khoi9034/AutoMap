"""Structured request planning for AutoMap Brain v2."""

from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from app.automap_brain.domain_ontology import (
    COMMERCIAL_ZONING_TERMS,
    DOMAIN_ONTOLOGY,
    MAJOR_ROAD_TERMS,
    OUT_OF_SCOPE_PLACES,
    PLACE_ALIASES,
    SUPPORTED_SCOPE,
)
from app.automap_brain.normalizer import normalize_prompt


def _elapsed_ms(start: float) -> int:
    return int(round((perf_counter() - start) * 1000))


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text) for term in terms)


def _geography(text: str, parsed_request: dict[str, Any]) -> tuple[str | None, str | None, float, bool]:
    for place in OUT_OF_SCOPE_PLACES:
        if re.search(rf"(?<!\w){re.escape(place)}(?!\w)", text):
            return place.title(), "unsupported_area", 0.2, True
    for geo in parsed_request.get("geography_terms") or []:
        if isinstance(geo, dict) and geo.get("name"):
            return str(geo["name"]), str(geo.get("type") or "place"), 0.95, False
    for alias, meta in PLACE_ALIASES.items():
        if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text):
            return str(meta["name"]), str(meta["type"]), float(meta["confidence"]), False
    return ("Cabarrus County", "county", 0.92, False) if "cabarrus" in text else (None, None, 0.0, False)


def _output_mode(text: str, requested_output_type: str | None) -> str:
    if requested_output_type == "table" or _contains_any(text, DOMAIN_ONTOLOGY["table_requests"]["synonyms"]):
        return "table"
    if re.search(r"\b(report|print|pdf|export package)\b", text):
        return "report"
    if re.search(r"\b(nearest|route|nearest line|driving|road route)\b", text):
        return "route"
    return "map"


def _spatial_relationships(text: str) -> list[str]:
    relationships: list[str] = []
    if re.search(r"\b(intersecting|intersect|overlap|inside|within|in the)\b", text):
        relationships.append("intersecting")
    if re.search(r"\b(around|near|nearby|close to|adjacent)\b", text):
        relationships.append("near_or_around")
    if re.search(r"\boutside\b|\bnot in\b|\bavoid\b", text):
        relationships.append("excluding")
    return relationships


def _domains(text: str, parsed_topics: list[str]) -> tuple[str | None, list[str]]:
    domain_map = {
        "addresses": "address_proximity",
        "parcel": "parcels",
        "zoning": "zoning",
        "flood": "floodplain",
        "transportation": "transportation",
        "traffic": "transportation",
        "development": "development_activity",
    }
    domains: list[str] = []
    for topic in parsed_topics:
        mapped = domain_map.get(topic)
        if mapped and mapped not in domains:
            domains.append(mapped)
    for domain, meta in DOMAIN_ONTOLOGY.items():
        if domain not in domains and _contains_any(text, meta["synonyms"]):
            domains.append(domain)
    if re.search(r"\b(20[01][0-9]|historical|archive|old|past)\b", text) and "historical_layers" not in domains:
        domains.append("historical_layers")
    if re.search(r"\b(table|list|spreadsheet|csv|records|attribute table)\b", text) and "table_requests" not in domains:
        domains.append("table_requests")
    if not domains:
        return None, []
    return domains[0], domains[1:]


def _request_type(text: str, output_mode: str, primary_domain: str | None, secondary_domains: list[str], parsed_request: dict[str, Any]) -> str:
    domains = {primary_domain, *secondary_domains}
    if output_mode == "table" or "table_requests" in domains:
        return "table_request"
    if re.search(r"\bnearest\b", text) and re.search(r"\b(fire|station|facility|line)\b", text):
        return "proximity"
    if "zoning" in domains:
        return "zoning_context"
    if {"parcels", "floodplain"}.issubset(domains):
        return "floodplain_screening"
    if "development_activity" in domains:
        return "development_activity"
    if "suitability" in domains:
        return "suitability"
    if parsed_request.get("historical_year") or "historical_layers" in domains:
        return "historical_lookup"
    return "general_map" if primary_domain else "unsupported"


def _filters(text: str, parsed_request: dict[str, Any]) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    details = parsed_request.get("topic_details") or {}
    if "commercial" in details.get("zoning_modifiers", []) or _contains_any(text, COMMERCIAL_ZONING_TERMS):
        filters.append({"domain": "zoning", "field_role": "zoning_code_or_description", "operator": "matches_any", "value": "commercial zoning", "confidence": 0.78})
    if details.get("flood_frequency"):
        filters.append({"domain": "floodplain", "field_role": "flood_type", "operator": "matches", "value": details["flood_frequency"], "confidence": 0.82})
    if parsed_request.get("historical_year"):
        filters.append({"domain": "historical_layers", "field_role": "historical_year", "operator": "equals", "value": parsed_request["historical_year"], "confidence": 0.9})
    if _contains_any(text, MAJOR_ROAD_TERMS):
        filters.append({"domain": "transportation", "field_role": "road_class_or_traffic", "operator": "major_or_context", "value": "major roads", "confidence": 0.74})
    return filters


def _required_layers(request_type: str, primary_domain: str | None, secondary_domains: list[str]) -> list[str]:
    if request_type == "proximity":
        return ["address", "public_facilities", "transportation"]
    if request_type == "zoning_context":
        required = ["zoning", "jurisdiction"]
        if "transportation" in secondary_domains:
            required.insert(1, "transportation")
        return required
    if request_type == "floodplain_screening":
        return ["parcel", "flood", "jurisdiction"]
    if request_type == "table_request":
        return ["parcel"]
    if request_type == "development_activity":
        return ["development", "jurisdiction"]
    if request_type == "historical_lookup":
        return ["parcel", "zoning"]
    if request_type == "suitability":
        return ["parcel", "zoning", "flood", "transportation"]
    return [primary_domain] if primary_domain else []


def _optional_context_layers(primary_domain: str | None, secondary_domains: list[str]) -> list[str]:
    lookup = {"transportation": "roads", "floodplain": "floodplain", "zoning": "zoning", "parcels": "parcels", "development_activity": "development activity"}
    return [lookup[domain] for domain in secondary_domains if domain in lookup and domain != primary_domain]


def _confidence(normalization: dict[str, Any], request_type: str, geography_confidence: float, filters: list[dict[str, Any]]) -> float:
    value = 0.72 + (0.12 if request_type != "unsupported" else 0) + (geography_confidence * 0.08 if geography_confidence else 0) + (0.04 if filters else 0)
    if normalization.get("corrected"):
        value -= 0.03
    return round(max(0.12, min(value, 0.96)), 2)


def build_brain_plan(prompt: str, parsed_request: dict[str, Any] | None = None) -> dict[str, Any]:
    started = perf_counter()
    normalization = normalize_prompt(prompt)
    if parsed_request is None:
        from app.prompt_parser import parse_prompt

        parsed_request = parse_prompt(prompt)
    text = str(parsed_request.get("normalized_prompt") or normalization["normalized_text"])
    geography_name, geography_type, geography_confidence, unsupported_area = _geography(text, parsed_request)
    output_mode = _output_mode(text, parsed_request.get("requested_output_type"))
    primary_domain, secondary_domains = _domains(text, list(parsed_request.get("topics") or []))
    if primary_domain == "table_requests" and "parcel" in parsed_request.get("topics", []):
        primary_domain = "parcels"
        if "table_requests" not in secondary_domains:
            secondary_domains.insert(0, "table_requests")
    if output_mode == "table" and "table_requests" not in secondary_domains and primary_domain != "table_requests":
        secondary_domains.append("table_requests")
    request_type = "unsupported" if unsupported_area or "owner name" in text else _request_type(text, output_mode, primary_domain, secondary_domains, parsed_request)
    if request_type == "proximity":
        primary_domain = primary_domain or "address_proximity"
        if "transportation" not in secondary_domains:
            secondary_domains.append("transportation")
    filters = _filters(text, parsed_request)
    missing = []
    if request_type == "zoning_context" and not geography_name:
        missing.append("geography")
    if request_type == "proximity" and not re.search(r"\d+\s+\w+", text):
        missing.append("origin address or parcel")
    spatial_relationships = _spatial_relationships(text)
    fallback_strategy = {
        "zoning_context": ["Broaden uncertain commercial zoning filters to muted zoning context.", "Show road context if major-road classification is unavailable."],
        "proximity": ["Use straight-line fallback only when bounded road-network routing fails."],
        "table_request": ["Preview rows first and block unsafe exports over limits."],
        "unsupported": [f"Return unsupported_area because live workflows are scoped to {SUPPORTED_SCOPE}."],
    }.get(request_type, [])
    confidence = _confidence(normalization, request_type, geography_confidence, filters)
    return {
        "brain_version": "automap_brain_v2",
        "normalized_prompt": text,
        "normalization": normalization,
        "request_type": request_type,
        "confidence": confidence,
        "geography": geography_name,
        "geography_type": geography_type,
        "geography_confidence": round(geography_confidence, 2),
        "output_mode": output_mode,
        "primary_domain": primary_domain,
        "secondary_domains": secondary_domains,
        "spatial_relationships": spatial_relationships,
        "filters": filters,
        "requested_time_period": parsed_request.get("historical_year") or (parsed_request.get("time_references") or [None])[0],
        "required_layers": _required_layers(request_type, primary_domain, secondary_domains),
        "optional_context_layers": _optional_context_layers(primary_domain, secondary_domains),
        "missing_parameters": missing,
        "fallback_strategy": fallback_strategy,
        "safety_notes": [f"Live address, parcel, and proximity workflows support {SUPPORTED_SCOPE} only.", "Owner/name fields are not searched by default.", "Real ArcGIS publishing is disabled."],
        "parameters": {
            "geography": geography_name,
            "feature_type": list(parsed_request.get("topics") or []),
            "subtype_filter": [item["value"] for item in filters if item.get("value") in {"commercial zoning", "major roads"}],
            "spatial_relationship": spatial_relationships[0] if spatial_relationships else None,
            "output_mode": output_mode,
            "time_period": parsed_request.get("historical_year") or (parsed_request.get("time_references") or [None])[0],
            "confidence": confidence,
            "missing_parameters": missing,
            "safety_scope": f"{SUPPORTED_SCOPE} only",
        },
        "zoning_category": "commercial" if any(item.get("value") == "commercial zoning" for item in filters) else None,
        "commercial_zoning_terms": COMMERCIAL_ZONING_TERMS if any(item.get("value") == "commercial zoning" for item in filters) else [],
        "context_layers": ["roads"] if "transportation" in parsed_request.get("topics", []) or any(item.get("value") == "major roads" for item in filters) else [],
        "status": "unsupported_area" if unsupported_area else "unsupported" if request_type == "unsupported" else "interpreted",
        "timing": {"normalize_ms": 0, "parse_ms": 0, "total_ms": _elapsed_ms(started)},
    }


def build_request_plan(prompt: str, parsed_request: dict[str, Any]) -> dict[str, Any]:
    return build_brain_plan(prompt, parsed_request)
