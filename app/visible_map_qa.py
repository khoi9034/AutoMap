"""Bounded visible-map QA for composer preview layers."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.geometry_utils import buffer_extent
from app.spatial_query_client import SpatialQueryClient


DEFAULT_QA_TIMEOUT_SECONDS = 4
SPATIAL_REL_INTERSECTS = "esriSpatialRelIntersects"
ENVELOPE_GEOMETRY_TYPE = "esriGeometryEnvelope"
CONCORD_FALLBACK_EXTENT = {
    "xmin": -80.72,
    "ymin": 35.30,
    "xmax": -80.46,
    "ymax": 35.49,
    "spatialReference": {"wkid": 4326},
}


def _extent(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    try:
        return {
            "xmin": float(value["xmin"]),
            "ymin": float(value["ymin"]),
            "xmax": float(value["xmax"]),
            "ymax": float(value["ymax"]),
            "spatialReference": value.get("spatialReference") or {"wkid": 4326},
        }
    except (KeyError, TypeError, ValueError):
        return None


def _union_extent(extents: list[dict[str, Any]]) -> dict[str, Any] | None:
    normalized = [_extent(item) for item in extents]
    normalized = [item for item in normalized if item]
    if not normalized:
        return None
    return {
        "xmin": min(item["xmin"] for item in normalized),
        "ymin": min(item["ymin"] for item in normalized),
        "xmax": max(item["xmax"] for item in normalized),
        "ymax": max(item["ymax"] for item in normalized),
        "spatialReference": normalized[0].get("spatialReference") or {"wkid": 4326},
    }


def _layer_url(layer: dict[str, Any]) -> str | None:
    url = layer.get("layer_url") or layer.get("url")
    if isinstance(url, str) and url:
        return url
    service_url = layer.get("service_url")
    layer_id = layer.get("layer_id")
    if isinstance(service_url, str) and isinstance(layer_id, int):
        return f"{service_url.rstrip('/')}/{layer_id}"
    return None


def _layer_text(layer: dict[str, Any]) -> str:
    parts = [
        layer.get("layer_key"),
        layer.get("title"),
        layer.get("layer_name"),
        layer.get("role"),
        layer.get("category"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _definition(layer: dict[str, Any]) -> str | None:
    expression = layer.get("definition_expression")
    if isinstance(expression, str) and expression.strip():
        return expression.strip()
    definition = layer.get("layerDefinition") or {}
    expression = definition.get("definitionExpression") if isinstance(definition, dict) else None
    return expression.strip() if isinstance(expression, str) and expression.strip() else None


def _visibility(layer: dict[str, Any]) -> bool:
    if "visibility" in layer:
        return bool(layer.get("visibility"))
    if "default_visible" in layer:
        return bool(layer.get("default_visible"))
    return True


def _expected_role(layer: dict[str, Any]) -> str:
    blob = _layer_text(layer)
    if "zoning" in blob:
        return "zoning"
    if "road" in blob or "street" in blob or "centerline" in blob:
        return "roads"
    if "municipal" in blob or "district" in blob or "boundary" in blob:
        return "boundary"
    if "parcel" in blob:
        return "parcel_context"
    return str(layer.get("role") or layer.get("category") or "context")


def _is_commercial_zoning_context(recipe: dict[str, Any]) -> bool:
    plan = recipe.get("request_plan") or {}
    parsed = recipe.get("parsed_request") or {}
    return (
        plan.get("request_type") == "zoning_context"
        and (
            plan.get("zoning_category") == "commercial"
            or "commercial" in (parsed.get("topic_details", {}).get("zoning_modifiers") or [])
        )
    )


def _zoning_fallback_warning(recipe: dict[str, Any]) -> str:
    geography = ((recipe.get("request_plan") or {}).get("parameters") or {}).get("geography") or "requested area"
    return f"Commercial zoning values were not confidently identified; showing zoning context around {geography}."


def _road_fallback_warning(preview_config: dict[str, Any] | None = None) -> str:
    aoi = (preview_config or {}).get("aoi") if isinstance(preview_config, dict) else {}
    geography = (aoi or {}).get("geography_name") or "the requested area"
    return f"Major-road classification unavailable; showing road context clipped to {geography}."


def _is_route_or_derived(layer: dict[str, Any]) -> bool:
    return bool(layer.get("derived_local_analysis") or layer.get("local_output") or str(layer.get("preview_type") or "") == "local_geojson")


def visible_map_qa(
    preview_config: dict[str, Any] | None,
    recipe: dict[str, Any],
    *,
    query_client: SpatialQueryClient | None = None,
) -> dict[str, Any]:
    """Confirm visible operational layers have safe count/extent metadata."""
    if not preview_config:
        return {
            "visible_feature_summary": [],
            "visible_feature_total": 0,
            "visible_extent": None,
            "warnings": ["Preview config unavailable for visible-map QA."],
            "fallback_used": False,
        }
    client = query_client or SpatialQueryClient(max_features=250, timeout=DEFAULT_QA_TIMEOUT_SECONDS)
    aoi = preview_config.get("aoi") if isinstance(preview_config.get("aoi"), dict) else {}
    request_extent = _extent((aoi or {}).get("extent") or preview_config.get("focus_extent") or preview_config.get("initial_extent")) or CONCORD_FALLBACK_EXTENT
    layers = deepcopy(preview_config.get("context_layers") or preview_config.get("operational_layers") or [])
    commercial_context = _is_commercial_zoning_context(recipe)
    summary: list[dict[str, Any]] = []
    warnings: list[str] = []
    extents: list[dict[str, Any]] = []
    fallback_used = False
    local_aoi = bool(aoi and aoi.get("type") not in {"county", "unknown"})
    display_complexity = preview_config.get("display_complexity") if isinstance(preview_config.get("display_complexity"), dict) else {}
    if display_complexity.get("status") == "complex":
        warnings.append("Visible layer stack was complex; low-priority layers should be hidden or muted.")

    for layer in layers:
        layer_key = str(layer.get("layer_key") or layer.get("id") or layer.get("title") or "layer")
        layer_title = str(layer.get("title") or layer.get("layer_name") or layer_key)
        visible = _visibility(layer)
        expected_role = _expected_role(layer)
        where = _definition(layer)
        url = _layer_url(layer)
        clipped_to_aoi = bool(layer.get("clipped_to_aoi"))
        aoi_filter_applied = bool(layer.get("aoi_filter_applied"))
        row: dict[str, Any] = {
            "layer_id": layer_key,
            "layer_title": layer_title,
            "expected_role": expected_role,
            "map_role": layer.get("map_role") or layer.get("cartography_role") or layer.get("role"),
            "feature_count": None,
            "visible": visible,
            "visible_by_default": layer.get("visible_by_default", visible),
            "opacity": layer.get("opacity"),
            "fallback_used": False,
            "warning": None,
            "where": where,
            "clipped_to_aoi": clipped_to_aoi,
            "aoi_filter_applied": aoi_filter_applied,
            "aoi_summary": (aoi or {}).get("summary"),
            "max_feature_count": layer.get("max_feature_count"),
            "simplification_applied": bool(layer.get("simplification_applied")),
        }
        if not visible:
            summary.append(row)
            continue
        if local_aoi and not clipped_to_aoi:
            row["warning"] = "Visible local layer is not marked as clipped to the requested AOI."
            warnings.append(row["warning"])
        if _is_route_or_derived(layer):
            row["feature_count"] = 1
            summary.append(row)
            continue
        if not url:
            row["warning"] = "Layer source URL unavailable for preview QA."
            warnings.append(row["warning"])
            summary.append(row)
            continue
        try:
            count = client.query_count(
                url,
                where=where,
                geometry=request_extent,
                geometry_type=ENVELOPE_GEOMETRY_TYPE,
                spatial_rel=SPATIAL_REL_INTERSECTS,
            )
            row["feature_count"] = int(count.get("count") or 0)
            if row["feature_count"] > 0:
                try:
                    extent_result = client.query_extent(
                        url,
                        where=where,
                        geometry=request_extent,
                        geometry_type=ENVELOPE_GEOMETRY_TYPE,
                        spatial_rel=SPATIAL_REL_INTERSECTS,
                    )
                    if extent_result.get("extent"):
                        extents.append(extent_result["extent"])
                except Exception:
                    pass
            elif expected_role == "zoning" and commercial_context and where:
                fallback_count = client.query_count(
                    url,
                    where=None,
                    geometry=request_extent,
                    geometry_type=ENVELOPE_GEOMETRY_TYPE,
                    spatial_rel=SPATIAL_REL_INTERSECTS,
                )
                if int(fallback_count.get("count") or 0) > 0:
                    row["feature_count"] = int(fallback_count["count"])
                    row["where"] = None
                    row["fallback_used"] = True
                    row["warning"] = _zoning_fallback_warning(recipe)
                    warnings.append(row["warning"])
                    fallback_used = True
            elif expected_role == "roads" and "major" in str(recipe.get("user_intent") or "").lower():
                row["fallback_used"] = True
                row["warning"] = _road_fallback_warning(preview_config)
                warnings.append(row["warning"])
                fallback_used = True
            if layer.get("max_feature_count") and row.get("feature_count") is not None:
                try:
                    if int(row["feature_count"]) > int(layer["max_feature_count"]):
                        row["warning"] = row.get("warning") or "Feature count is high for this local map; AutoMap should simplify or hide context."
                        warnings.append(row["warning"])
                except (TypeError, ValueError):
                    pass
        except Exception as exc:
            row["warning"] = f"Feature count check unavailable for {layer_title}: {exc}"
            warnings.append(row["warning"])
        summary.append(row)

    visible_counts = [int(item.get("feature_count") or 0) for item in summary if item.get("visible")]
    visible_total = sum(visible_counts)
    visible_extent = _union_extent(extents)
    if not visible_extent and visible_total > 0:
        visible_extent = request_extent
    if visible_extent:
        visible_extent = buffer_extent(visible_extent, ratio=0.08, minimum=0.003)
    if visible_total == 0:
        warnings.append(
            "AutoMap found the relevant layers but the filter returned no visible features. Try broadening the zoning filter or showing all zoning around Concord."
        )
    return {
        "visible_feature_summary": summary,
        "visible_feature_total": visible_total,
        "visible_extent": visible_extent,
        "warnings": sorted({warning for warning in warnings if warning}),
        "fallback_used": fallback_used,
    }
