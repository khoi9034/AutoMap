"""Human adjustment model helpers for AutoMap draft review packets."""

from __future__ import annotations

from typing import Any


ADJUSTMENT_FIELDS = {
    "map_title",
    "map_description",
    "suggested_extent_override",
    "layer_order",
    "layer_adjustments",
    "definition_expression_overrides",
    "symbology_overrides",
    "popup_overrides",
    "reviewer_notes",
    "warnings_to_resolve",
    "warnings_to_keep",
    "missing_data_notes",
    "publish_ready",
}

LAYER_ADJUSTMENT_FIELDS = {
    "visibility",
    "opacity",
    "title",
    "role",
    "showLegend",
    "remove_layer",
}

ADJUSTED_PACKET_FILES = {
    "original_recipe.json",
    "original_webmap.json",
    "adjusted_recipe.json",
    "adjusted_webmap.json",
    "applied_adjustments.json",
    "adjusted_review_summary.md",
    "adjusted_warnings.json",
    "adjusted_layer_review.json",
    "adjusted_review.html",
}


def empty_adjustments() -> dict[str, Any]:
    """Return a complete empty adjustment payload."""
    return {
        "map_title": None,
        "map_description": None,
        "suggested_extent_override": None,
        "layer_order": [],
        "layer_adjustments": {},
        "definition_expression_overrides": {},
        "symbology_overrides": {},
        "popup_overrides": {},
        "reviewer_notes": [],
        "warnings_to_resolve": [],
        "warnings_to_keep": [],
        "missing_data_notes": [],
        "publish_ready": False,
    }


def normalize_adjustments(adjustments: dict[str, Any] | None) -> dict[str, Any]:
    """Fill optional adjustment fields with predictable defaults."""
    normalized = empty_adjustments()
    for key, value in (adjustments or {}).items():
        if key in normalized:
            normalized[key] = value
    for list_key in ["layer_order", "reviewer_notes", "warnings_to_resolve", "warnings_to_keep", "missing_data_notes"]:
        value = normalized.get(list_key)
        if value is None:
            normalized[list_key] = []
        elif not isinstance(value, list):
            normalized[list_key] = [value]
    for dict_key in ["layer_adjustments", "definition_expression_overrides", "symbology_overrides", "popup_overrides"]:
        if normalized.get(dict_key) is None:
            normalized[dict_key] = {}
    normalized["publish_ready"] = bool(normalized.get("publish_ready"))
    return normalized


def validate_adjustment_shape(adjustments: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors for an adjustment payload."""
    errors: list[str] = []
    unknown_fields = sorted(set(adjustments) - ADJUSTMENT_FIELDS)
    if unknown_fields:
        errors.append(f"Unknown adjustment fields: {', '.join(unknown_fields)}")

    if adjustments.get("map_title") is not None and not isinstance(adjustments["map_title"], str):
        errors.append("map_title must be a string.")
    if adjustments.get("map_description") is not None and not isinstance(adjustments["map_description"], str):
        errors.append("map_description must be a string.")
    if adjustments.get("suggested_extent_override") is not None and not isinstance(adjustments["suggested_extent_override"], dict):
        errors.append("suggested_extent_override must be an object.")

    if not isinstance(adjustments.get("layer_order", []), list):
        errors.append("layer_order must be a list.")
    for list_key in ["reviewer_notes", "warnings_to_resolve", "warnings_to_keep", "missing_data_notes"]:
        if not isinstance(adjustments.get(list_key, []), list):
            errors.append(f"{list_key} must be a list.")

    for dict_key in ["layer_adjustments", "definition_expression_overrides", "symbology_overrides", "popup_overrides"]:
        if not isinstance(adjustments.get(dict_key, {}), dict):
            errors.append(f"{dict_key} must be an object.")

    if "publish_ready" in adjustments and not isinstance(adjustments["publish_ready"], bool):
        errors.append("publish_ready must be true or false.")

    layer_adjustments = adjustments.get("layer_adjustments") or {}
    if isinstance(layer_adjustments, dict):
        for layer_name, layer_adjustment in layer_adjustments.items():
            if not isinstance(layer_adjustment, dict):
                errors.append(f"layer_adjustments.{layer_name} must be an object.")
                continue
            unknown_layer_fields = sorted(set(layer_adjustment) - LAYER_ADJUSTMENT_FIELDS)
            if unknown_layer_fields:
                errors.append(
                    f"Unknown layer_adjustments.{layer_name} fields: {', '.join(unknown_layer_fields)}"
                )
            if "opacity" in layer_adjustment:
                try:
                    opacity = float(layer_adjustment["opacity"])
                except (TypeError, ValueError):
                    errors.append(f"layer_adjustments.{layer_name}.opacity must be numeric.")
                else:
                    if opacity < 0 or opacity > 1:
                        errors.append(f"layer_adjustments.{layer_name}.opacity must be between 0 and 1.")
            for bool_field in ["visibility", "showLegend", "remove_layer"]:
                if bool_field in layer_adjustment and not isinstance(layer_adjustment[bool_field], bool):
                    errors.append(f"layer_adjustments.{layer_name}.{bool_field} must be true or false.")
            for text_field in ["title", "role"]:
                if text_field in layer_adjustment and not isinstance(layer_adjustment[text_field], str):
                    errors.append(f"layer_adjustments.{layer_name}.{text_field} must be a string.")

    return errors
