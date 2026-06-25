"""Parameter extraction for AutoMap Brain Kernel v1."""

from __future__ import annotations

from typing import Any

from app.automap_brain.intent_classifier import classify_intent
from app.prompt_parser import parse_prompt


def _target_features(plan: dict[str, Any]) -> list[str]:
    request_type = str(plan.get("request_type") or "")
    primary = str(plan.get("primary_domain") or "")
    if request_type == "proximity":
        return ["nearest facility", "route"]
    if request_type == "floodplain_screening":
        return ["affected parcels"]
    if request_type == "zoning_context":
        return ["zoning"]
    if request_type == "table_request":
        return ["parcel records"]
    return [primary] if primary else []


def _context_features(plan: dict[str, Any]) -> list[str]:
    contexts: list[str] = []
    domains = plan.get("secondary_domains") or []
    if "floodplain" in domains or plan.get("request_type") == "floodplain_screening":
        contexts.append("100-year floodplain")
    if "transportation" in domains:
        contexts.append("roads")
    if plan.get("geography"):
        contexts.append("boundary")
    return contexts


def extract_parameters(
    prompt: str,
    parsed_request: dict[str, Any] | None = None,
    request_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract reusable map/table parameters from a user prompt."""
    parsed = parsed_request or parse_prompt(prompt)
    plan = request_plan or classify_intent(prompt, parsed)["request_plan"]
    params = plan.get("parameters") if isinstance(plan.get("parameters"), dict) else {}
    filters = plan.get("filters") or []
    return {
        "original_prompt": prompt,
        "normalized_prompt": plan.get("normalized_prompt"),
        "geography": plan.get("geography"),
        "geography_type": plan.get("geography_type"),
        "target_features": _target_features(plan),
        "context_features": _context_features(plan),
        "spatial_relationship": (plan.get("spatial_relationships") or ["context_only"])[0],
        "time_period": plan.get("requested_time_period"),
        "filters": filters,
        "requested_fields": params.get("requested_fields") or parsed.get("requested_fields") or [],
        "floodplain_type": plan.get("floodplain_type") or params.get("floodplain_type"),
        "zoning_category": plan.get("zoning_category") or params.get("subtype_filter"),
        "missing_parameters": plan.get("missing_parameters") or [],
        "confidence": plan.get("confidence", 0),
    }
