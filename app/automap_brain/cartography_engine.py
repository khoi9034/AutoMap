"""Role-based cartography engine for AutoMap Brain v2."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


ROLE_DRAW_ORDER = {
    "context_polygon_muted": 20,
    "floodplain_overlay": 22,
    "primary_polygon_highlight": 24,
    "parcel_outline": 30,
    "affected_parcels": 34,
    "boundary_outline": 36,
    "road_context": 40,
    "major_road": 45,
    "route_line": 50,
    "origin_marker": 60,
    "target_marker": 62,
    "point_facility": 62,
    "historical_layer": 26,
    "table_only": 99,
}

CARTOGRAPHY_TOKENS: dict[str, dict[str, Any]] = {
    "commercial_zoning": {
        "cartography_role": "commercial_zoning",
        "map_role": "primary_polygon_highlight",
        "legend_label": "Commercial zoning",
        "opacity": 0.55,
        "fill": [37, 99, 235, 104],
        "outline": [30, 64, 175, 245],
        "width": 1.6,
        "min_stroke_width": 1.4,
        "scale_behavior": "primary_result_visible",
    },
    "zoning": {
        "cartography_role": "zoning",
        "map_role": "context_polygon_muted",
        "legend_label": "Zoning context",
        "opacity": 0.22,
        "fill": [100, 116, 139, 30],
        "outline": [71, 85, 105, 135],
        "width": 0.7,
        "min_stroke_width": 0.6,
        "scale_behavior": "muted_context",
    },
    "boundary": {
        "cartography_role": "boundary",
        "map_role": "boundary_outline",
        "legend_label": "Concord boundary",
        "opacity": 1.0,
        "fill": [255, 255, 255, 0],
        "outline": [15, 23, 42, 255],
        "width": 3.2,
        "min_stroke_width": 3.0,
        "scale_behavior": "outline_visible_at_municipality_scale",
    },
    "flood": {
        "cartography_role": "flood",
        "map_role": "floodplain_overlay",
        "legend_label": "100-year floodplain",
        "opacity": 0.46,
        "fill": [14, 165, 233, 112],
        "outline": [2, 132, 199, 235],
        "width": 1.8,
        "min_stroke_width": 1.6,
        "scale_behavior": "supporting_overlay_visible",
    },
    "affected_parcels": {
        "cartography_role": "affected_parcels",
        "map_role": "affected_parcels",
        "legend_label": "Parcels in 100-year floodplain",
        "opacity": 0.9,
        "fill": [245, 158, 11, 118],
        "outline": [146, 64, 14, 245],
        "width": 1.2,
        "min_stroke_width": 1.0,
        "scale_behavior": "primary_result_visible",
    },
    "parcel_context": {
        "cartography_role": "parcel_context",
        "map_role": "parcel_outline",
        "legend_label": "Parcels",
        "opacity": 0.24,
        "fill": [255, 255, 255, 0],
        "outline": [100, 116, 139, 145],
        "width": 0.55,
        "min_stroke_width": 0.5,
        "scale_behavior": "hide_or_mute_at_municipality_scale",
    },
    "roads": {
        "cartography_role": "roads",
        "map_role": "road_context",
        "legend_label": "Road context",
        "opacity": 0.82,
        "line": [51, 65, 85, 215],
        "width": 1.6,
        "min_stroke_width": 1.3,
        "scale_behavior": "context_lines_clipped_to_aoi",
    },
    "major_roads": {
        "cartography_role": "major_roads",
        "map_role": "major_road",
        "legend_label": "Major roads",
        "opacity": 0.94,
        "line": [31, 41, 55, 245],
        "width": 2.8,
        "min_stroke_width": 2.4,
        "scale_behavior": "major_context_lines",
    },
}

DENSE_POLYGON_FEATURE_THRESHOLD = 100
MEDIUM_POLYGON_FEATURE_THRESHOLD = 50

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


def map_purpose_for_recipe(recipe: dict[str, Any]) -> str:
    plan = recipe.get("request_plan") or {}
    explicit = str(recipe.get("map_purpose") or plan.get("map_purpose") or "").strip()
    if explicit:
        return explicit
    request_type = str(plan.get("request_type") or recipe.get("request_type") or "")
    if request_type == "proximity":
        return "proximity_route"
    if request_type == "floodplain_screening":
        return "relationship_overlay"
    primary = str(plan.get("primary_domain") or "")
    secondary = [str(item) for item in plan.get("secondary_domains") or [] if item]
    relationships = {str(item) for item in plan.get("spatial_relationships") or [] if item}
    if primary and secondary and relationships.intersection({"intersects", "within", "contains", "near", "around", "avoids"}):
        return "relationship_overlay"
    if request_type == "zoning_context":
        return "zoning_context"
    if request_type == "development_activity":
        return "development_activity"
    if request_type == "table_request":
        return "table_preview"
    return "general_reference"


def relationship_type_for_recipe(recipe: dict[str, Any]) -> str | None:
    if map_purpose_for_recipe(recipe) != "relationship_overlay":
        return None
    plan = recipe.get("request_plan") or {}
    explicit = str(recipe.get("relationship_type") or plan.get("relationship_type") or "").strip()
    if explicit:
        return explicit
    relationships = {str(item) for item in plan.get("spatial_relationships") or [] if item}
    if relationships.intersection({"intersects", "within", "contains"}):
        return "target_intersects_constraint"
    if relationships.intersection({"near", "around"}):
        return "target_near_context"
    if relationships.intersection({"avoids", "outside"}):
        return "target_avoids_constraint"
    return "target_intersects_constraint"


def simple_fill_renderer(fill: list[int], outline: list[int], width: float = 1.0) -> dict[str, Any]:
    return {"type": "simple", "symbol": {"type": "esriSFS", "style": "esriSFSSolid", "color": fill, "outline": {"type": "esriSLS", "style": "esriSLSSolid", "color": outline, "width": width}}}


def simple_line_renderer(color: list[int], width: float = 1.8, style: str = "esriSLSSolid") -> dict[str, Any]:
    return {"type": "simple", "symbol": {"type": "esriSLS", "style": style, "color": color, "width": width}}


def _style_from_token(token_key: str) -> dict[str, Any]:
    token = CARTOGRAPHY_TOKENS[token_key]
    if "line" in token:
        renderer = simple_line_renderer(token["line"], token["width"])
    else:
        renderer = simple_fill_renderer(token["fill"], token["outline"], token["width"])
    return {
        "cartography_role": token["cartography_role"],
        "map_role": token["map_role"],
        "legend_label": token["legend_label"],
        "opacity": token["opacity"],
        "drawing_info": {"renderer": renderer},
        "draw_order": ROLE_DRAW_ORDER.get(token["map_role"], 35),
        "min_stroke_width": token["min_stroke_width"],
        "scale_behavior": token["scale_behavior"],
    }


def _apply_relationship_compositing(style: dict[str, Any]) -> dict[str, Any]:
    next_style = deepcopy(style)
    role = str(next_style.get("map_role") or next_style.get("cartography_role") or "")
    symbol = (((next_style.get("drawing_info") or {}).get("renderer") or {}).get("symbol") or {})
    if role == "affected_parcels":
        symbol["color"] = [245, 158, 11, 62]
        if isinstance(symbol.get("outline"), dict):
            symbol["outline"]["color"] = [146, 64, 14, 205]
            symbol["outline"]["width"] = 1.1
        next_style.update(
            {
                "opacity": 0.74,
                "draw_order": ROLE_DRAW_ORDER["affected_parcels"],
                "relationship_role": "target_result",
                "compositing_mode": "target_fill_constraint_overlay",
            }
        )
    elif role == "floodplain_overlay":
        symbol["color"] = [14, 165, 233, 128]
        if isinstance(symbol.get("outline"), dict):
            symbol["outline"]["color"] = [2, 132, 199, 255]
            symbol["outline"]["width"] = 2.25
        next_style.update(
            {
                "opacity": 0.68,
                "draw_order": ROLE_DRAW_ORDER["affected_parcels"] + 1,
                "relationship_role": "constraint_overlay",
                "compositing_mode": "constraint_visible_above_target",
            }
        )
    return next_style


def display_mode_for_role(
    role: str,
    *,
    feature_count: int = 0,
    geometry_type: str = "polygon",
    focus_mode: str | None = None,
) -> dict[str, Any]:
    """Return the lightest display mode that keeps dense primary results readable."""
    normalized_role = str(role or "")
    normalized_geometry = str(geometry_type or "").lower()
    try:
        count = int(feature_count or 0)
    except (TypeError, ValueError):
        count = 0
    is_primary_polygon = normalized_geometry in {"polygon", "multipolygon", "esrigeometrypolygon"} and normalized_role in {
        "affected_parcels",
        "primary_result",
        "primary_polygon_highlight",
        "commercial_zoning",
    }
    if not is_primary_polygon:
        return {
            "display_mode": "detailed_features",
            "visual_density_score": count,
            "outline_visibility": "normal",
            "recommendation": "standard_role_style",
        }
    if count >= DENSE_POLYGON_FEATURE_THRESHOLD:
        return {
            "display_mode": "dissolved_result_area",
            "visual_density_score": count,
            "outline_visibility": "generalized_area_outline",
            "outline_width": 1.2,
            "fill_opacity": 0.46,
            "simplification_tolerance": 0.00004,
            "recommendation": "generalize_dense_primary_polygons",
            "diagnostic_note": "Display generalized from affected parcel features for map readability.",
            "focus_mode": focus_mode or "result_focused",
        }
    if count >= MEDIUM_POLYGON_FEATURE_THRESHOLD:
        return {
            "display_mode": "simplified_features",
            "visual_density_score": count,
            "outline_visibility": "thin",
            "outline_width": 1.0,
            "fill_opacity": 0.44,
            "simplification_tolerance": 0.00002,
            "recommendation": "thin_dense_primary_outlines",
            "focus_mode": focus_mode or "result_focused",
        }
    return {
        "display_mode": "detailed_features",
        "visual_density_score": count,
        "outline_visibility": "normal",
        "outline_width": 1.2,
        "fill_opacity": 0.46,
        "simplification_tolerance": 0,
        "recommendation": "show_individual_features",
        "focus_mode": focus_mode or "result_focused",
    }


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


def _commercial_zoning_fallback_warning(recipe: dict[str, Any]) -> str:
    geography = ((recipe.get("request_plan") or {}).get("parameters") or {}).get("geography") or "requested area"
    return f"Commercial zoning values were not confidently identified; showing zoning context around {geography}."


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


def cartography_for_role(role: str, *, major_requested: bool = False, map_purpose: str | None = None) -> dict[str, Any]:
    if role == "commercial_zoning":
        style = _style_from_token("commercial_zoning")
    elif role == "zoning":
        style = _style_from_token("zoning")
    elif role == "roads":
        style = _style_from_token("major_roads" if major_requested else "roads")
    elif role == "boundary":
        style = _style_from_token("boundary")
    elif role == "flood":
        style = _style_from_token("flood")
    elif role == "affected_parcels":
        style = _style_from_token("affected_parcels")
    elif role == "parcel_context":
        style = _style_from_token("parcel_context")
    else:
        style = {"cartography_role": role, "legend_label": "Context layer", "opacity": 0.65}
    return _apply_relationship_compositing(style) if map_purpose == "relationship_overlay" else style


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
    if isinstance(layer.get("draw_order"), (int, float)):
        return int(layer["draw_order"])
    role = str(layer.get("map_role") or layer.get("cartography_role") or context_role(layer))
    return ROLE_DRAW_ORDER.get(role, draw_order_for_role(role))


def plain_legend_label(layer: dict[str, Any]) -> str:
    labels = {"primary_polygon_highlight": "Commercial zoning", "context_polygon_muted": "Zoning context", "boundary_outline": "Concord boundary", "affected_parcels": "Parcels in 100-year floodplain", "parcel_outline": "Parcels", "floodplain_overlay": "100-year floodplain", "road_context": "Road context", "major_road": "Major roads", "route_line": "Road-following draft route"}
    role = str(layer.get("map_role") or layer.get("cartography_role") or context_role(layer))
    return str(layer.get("legend_label") or labels.get(role) or layer.get("title") or "Context layer")


def style_context_layer(layer: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    item = deepcopy(layer)
    role = context_role(item)
    map_purpose = map_purpose_for_recipe(recipe)
    major_requested = "major" in str(recipe.get("user_intent") or "").lower()
    if role == "zoning" and request_is_commercial_zoning(recipe) and item.get("definition_expression"):
        style = cartography_for_role("commercial_zoning", map_purpose=map_purpose)
        item["title"] = "Commercial zoning"
    elif role == "zoning":
        style = cartography_for_role("zoning", map_purpose=map_purpose)
        item["title"] = "Zoning context"
    elif role == "roads":
        style = cartography_for_role("roads", major_requested=major_requested, map_purpose=map_purpose)
        item["title"] = style["legend_label"]
    elif role == "boundary":
        style = cartography_for_role("boundary", map_purpose=map_purpose)
        item["title"] = "Concord boundary" if "concord" in str(recipe.get("user_intent") or "").lower() else "Boundary"
        if item["title"] == "Boundary":
            style = {**style, "legend_label": "Boundary"}
    elif role == "flood":
        style = cartography_for_role("flood", map_purpose=map_purpose)
        item["title"] = "100-year floodplain"
    elif role == "affected_parcels":
        style = cartography_for_role("affected_parcels", map_purpose=map_purpose)
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
    by_id = {str(row.get("layer_id")): row for row in qa.get("visible_feature_summary") or [] if isinstance(row, dict) and row.get("fallback_used")}
    zoning_failed = request_is_commercial_zoning(recipe) and any(
        isinstance(row, dict)
        and row.get("expected_role") == "zoning"
        and row.get("visible") is not False
        and row.get("query_status") in {"query_failed", "source_unavailable", "zero_features"}
        for row in qa.get("visible_feature_summary") or []
    )
    if not by_id and not zoning_failed:
        return config
    patched = deepcopy(config)
    fallback_key: str | None = None
    if zoning_failed and not by_id:
        zoning_layers = [
            layer
            for layer in patched.get("context_layers") or []
            if isinstance(layer, dict) and "zoning" in layer_text(layer) and (layer.get("layer_url") or layer.get("url") or layer.get("service_url"))
        ]
        preferred = next((layer for layer in zoning_layers if not layer.get("definition_expression") and not layer.get("visibility", True)), None)
        fallback_layer = preferred or next((layer for layer in zoning_layers if not layer.get("definition_expression")), None) or (zoning_layers[0] if zoning_layers else None)
        if fallback_layer:
            fallback_key = str(fallback_layer.get("layer_key") or fallback_layer.get("id") or fallback_layer.get("title") or "")
    next_layers: list[dict[str, Any]] = []
    for layer in patched.get("context_layers") or []:
        if not isinstance(layer, dict):
            next_layers.append(layer)
            continue
        key = str(layer.get("layer_key") or layer.get("id") or layer.get("title") or "")
        row = by_id.get(key)
        if (row and row.get("expected_role") == "zoning") or (fallback_key and key == fallback_key):
            layer = deepcopy(layer)
            layer.pop("definition_expression", None)
            layer.update({"title": "Zoning context", "fallback_used": True, "visibility": True, "default_visible": True, "visible_by_default": True, "diagnostics_only": False, **cartography_for_role("zoning")})
            warnings = list(layer.get("review_warnings") or [])
            warning = row.get("warning") if row else _commercial_zoning_fallback_warning(recipe)
            if warning and warning not in warnings:
                warnings.append(str(warning))
            layer["review_warnings"] = warnings
        next_layers.append(layer)
    patched["context_layers"] = sorted(next_layers, key=lambda item: context_draw_rank(item) if isinstance(item, dict) else 99)
    return patched
