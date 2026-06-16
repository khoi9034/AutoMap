"""Lightweight guided workflow responses for the frontend."""

from __future__ import annotations

from uuid import uuid4
from typing import Any

from app.recipe_engine import build_recipe


def _selected_layers(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "layer_key": layer.get("layer_key"),
            "layer_name": layer.get("layer_name"),
            "category": layer.get("category"),
            "role": layer.get("role"),
            "source_status": layer.get("source_status"),
            "source_role": layer.get("source_role"),
            "confidence_score": layer.get("confidence_score"),
            "layer_url": layer.get("layer_url"),
        }
        for layer in recipe.get("selected_layers") or []
    ]


def _can_preview(recipe: dict[str, Any], parcel_context: dict[str, Any]) -> bool:
    if parcel_context and parcel_context.get("can_focus_map") is False:
        return False
    return bool(recipe.get("selected_layers"))


def _can_analyze(recipe: dict[str, Any], parcel_context: dict[str, Any]) -> bool:
    if parcel_context:
        return False
    analysis = recipe.get("analysis_execution") or {}
    return bool(analysis.get("executable"))


def _next_action(recipe: dict[str, Any], parcel_context: dict[str, Any], can_preview: bool, can_analyze: bool) -> str:
    if parcel_context and parcel_context.get("can_focus_map") is False:
        return "correct_parcel_identifier"
    if can_preview:
        return "create_preview"
    if can_analyze:
        return "run_analysis"
    if recipe.get("needs_review"):
        return "review_recipe"
    return "generate_report"


def run_prompt_workflow(prompt: str) -> dict[str, Any]:
    """Create a fast guided workflow plan without creating packets or running analysis."""
    recipe = build_recipe(prompt)
    parcel_context = recipe.get("parcel_context") or {}
    can_preview = _can_preview(recipe, parcel_context)
    can_analyze = _can_analyze(recipe, parcel_context)
    next_action = _next_action(recipe, parcel_context, can_preview, can_analyze)
    warnings = [
        *[str(item) for item in recipe.get("review_reasons") or [] if item],
        *[str(item) for item in parcel_context.get("parcel_warnings") or [] if item],
    ]
    return {
        "workflow_id": f"workflow_{uuid4().hex[:12]}",
        "recipe_id": f"recipe_{uuid4().hex[:12]}",
        "prompt": prompt,
        "recipe": recipe,
        "parcel_context": parcel_context,
        "selected_layers": _selected_layers(recipe),
        "warnings": sorted({warning for warning in warnings if warning}),
        "missing_data_needed": recipe.get("missing_data_needed") or [],
        "packet_id": None,
        "preview_url": None,
        "can_preview": can_preview,
        "can_analyze": can_analyze,
        "can_report": False,
        "next_recommended_action": next_action,
        "analysis_not_needed": bool(parcel_context and parcel_context.get("can_focus_map")),
        "draft_only": True,
        "published": False,
    }
