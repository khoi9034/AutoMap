"""Shared map recipe model helpers."""

from __future__ import annotations

from typing import Any


RECIPE_REQUIRED_KEYS = {
    "map_title",
    "user_intent",
    "parsed_request",
    "selected_layers",
    "rejected_layers",
    "filters",
    "spatial_operations",
    "symbology_recommendations",
    "suggested_extent",
    "confidence_score",
    "needs_review",
    "missing_data_needed",
    "filter_plan",
    "request_intelligence",
    "analysis_plan",
}

SELECTED_LAYER_KEYS = {
    "layer_key",
    "layer_name",
    "category",
    "layer_url",
    "service_url",
    "source_key",
    "source_status",
    "approval_status",
    "source_role",
    "source_priority",
    "geometry_type",
    "layer_id",
    "confidence_score",
    "match_score",
    "match_reasons",
    "intent_reasons",
    "why_selected",
    "why_not_legacy",
    "review_notes",
    "coverage_geography",
    "source_limitation",
    "gap_support",
    "coverage_warnings",
    "display_title",
    "role",
}


def selected_layer_from_match(match: dict[str, Any]) -> dict[str, Any]:
    """Return the public selected-layer shape used in map recipes."""
    return {
        "layer_key": match.get("layer_key"),
        "layer_name": match.get("layer_name"),
        "category": match.get("category"),
        "layer_url": match.get("layer_url") or match.get("rest_url"),
        "service_url": match.get("service_url"),
        "source_key": match.get("source_key"),
        "source_status": match.get("source_status"),
        "approval_status": match.get("approval_status") or "approved",
        "source_role": match.get("source_role"),
        "source_priority": match.get("source_priority"),
        "geometry_type": match.get("geometry_type"),
        "layer_id": match.get("layer_id"),
        "confidence_score": round(float(match.get("confidence_score") or 0), 3),
        "match_score": match.get("match_score", match.get("raw_score")),
        "match_reasons": match.get("match_reasons", []),
        "intent_reasons": match.get("intent_reasons", []),
        "why_selected": match.get("why_selected"),
        "why_not_legacy": match.get("why_not_legacy"),
        "review_notes": match.get("review_notes", []),
        "coverage_geography": match.get("coverage_geography"),
        "source_limitation": match.get("source_limitation") or match.get("known_limitations"),
        "gap_support": match.get("gap_support"),
        "coverage_warnings": match.get("coverage_warnings", []),
        "display_title": match.get("display_title"),
        "role": match.get("role", "reference_layer"),
    }


def rejected_layer_from_match(match: dict[str, Any]) -> dict[str, Any]:
    """Return a compact rejected-layer explanation."""
    return {
        "layer_key": match.get("layer_key"),
        "layer_name": match.get("layer_name"),
        "category": match.get("category"),
        "source_status": match.get("source_status"),
        "approval_status": match.get("approval_status") or "approved",
        "source_priority": match.get("source_priority"),
        "layer_url": match.get("layer_url") or match.get("rest_url"),
        "confidence_score": round(float(match.get("confidence_score") or 0), 3),
        "score": match.get("match_score", match.get("raw_score")),
        "reason_rejected": match.get("reason_rejected", match.get("rejection_reason", "Lower scoring match than selected catalog layer.")),
        "rejection_reason": match.get("reason_rejected", match.get("rejection_reason", "Lower scoring match than selected catalog layer.")),
        "is_legacy_or_historical": bool(match.get("is_legacy_or_historical")),
        "superseded_by_new_opendata": bool(match.get("superseded_by_new_opendata")),
    }


def recipe_has_required_keys(recipe: dict[str, Any]) -> bool:
    """Validate the top-level recipe JSON shape."""
    return RECIPE_REQUIRED_KEYS.issubset(recipe)
