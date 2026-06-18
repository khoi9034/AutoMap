"""Build report/statistics summaries from saved composer map state."""

from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return [value]
    return [value]


def _source_bucket(layer: dict[str, Any]) -> str:
    role = str(layer.get("source_role") or layer.get("source_status") or layer.get("role") or "").lower()
    if layer.get("local_output") or layer.get("is_derived") or "derived" in role:
        return "derived_local"
    if "proxy" in role:
        return "proxy"
    if "reference" in role:
        return "reference"
    if role in {"active", "approved", "verified", "official"}:
        return "official"
    return "reference"


def build_report_statistics(map_state: dict[str, Any] | None) -> dict[str, Any]:
    """Return honest available statistics and unavailable placeholders."""
    state = map_state or {}
    visible_layers = _as_list(state.get("visible_layers"))
    hidden_layers = _as_list(state.get("hidden_layers"))
    derived_overlays = _as_list(state.get("derived_overlays"))
    warnings = _as_list(state.get("warnings"))
    missing_data = _as_list(state.get("missing_data"))
    proximity = state.get("proximity_summary") or {}
    parcel_context = state.get("parcel_context") or {}
    table_context = state.get("table_context") or {}
    table_recipe = table_context.get("table_recipe") if isinstance(table_context, dict) else {}
    table_recipe = table_recipe if isinstance(table_recipe, dict) else {}

    buckets = {"official": 0, "proxy": 0, "reference": 0, "derived_local": 0}
    for layer in [*visible_layers, *derived_overlays]:
        if not isinstance(layer, dict):
            continue
        bucket = _source_bucket(layer)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    distance = proximity.get("distance_value")
    distance_unit = proximity.get("distance_unit")
    proximity_distance = None
    if isinstance(distance, (int, float)):
        proximity_distance = {"value": distance, "unit": distance_unit or "miles"}

    return {
        "selected_visible_layer_count": len(visible_layers),
        "hidden_layer_count": len(hidden_layers),
        "derived_overlay_count": len(derived_overlays),
        "warning_count": len(warnings),
        "missing_data_count": len(missing_data),
        "source_coverage_counts": buckets,
        "proximity": {
            "available": bool(proximity),
            "distance": proximity_distance,
            "route_mode": proximity.get("route_mode"),
            "route_label": proximity.get("route_label"),
            "origin": proximity.get("origin_input") or proximity.get("origin_type"),
            "target": proximity.get("target_name") or proximity.get("target_type"),
        },
        "parcel": {
            "available": bool(parcel_context),
            "match_status": parcel_context.get("match_status")
            or parcel_context.get("origin_match_status")
            or proximity.get("property_match_status"),
            "selected_parcel_count": parcel_context.get("matched_count") or parcel_context.get("selected_parcel_count"),
        },
        "table": {
            "available": bool(table_context),
            "title": table_recipe.get("table_title"),
            "intent": table_recipe.get("table_intent"),
            "estimated_count": table_recipe.get("estimated_count"),
            "field_count": len(table_recipe.get("selected_fields") or []),
            "source_layer_count": len(table_recipe.get("source_layers") or []),
            "safety_status": table_recipe.get("safety_status"),
            "export_status": table_context.get("export_status") if isinstance(table_context, dict) else None,
            "returnGeometry": (table_recipe.get("query_options") or {}).get("returnGeometry"),
        },
        "permit_summary": {
            "available": False,
            "reason": "Official current permit source remains unresolved or was not requested for this map.",
        },
        "planning_cases_summary": {
            "available": False,
            "reason": "Planning case statistics are unavailable unless a verified bounded source is selected.",
        },
        "development_proxy_summary": {
            "available": False,
            "reason": "Development proxy layers are context only and are not official approval statistics.",
        },
    }
