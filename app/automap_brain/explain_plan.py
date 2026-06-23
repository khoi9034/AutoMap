"""Compact Brain v2 explanation helpers for the preview UI."""

from __future__ import annotations

from typing import Any


def _layer_label(layer: dict[str, Any]) -> str:
    return str(layer.get("legend_label") or layer.get("title") or layer.get("layer_name") or layer.get("layer_key") or "Layer")


def build_brain_explanation(recipe: dict[str, Any], preview_config: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = recipe.get("request_plan") or {}
    params = plan.get("parameters") or {}
    context_layers = [_layer_label(layer) for layer in (preview_config or {}).get("context_layers") or [] if isinstance(layer, dict) and layer.get("visibility", layer.get("default_visible", True)) is not False]
    selected_layers = [_layer_label(layer) for layer in recipe.get("selected_layers") or [] if isinstance(layer, dict)]
    warnings = list((preview_config or {}).get("warnings") or [])
    qa = (preview_config or {}).get("visible_map_qa") or {}
    return {
        "brain_version": plan.get("brain_version") or "automap_brain_v2",
        "interpreted_request": str(plan.get("request_type") or recipe.get("request_type") or "general_map").replace("_", " "),
        "area": params.get("geography") or plan.get("geography") or "Cabarrus County, NC",
        "primary_layer": context_layers[0] if context_layers else selected_layers[0] if selected_layers else "Not selected",
        "context_layers": context_layers[1:] if context_layers else selected_layers[1:],
        "filters_used": params.get("subtype_filter") or [item.get("value") for item in plan.get("filters") or [] if isinstance(item, dict)],
        "fallback_used": bool(qa.get("fallback_used")),
        "warnings": warnings[:6],
        "summary": "AutoMap matched the request to verified Cabarrus County layers, applied bounded QA, and styled layers by map role.",
    }
