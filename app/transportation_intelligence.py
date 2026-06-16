"""Transportation context intelligence for AutoMap."""

from __future__ import annotations

from typing import Any


def _prompt_text(parsed_request: dict[str, Any]) -> str:
    return str(parsed_request.get("normalized_prompt") or parsed_request.get("raw_prompt") or "").lower()


def is_high_traffic_request(parsed_request: dict[str, Any]) -> bool:
    text = _prompt_text(parsed_request)
    return any(phrase in text for phrase in ["high traffic", "aadt", "traffic count", "traffic counts", "road volume"])


def is_planned_transportation_project_request(parsed_request: dict[str, Any]) -> bool:
    text = _prompt_text(parsed_request)
    return any(
        phrase in text
        for phrase in [
            "planned road",
            "planned transportation",
            "road project",
            "road projects",
            "transportation project",
            "transportation projects",
            "road improvement",
            "road improvements",
            "stip",
        ]
    )


def transportation_topics_for_request(parsed_request: dict[str, Any]) -> list[str]:
    topics: list[str] = []
    if is_high_traffic_request(parsed_request):
        topics.append("traffic")
    if is_planned_transportation_project_request(parsed_request):
        topics.append("transportation_projects")
    return topics


def transportation_context_notes(selected_layers: list[dict[str, Any]]) -> list[str]:
    notes: list[str] = []
    if any(layer.get("category") == "transportation" and "aadt" in str(layer.get("layer_name") or "").lower() for layer in selected_layers):
        notes.append("AADT layers provide traffic-volume context and do not indicate development approval.")
    if any(layer.get("category") == "transportation_projects" for layer in selected_layers):
        notes.append("STIP layers provide planned transportation project context and are not development pipeline sources.")
    return notes
