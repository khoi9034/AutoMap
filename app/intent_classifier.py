"""Deterministic intent classification for AutoMap requests."""

from __future__ import annotations

import re
from typing import Any


INTENT_ORDER = [
    "property_lookup",
    "flood_exposure",
    "zoning_review",
    "school_district_lookup",
    "development_activity",
    "development_pressure",
    "growth_suitability",
    "infrastructure_access",
    "transportation_corridor",
    "environmental_constraint",
    "historical_comparison",
    "civic_boundary_lookup",
    "public_facility_lookup",
    "general_reference_map",
    "unknown_or_unsupported",
]


INTENT_SYNONYMS: dict[str, list[str]] = {
    "property_lookup": [
        "parcel",
        "parcels",
        "property",
        "properties",
        "tax parcel",
        "tax parcels",
        "land records",
        "site",
        "sites",
    ],
    "flood_exposure": [
        "flood",
        "floodplain",
        "flood plain",
        "flood hazard",
        "flood zone",
        "floodway",
        "100 year",
        "500 year",
        "fema",
        "flood risk",
    ],
    "zoning_review": [
        "zoning",
        "zone district",
        "zoning district",
        "land use regulation",
        "commercial zoning",
        "industrial zoning",
        "residential zoning",
        "allowed use",
        "allowed uses",
    ],
    "school_district_lookup": [
        "school",
        "schools",
        "school zone",
        "school zones",
        "school district",
        "school districts",
        "attendance zone",
        "elementary",
        "middle school",
        "high school",
    ],
    "development_activity": [
        "permit",
        "permits",
        "current permits",
        "planning case",
        "planning cases",
        "subdivision",
        "subdivisions",
        "under review",
        "development pipeline",
        "construction activity",
        "last 6 months",
    ],
    "development_pressure": [
        "development pressure",
        "growth pressure",
        "new construction",
        "development activity",
        "fast growing",
        "buildout",
        "permits nearby",
        "active development",
        "planning activity",
    ],
    "growth_suitability": [
        "good sites",
        "good commercial sites",
        "good for development",
        "best sites",
        "best places",
        "potential areas",
        "opportunity areas",
        "growth areas",
        "commercial growth",
        "suitable",
        "suitability",
        "avoid constraints",
        "constrained parcels",
    ],
    "infrastructure_access": [
        "utility",
        "utilities",
        "infrastructure",
        "water access",
        "sewer access",
        "service area",
        "capacity",
    ],
    "transportation_corridor": [
        "road",
        "roads",
        "street",
        "streets",
        "centerline",
        "centerlines",
        "corridor",
        "corridors",
        "traffic",
        "aadt",
        "high traffic",
        "road access",
        "highway",
        "highways",
        "major roads",
    ],
    "environmental_constraint": [
        "environmental",
        "constraint",
        "constraints",
        "constrained",
        "avoid flood",
        "avoid flood zones",
        "hydrology",
        "stream",
        "streams",
        "creek",
        "creeks",
        "water",
        "watershed",
    ],
    "historical_comparison": [
        "historical",
        "history",
        "past",
        "archive",
        "archived",
        "old parcels",
        "old zoning",
        "compare to current",
        "compared to current",
        "current vs historical",
    ],
    "civic_boundary_lookup": [
        "municipal limits",
        "city limits",
        "town limits",
        "municipal boundary",
        "boundary",
        "boundaries",
        "etj",
        "precinct",
        "precincts",
        "voting",
        "polling",
        "election",
    ],
    "public_facility_lookup": [
        "facility",
        "facilities",
        "county facilities",
        "government buildings",
        "public facilities",
    ],
    "general_reference_map": [
        "show",
        "map",
        "display",
        "reference map",
        "overview map",
    ],
}


TOPIC_INTENT_HINTS = {
    "parcel": "property_lookup",
    "flood": "flood_exposure",
    "zoning": "zoning_review",
    "schools": "school_district_lookup",
    "traffic": "transportation_corridor",
    "transportation": "transportation_corridor",
    "transportation_projects": "transportation_corridor",
    "development": "development_activity",
    "addresses": "property_lookup",
    "environmental": "environmental_constraint",
    "terrain": "general_reference_map",
    "civic": "civic_boundary_lookup",
    "public_facilities": "public_facility_lookup",
    "jurisdiction": "civic_boundary_lookup",
}


INTENT_LAYER_REQUIREMENTS: dict[str, dict[str, list[str]]] = {
    "property_lookup": {"required": ["parcel"], "optional": ["jurisdiction", "addresses"]},
    "flood_exposure": {"required": ["flood"], "optional": ["parcel", "jurisdiction"]},
    "zoning_review": {"required": ["zoning"], "optional": ["parcel", "jurisdiction"]},
    "school_district_lookup": {"required": ["schools"], "optional": ["parcel", "jurisdiction"]},
    "development_activity": {"required": ["development"], "optional": ["parcel", "jurisdiction", "transportation"]},
    "development_pressure": {
        "required": ["development"],
        "optional": ["parcel", "schools", "flood", "zoning", "transportation"],
    },
    "growth_suitability": {
        "required": ["parcel", "zoning", "transportation"],
        "optional": ["flood", "environmental", "jurisdiction", "schools"],
    },
    "infrastructure_access": {"required": ["utility"], "optional": ["parcel", "transportation", "jurisdiction"]},
    "transportation_corridor": {"required": ["transportation"], "optional": ["parcel", "zoning"]},
    "environmental_constraint": {"required": ["environmental"], "optional": ["flood", "parcel"]},
    "historical_comparison": {"required": [], "optional": ["parcel", "zoning", "flood"]},
    "civic_boundary_lookup": {"required": ["jurisdiction"], "optional": ["civic"]},
    "public_facility_lookup": {"required": ["public_facilities"], "optional": ["jurisdiction"]},
    "general_reference_map": {"required": [], "optional": []},
    "unknown_or_unsupported": {"required": [], "optional": []},
}


def normalize_text(value: str) -> str:
    """Return a lowercase searchable form for staff-style request text."""
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return re.sub(r"\s+", " ", normalized).strip()


def phrase_matches(text: str, phrase: str) -> bool:
    """Return whether a normalized phrase appears with word boundaries."""
    normalized_phrase = normalize_text(phrase)
    if not normalized_phrase:
        return False
    return re.search(rf"(?<!\w){re.escape(normalized_phrase)}(?!\w)", text) is not None


def _confidence(raw_score: float) -> float:
    if raw_score <= 0:
        return 0.0
    return round(min(0.99, 0.35 + raw_score * 0.13), 3)


def classify_intents(prompt: str, parsed_request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify one prompt into one or more deterministic map request intents."""
    text = normalize_text(prompt)
    scores: dict[str, float] = {intent: 0.0 for intent in INTENT_ORDER}
    matched_phrases: dict[str, list[str]] = {intent: [] for intent in INTENT_ORDER}

    for intent, phrases in INTENT_SYNONYMS.items():
        for phrase in phrases:
            if phrase_matches(text, phrase):
                scores[intent] += 1.0
                matched_phrases[intent].append(phrase)

    parsed_request = parsed_request or {}
    for topic in parsed_request.get("topics") or []:
        hinted_intent = TOPIC_INTENT_HINTS.get(topic)
        if hinted_intent:
            scores[hinted_intent] += 1.25
            matched_phrases[hinted_intent].append(f"parsed topic: {topic}")

    if parsed_request.get("historical_year") is not None or "historical" in (parsed_request.get("time_references") or []):
        scores["historical_comparison"] += 3.0
        matched_phrases["historical_comparison"].append("historical time reference")

    if "flood_exposure" in scores and scores["flood_exposure"] > 0 and any(
        phrase_matches(text, phrase) for phrase in ["risky", "risk", "avoid", "constraint", "constraints", "constrained"]
    ):
        scores["environmental_constraint"] += 1.0
        matched_phrases["environmental_constraint"].append("flood constraint language")

    if scores["zoning_review"] > 0 and any(
        phrase_matches(text, phrase) for phrase in ["commercial", "industrial", "residential", "growth", "opportunity"]
    ):
        scores["growth_suitability"] += 0.75
        matched_phrases["growth_suitability"].append("zoning opportunity language")

    if scores["transportation_corridor"] > 0 and any(
        phrase_matches(text, phrase) for phrase in ["high traffic", "road access", "major roads", "corridor"]
    ):
        scores["growth_suitability"] += 0.75
        matched_phrases["growth_suitability"].append("transportation opportunity language")

    if any(phrase_matches(text, phrase) for phrase in ["development pressure", "growth pressure"]):
        scores["development_pressure"] += 2.0
        matched_phrases["development_pressure"].append("explicit development pressure request")

    if any(phrase_matches(text, phrase) for phrase in ["commercial growth", "best sites", "good sites", "good commercial sites", "good for development", "suitable", "opportunity areas"]):
        scores["growth_suitability"] += 2.0
        matched_phrases["growth_suitability"].append("explicit suitability request")

    ranked = sorted(
        [intent for intent in INTENT_ORDER if intent not in {"unknown_or_unsupported"} and scores[intent] > 0],
        key=lambda intent: (-scores[intent], INTENT_ORDER.index(intent)),
    )
    if len(ranked) > 1 and "general_reference_map" in ranked:
        ranked = [intent for intent in ranked if intent != "general_reference_map"]

    if not ranked:
        ranked = ["unknown_or_unsupported"]
        scores["unknown_or_unsupported"] = 1.0
        matched_phrases["unknown_or_unsupported"].append("no supported intent detected")
    elif ranked == ["general_reference_map"] and parsed_request.get("topics"):
        ranked = [TOPIC_INTENT_HINTS.get(parsed_request["topics"][0], "general_reference_map"), "general_reference_map"]

    primary = ranked[0]
    confidence_by_intent = {intent: _confidence(scores[intent]) for intent in ranked}

    return {
        "detected_intents": ranked,
        "confidence_by_intent": confidence_by_intent,
        "primary_intent": primary,
        "secondary_intents": ranked[1:],
        "matched_phrases_by_intent": {
            intent: sorted(set(matched_phrases[intent]))
            for intent in ranked
            if matched_phrases.get(intent)
        },
    }
