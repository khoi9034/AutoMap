"""Spatial operation planning for AutoMap Brain Kernel v1."""

from __future__ import annotations

from typing import Any

from app.automap_brain.parameter_extractor import extract_parameters


def _layer_roles_for_plan(plan: dict[str, Any], params: dict[str, Any]) -> list[str]:
    request_type = str(plan.get("request_type") or "")
    domains = {plan.get("primary_domain"), *(plan.get("secondary_domains") or [])}
    if request_type == "proximity":
        return ["origin_marker", "target_marker", "route_line"]
    if request_type == "floodplain_screening":
        roles = ["affected_parcels", "parcel_outline", "floodplain_overlay", "boundary_outline"]
        if "transportation" in domains:
            roles.append("road_context")
        return roles
    if request_type == "zoning_context":
        roles = ["primary_polygon_highlight", "boundary_outline"]
        if "transportation" in domains:
            roles.append("major_road")
        return roles
    if request_type == "table_request":
        return ["table_source", "table_only"]
    if request_type == "development_activity":
        return ["primary_result", "point_facility", "boundary_outline"]
    if request_type == "historical_lookup":
        return ["historical_layer", "boundary_outline"]
    if request_type == "suitability":
        return ["primary_polygon_highlight", "road_context", "floodplain_overlay", "boundary_outline"]
    if "parcels" in domains:
        return ["primary_result", "boundary_outline"]
    return ["context_polygon_muted"]


def plan_spatial_operation(
    request_plan: dict[str, Any],
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Infer the spatial operation that answers the request."""
    params = parameters or extract_parameters(
        str(request_plan.get("original_prompt") or request_plan.get("normalized_prompt") or ""),
        request_plan=request_plan,
    )
    request_type = str(request_plan.get("request_type") or "")
    relationships = set(request_plan.get("spatial_relationships") or [])
    domains = {request_plan.get("primary_domain"), *(request_plan.get("secondary_domains") or [])}
    operation = "context_only"
    result_role = "primary_result"
    method = "layer_context"
    clip_to_aoi = True
    reasoning = "Show relevant layers clipped to the area of interest."

    if request_type == "proximity":
        operation = "closest_by_road"
        result_role = "route_line"
        method = "road_network"
        reasoning = "Match the origin, compare candidate facilities by road-network cost when available, and render the route."
    elif request_type == "floodplain_screening":
        operation = "intersects"
        result_role = "affected_parcels"
        method = "parcel_floodplain_intersection"
        reasoning = "Select parcels in the AOI that intersect the requested floodplain layer."
    elif request_type == "zoning_context":
        operation = "clipped_to_aoi"
        result_role = "primary_polygon_highlight"
        method = "filtered_context_map"
        reasoning = "Filter zoning values when confident and clip zoning and road context to the AOI."
    elif "near_or_around" in relationships and "excluding" in relationships and {"parcels", "transportation", "floodplain"}.issubset(domains):
        operation = "near_and_avoids"
        result_role = "affected_parcels"
        method = "parcel_suitability_screening"
        reasoning = "Screen parcels near transportation context while excluding floodplain exposure."
    elif request_type == "table_request":
        operation = "attribute_projection"
        result_role = "table_source"
        method = "bounded_table_preview"
        clip_to_aoi = False
        reasoning = "Return requested fields with safe row limits and no geometry unless needed."

    return {
        "operation": operation,
        "method": method,
        "spatial_relationship": operation if operation in {"intersects", "within", "contains", "near", "around"} else params.get("spatial_relationship"),
        "result_layer_role": result_role,
        "layer_roles": _layer_roles_for_plan(request_plan, params),
        "clip_to_aoi": clip_to_aoi,
        "target_features": params.get("target_features") or [],
        "context_features": params.get("context_features") or [],
        "requires_geometry": operation in {"intersects", "near_and_avoids", "closest_by_road"},
        "fallback_allowed": operation != "attribute_projection",
        "reasoning": reasoning,
        "safety_notes": [
            "Use bounded spatial queries only.",
            "Do not search owner/name fields.",
            "Do not publish real ArcGIS items.",
        ],
    }
