"""Deterministic planning scenario classification."""

from __future__ import annotations

from typing import Any

from app.intent_classifier import normalize_text, phrase_matches
from app.prompt_parser import parse_prompt


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase_matches(text, phrase) for phrase in phrases)


def classify_scenario(prompt: str, parsed_request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify a prompt into a reviewable planning scenario type."""
    parsed_request = parsed_request or parse_prompt(prompt)
    text = normalize_text(prompt)
    topics = set(parsed_request.get("topics") or [])
    reasons: list[str] = []
    scenario_type = "unsupported_scenario"
    confidence = 0.35

    growth_terms = ["growth", "suitable", "suitability", "opportunity", "opportunities", "best sites", "good sites"]
    if _has_any(text, ["commercial", "business"]) and _has_any(text, growth_terms):
        scenario_type = "commercial_growth_suitability"
        confidence = 0.86
        reasons.extend(["commercial modifier", "growth or suitability language"])
    elif _has_any(text, ["residential", "housing", "homes", "subdivision"]) and _has_any(text, growth_terms):
        scenario_type = "residential_growth_suitability"
        confidence = 0.84
        reasons.extend(["residential modifier", "growth or suitability language"])
    elif _has_any(text, ["development pressure", "growth pressure", "development activity", "nearby development"]):
        scenario_type = "development_pressure"
        confidence = 0.82
        reasons.append("development pressure language")
    elif _has_any(text, ["avoid flood", "avoid floodplain", "avoid flood risk", "not in flood", "outside flood"]):
        scenario_type = "flood_avoidance"
        confidence = 0.78
        reasons.append("flood avoidance language")
    elif "flood" in topics and _has_any(text, ["constraint", "constrained", "risk", "exposure", "issues"]):
        scenario_type = "constraint_exposure"
        confidence = 0.76
        reasons.append("constraint exposure language")
    elif _has_any(text, ["high traffic", "aadt", "traffic corridor", "road access", "transportation access"]):
        scenario_type = "transportation_access"
        confidence = 0.74
        reasons.append("transportation access language")
    elif _has_any(text, ["planning cases", "rezoning", "land use cases"]):
        scenario_type = "planning_case_context"
        confidence = 0.72
        reasons.append("planning case language")
    elif "schools" in topics and _has_any(text, ["impact", "concern", "capacity", "growth"]):
        scenario_type = "school_impact_context"
        confidence = 0.7
        reasons.append("school impact context")
    elif parsed_request.get("historical_year") or _has_any(text, ["historical", "compare current", "old zoning", "past"]):
        scenario_type = "historical_change_context"
        confidence = 0.72
        reasons.append("historical comparison language")

    if scenario_type == "unsupported_scenario" and _has_any(text, growth_terms):
        scenario_type = "commercial_growth_suitability" if "zoning" in topics else "development_pressure"
        confidence = 0.58
        reasons.append("generic growth language")

    return {
        "scenario_type": scenario_type,
        "confidence_score": confidence,
        "classification_reasons": reasons or ["No scenario-specific pattern matched."],
    }
