"""Role-based cartography engine for AutoMap Brain v2."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ROLE_DRAW_ORDER = {
    "boundary_outline": 10,
    "context_polygon_muted": 20,
    "floodplain_overlay": 22,
    "primary_polygon_highlight": 24,
    "parcel_outline": 30,
    "affected_parcels": 34,
    "road_context": 40,
    "major_road": 45,
    "route_line": 50,
    "origin_marker": 60,
    "target_marker": 62,
    "point_facility": 62,
    "historical_layer": 26,
    "table_only": 99,
}

UNIVERSAL_LAYER_ROLES = {
    "affected_parcels": "primary_result",
    "primary_polygon_highlight": "primary_result",
    "commercial_zoning": "primary_result",
    "route_line": "primary_result",
    "floodplain_overlay": "supporting_context",
    "context_polygon_muted": "supporting_context",
    "flood": "supporting_context",
    "zoning": "supporting_context",
    "boundary_outline": "boundary_context",
    "boundary": "boundary_context",
    "major_road": "transportation_context",
    "road_context": "transportation_context",
    "major_roads": "transportation_context",
    "roads": "transportation_context",
    "parcel_outline": "reference_context",
    "parcel_context": "reference_context",
    "diagnostics_only": "diagnostic_hidden",
    "table_only": "diagnostic_hidden",
    "origin_marker": "label_overlay",
    "target_marker": "label_overlay",
    "point_facility": "label_overlay",
}


def universal_layer_role(layer_or_role: dict[str, Any] | str) -> str:
    role = layer_or_role if isinstance(layer_or_role, str) else layer_or_role.get("map_role") or layer_or_role.get("cartography_role") or context_role(layer_or_role)
    return UNIVERSAL_LAYER_ROLES.get(str(role), "supporting_context")


def simple_fill_renderer(fill: list[int], outline: list[int], width: float = 1.0) -> dict[str, Any]:
    return {"type": "simple", "symbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": fill, "outline": {"type": "esriSLS", "style": "esriSLSSolid", "color": outline, "width": width}}}


def simple_line_renderer(color: list[int], width: float = 1.8, style: str = "esriSLSSolid") -> dict[str, Any]:
    return {"type": "simple", "symbol": {"type": "esriSLS", "style": style, "color": color, "width": width}}


def layer_text(layer: dict[str, Any]) -> str:
    return " ".join(
        str(value or "").lower()
        for value in [
            layer.get("title"),
            layer.get("layer_key"),
            layer.get("layer_name"),
            layer.get("role"),
            layer.get("category"),
            layer.get("map_role"),
            layer.get("cartography_role"),
            layer.get("geometry_role"),
            layer.get("legend_label"),
        ]
    )


def request_is_commercial_zoning(recipe: dict[str, Any]) -> bool:
    plan = recipe.get("request_plan") or {}
    parsed = recipe.get("parsed_request") or {}
    return plan.get("request_type") == "zoning_context" and (plan.get("zoning_category") == "commercial" or "commercial" in (parsed.get("topic_details", {}).get("zoning_modifiers") or []))


def context_role(layer: dict[str, Any]) -> str:
    if layer.get("diagnostics_only") or layer.get("map_role") == "diagnostics_only" or layer.get("display_role") == "diagnostics_only":
        return "diagnostics_only"
    blob = layer_text(layer)
    if "affected_parcels" in blob or ("affected" in blob and "parcel" in blob):
        return "affected_parcels"
    if "road" in blob or "street" in blob or "centerline" in blob:
        return "roads"
    if "zoning" in blob:
        return "zoning"
    if "flood" in blob:
        return "flood"
    if "municipal" in blob or "district" in blob or "boundary" in blob:
        return "boundary"
    if "parcel" in blob:
        return "parcel_context"
    return str(layer.get("role") or layer.get("category") or "context")


def cartography_for_role(role: str, *, major_requested: bool = False) -> dict[str, Any]:
    if role == "commercial_zoning":
        return {"cartography_role": "commercial_zoning", "map_role": "primary_polygon_highlight", "legend_label": "Commercial zoning", "opacity": 0.48, "drawing_info": {"renderer": simple_fill_renderer([37, 99, 235, 92], [30, 64, 175, 235], 1.35)}}
    if role == "zoning":
        return {"cartography_role": "zoning", "map_role": "context_polygon_muted", "legend_label": "Zoning context", "opacity": 0.22, "drawing_info": {"renderer": simple_fill_renderer([100, 116, 139, 34], [71, 85, 105, 155], 0.7)}}
    if role == "roads":
        return {"cartography_role": "major_roads" if major_requested else "roads", "map_role": "major_road" if major_requested else "road_context", "legend_label": "Major roads" if major_requested else "Road context", "opacity": 0.92, "drawing_info": {"renderer": simple_line_renderer([31, 41, 55, 238], 2.4 if major_requested else 1.7)}}
    if role == "boundary":
        return {"cartography_role": "boundary", "map_role": "boundary_outline", "legend_label": "Concord boundary", "opacity": 0.88, "drawing_info": {"renderer": simple_fill_renderer([255, 255, 255, 0], [17, 24, 39, 210], 1.8)}}
    if role == "flood":
        return {"cartography_role": "flood", "map_role": "floodplain_overlay", "legend_label": "100-year floodplain", "opacity": 0.34, "drawing_info": {"renderer": simple_fill_renderer([56, 189, 248, 74], [3, 105, 161, 210], 1.0)}}
    if role == "affected_parcels":
        return {"cartography_role": "affected_parcels", "map_role": "affected_parcels", "legend_label": "Parcels in 100-year floodplain", "opacity": 0.84, "drawing_info": {"renderer": simple_fill_renderer([249, 115, 22, 86], [154, 52, 18, 238], 1.45)}}
    if role == "parcel_context":
        return {"cartography_role": "parcel_context", "map_role": "parcel_outline", "legend_label": "Parcels", "opacity": 0.34, "drawing_info": {"renderer": simple_fill_renderer([255, 255, 255, 0], [100, 116, 139, 190], 0.55)}}
    return {"cartography_role": role, "legend_label": "Context layer", "opacity": 0.65}


def draw_order_for_role(role: str) -> int:
    if role == "commercial_zoning":
        return ROLE_DRAW_ORDER["primary_polygon_highlight"]
    if role == "zoning":
        return ROLE_DRAW_ORDER["context_polygon_muted"]
    if role == "roads":
        return ROLE_DRAW_ORDER["road_context"]
    if role == "boundary":
        return ROLE_DRAW_ORDER["boundary_outline"]
    if role == "flood":
        return ROLE_DRAW_ORDER["floodplain_overlay"]
    if role == "affected_parcels":
        return ROLE_DRAW_ORDER["affected_parcels"]
    if role == "parcel_context":
        return ROLE_DRAW_ORDER["parcel_outline"]
    return ROLE_DRAW_ORDER.get(role, 35)


def context_draw_rank(layer: dict[str, Any]) -> int:
    role = str(layer.get("map_role") or layer.get("cartography_role") or context_role(layer))
    return ROLE_DRAW_ORDER.get(role, draw_order_for_role(role))


def plain_legend_label(layer: dict[str, Any]) -> str:
    labels = {"primary_polygon_highlight": "Commercial zoning", "context_polygon_muted": "Zoning context", "boundary_outline": "Concord boundary", "affected_parcels": "Parcels in 100-year floodplain", "parcel_outline": "Parcels", "floodplain_overlay": "100-year floodplain", "road_context": "Road context", "major_road": "Major roads", "route_line": "Road-following draft route"}
    role = str(layer.get("map_role") or layer.get("cartography_role") or context_role(layer))
    return str(layer.get("legend_label") or labels.get(role) or layer.get("title") or "Context layer")


def style_context_layer(layer: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(layer)
    role = context_role(item)
    major_requested = "major" in str(recipe.get("user_intent") or "").lower()
    if role == "zoning" and request_is_commercial_zoning(recipe) and item.get("definition_expression"):
        style = cartography_for_role("commercial_zoning")
        item["title"] = "Commercial zoning"
    elif role == "zoning":
        style = cartography_for_role("zoning")
        item["title"] = "Zoning context"
    elif role == "roads":
        style = cartography_for_role("roads", major_requested=major_requested)
        item["title"] = style["legend_label"]
    elif role == "boundary":
        style = cartography_for_role("boundary")
        item["title"] = "Concord boundary" if "concord" in str(recipe.get("user_intent") or "").lower() else "Boundary"
        if item["title"] == "Boundary":
            style = {**style, "legend_label": "Boundary"}
    elif role == "flood":
        style = cartography_for_role("flood")
        item["title"] = "100-year floodplain"
    elif role == "affected_parcels":
        style = cartography_for_role("affected_parcels")
        item["title"] = "Parcels in 100-year floodplain"
    elif role == "parcel_context":
        style = cartography_for_role("parcel_context")
    else:
        style = {"cartography_role": role, "legend_label": item.get("title") or "Context layer"}
    for key, value in style.items():
        item[key] = min(float(item.get("opacity") or value), float(value)) if key == "opacity" and role == "parcel_context" else value
    item["draw_order"] = context_draw_rank(item)
    item["layer_role"] = universal_layer_role(item)
    return item


def apply_visible_qa_fallbacks(config: dict[str, Any], qa: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    if not qa.get("fallback_used"):
        return config
    by_id = {str(row.get("layer_id")): row for row in qa.get("visible_feature_summary") or [] if isinstance(row, dict) and row.get("fallback_used")}
    if not by_id:
        return config
    patched = deepcopy(config)
    next_layers: list[dict[str, Any]] = []
    for layer in patched.get("context_layers") or []:
        if not isinstance(layer, dict):
            next_layers.append(layer)
            continue
        key = str(layer.get("layer_key") or layer.get("id") or layer.get("title") or "")
        row = by_id.get(key)
        if row and row.get("expected_role") == "zoning":
            layer = deepcopy(layer)
            layer.pop("definition_expression", None)
            layer.update({"title": "Zoning context", "fallback_used": True, **cartography_for_role("zoning")})
            warnings = list(layer.get("review_warnings") or [])
            warning = row.get("warning")
            if warning and warning not in warnings:
                warnings.append(str(warning))
            layer["review_warnings"] = warnings
        next_layers.append(layer)
    patched["context_layers"] = sorted(next_layers, key=lambda item: context_draw_rank(item) if isinstance(item, dict) else 99)
    return patched
