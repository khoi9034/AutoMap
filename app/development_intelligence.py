"""Deterministic development-source intelligence for AutoMap."""

from __future__ import annotations

from typing import Any


def _prompt_text(parsed_request: dict[str, Any]) -> str:
    return str(parsed_request.get("normalized_prompt") or parsed_request.get("raw_prompt") or "").lower()


def is_permit_specific_request(parsed_request: dict[str, Any]) -> bool:
    text = _prompt_text(parsed_request)
    terms = parsed_request.get("topic_details", {}).get("development_terms") or []
    return "permits" in terms or "current permit" in text or "permits" in text or "permit" in text


def is_planning_case_request(parsed_request: dict[str, Any]) -> bool:
    text = _prompt_text(parsed_request)
    terms = parsed_request.get("topic_details", {}).get("development_terms") or []
    return "planning_cases" in terms or "planning case" in text or "rezoning" in text


def is_development_pressure_request(parsed_request: dict[str, Any]) -> bool:
    text = _prompt_text(parsed_request)
    return any(
        phrase in text
        for phrase in [
            "development pressure",
            "growth pressure",
            "development activity",
            "nearby development",
            "active development",
            "development pipeline",
        ]
    )


def allows_development_proxy(parsed_request: dict[str, Any]) -> bool:
    """Return whether a proxy activity layer can be selected as context."""
    if is_permit_specific_request(parsed_request) and not is_development_pressure_request(parsed_request):
        return False
    return is_development_pressure_request(parsed_request) or "development" in (parsed_request.get("topics") or [])


def planning_case_source_matches_geography(layer: dict[str, Any], parsed_request: dict[str, Any]) -> bool:
    """Return whether a limited planning case source matches requested geography."""
    geographies = [str(geo.get("name") or "").lower() for geo in parsed_request.get("geography_terms") or [] if isinstance(geo, dict)]
    if not geographies:
        return True
    source_key = str(layer.get("source_key") or "").lower()
    text = " ".join(
        str(layer.get(field) or "").lower()
        for field in ["layer_name", "service_name", "known_limitations", "source_notes", "description"]
    )
    if "concord" in source_key or "limited to concord" in text or "concord only" in text:
        return "concord" in geographies
    return True


def selected_planning_case_supports_request(
    selected_layers: list[dict[str, Any]],
    parsed_request: dict[str, Any],
) -> bool:
    """Return whether a selected planning case layer can support this request's geography."""
    for layer in selected_layers:
        if layer.get("category") == "planning_cases" and planning_case_source_matches_geography(layer, parsed_request):
            return True
    return False


def development_context_notes(selected_layers: list[dict[str, Any]], missing_data: list[str]) -> list[str]:
    """Return plain-language development context notes for recipes and review packets."""
    notes: list[str] = []
    if any(layer.get("category") == "development_activity_proxy" for layer in selected_layers):
        notes.append("Development activity is represented by a proxy source; it is not official permit or approval data.")
    if any(layer.get("category") == "planning_cases" for layer in selected_layers):
        notes.append("Planning case layers require coverage and case-status review before official use.")
    if any(str(item).lower() in {"permits", "current_permits", "permit"} for item in missing_data):
        notes.append("Official current permit data remains unresolved.")
    return notes
