"""Area-of-interest planning and local map complexity controls."""

from __future__ import annotations

from copy import deepcopy
import math
from typing import Any

from app.automap_brain.cartography_engine import cartography_for_role


COUNTY_EXTENT = {"xmin": -80.86, "ymin": 35.15, "xmax": -80.32, "ymax": 35.55, "spatialReference": {"wkid": 4326}}

KNOWN_GEOGRAPHY_EXTENTS = {
    "cabarrus county": COUNTY_EXTENT,
    "countywide": COUNTY_EXTENT,
    "concord": {"xmin": -80.72, "ymin": 35.30, "xmax": -80.46, "ymax": 35.49, "spatialReference": {"wkid": 4326}},
    "kannapolis": {"xmin": -80.73, "ymin": 35.43, "xmax": -80.55, "ymax": 35.56, "spatialReference": {"wkid": 4326}},
    "harrisburg": {"xmin": -80.70, "ymin": 35.27, "xmax": -80.56, "ymax": 35.38, "spatialReference": {"wkid": 4326}},
    "midland": {"xmin": -80.58, "ymin": 35.20, "xmax": -80.44, "ymax": 35.32, "spatialReference": {"wkid": 4326}},
    "mount pleasant": {"xmin": -80.48, "ymin": 35.34, "xmax": -80.36, "ymax": 35.45, "spatialReference": {"wkid": 4326}},
    "mt pleasant": {"xmin": -80.48, "ymin": 35.34, "xmax": -80.36, "ymax": 35.45, "spatialReference": {"wkid": 4326}},
    "locust": {"xmin": -80.45, "ymin": 35.21, "xmax": -80.35, "ymax": 35.31, "spatialReference": {"wkid": 4326}},
}

MAJOR_ROUTE_TOKENS = ["I-85", "I 85", "INTERSTATE", "US 29", "US-29", "US 601", "US-601", "NC 49", "NC-49", "NC 73", "NC-73", "NC 24", "NC-24", "NC 27", "NC-27"]


def _normalize_extent(value: Any) -> dict[str, Any] | None:
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


def _buffer_extent_miles(extent: dict[str, Any], miles: float) -> dict[str, Any]:
    if miles <= 0:
        return deepcopy(extent)
    center_lat = (float(extent["ymin"]) + float(extent["ymax"])) / 2
    lat_degrees = miles / 69.0
    lon_degrees = miles / max(69.0 * math.cos(math.radians(center_lat)), 1)
    return {
        "xmin": float(extent["xmin"]) - lon_degrees,
        "ymin": float(extent["ymin"]) - lat_degrees,
        "xmax": float(extent["xmax"]) + lon_degrees,
        "ymax": float(extent["ymax"]) + lat_degrees,
        "spatialReference": extent.get("spatialReference") or {"wkid": 4326},
    }


def _prompt_text(recipe: dict[str, Any]) -> str:
    plan = recipe.get("request_plan") or {}
    parsed = recipe.get("parsed_request") or {}
    return " ".join(
        str(value or "").lower()
        for value in [
            recipe.get("user_intent"),
            recipe.get("raw_prompt"),
            parsed.get("normalized_prompt"),
            plan.get("normalized_prompt"),
        ]
    )


def _geography_name(recipe: dict[str, Any]) -> tuple[str | None, str | None]:
    plan = recipe.get("request_plan") or {}
    params = plan.get("parameters") if isinstance(plan.get("parameters"), dict) else {}
    geography = plan.get("geography") or params.get("geography")
    geography_type = plan.get("geography_type")
    if geography:
        return str(geography), str(geography_type or "")
    parsed_terms = (recipe.get("parsed_request") or {}).get("geography_terms") or []
    for term in parsed_terms:
        if isinstance(term, dict) and term.get("name"):
            return str(term["name"]), str(term.get("type") or "")
    return None, None


def _buffer_distance_for(recipe: dict[str, Any], geography_type: str | None) -> float:
    text = _prompt_text(recipe)
    plan = recipe.get("request_plan") or {}
    relationships = set(plan.get("spatial_relationships") or [])
    if geography_type in {"county", "countywide"}:
        return 0
    if "route" in text or plan.get("request_type") == "proximity":
        return 0.5
    if "around" in text or "nearby" in text or "near_or_around" in relationships:
        if "major road" in text or "roads" in text:
            return 2.0
        return 1.5
    if "near" in text:
        return 1.0
    return 0.25


def build_aoi_plan(recipe: dict[str, Any], preview_config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Derive a bounded map AOI from the interpreted request."""
    plan = recipe.get("request_plan") or {}
    request_type = str(plan.get("request_type") or recipe.get("request_type") or "")
    geography, geography_type = _geography_name(recipe)
    suggested_extent = _normalize_extent(recipe.get("suggested_extent"))
    if request_type == "proximity" and suggested_extent:
        return {
            "type": "route_corridor",
            "geography_name": geography or "Route area",
            "source_layer": "proximity_result",
            "geometry": {"type": "Envelope", **suggested_extent},
            "extent": suggested_extent,
            "buffer_distance": {"value": 0, "unit": "miles"},
            "confidence": 0.92,
            "fallback_used": False,
            "warning": None,
            "summary": "Route extent + map padding",
        }

    key = str(geography or "").strip().lower()
    base_extent = _normalize_extent(KNOWN_GEOGRAPHY_EXTENTS.get(key))
    fallback_used = False
    warning = None
    if not base_extent:
        current_extent = _normalize_extent((preview_config or {}).get("focus_extent") or (preview_config or {}).get("initial_extent"))
        if current_extent:
            base_extent = current_extent
            fallback_used = True
            warning = "Requested boundary layer unavailable; using current preview extent as the AOI."
        else:
            base_extent = deepcopy(COUNTY_EXTENT)
            fallback_used = True
            warning = "Requested boundary layer unavailable; using Cabarrus County extent as a safe fallback."
    buffer_distance = _buffer_distance_for(recipe, geography_type)
    extent = _buffer_extent_miles(base_extent, buffer_distance)
    aoi_type = "county" if geography_type in {"county", "countywide"} or key in {"cabarrus county", "countywide"} else "municipality" if geography else "unknown"
    label = f"{geography or 'Cabarrus County'} boundary"
    if buffer_distance:
        label = f"{label} + {buffer_distance:g} mile buffer"
    return {
        "type": aoi_type,
        "geography_name": geography or "Cabarrus County",
        "source_layer": "verified_boundary_or_known_extent",
        "geometry": {"type": "Envelope", **extent},
        "extent": extent,
        "base_extent": base_extent,
        "buffer_distance": {"value": buffer_distance, "unit": "miles"},
        "confidence": 0.86 if fallback_used else 0.92,
        "fallback_used": fallback_used,
        "warning": warning,
        "summary": label,
    }


def _layer_blob(layer: dict[str, Any]) -> str:
    return " ".join(
        str(value or "").lower()
        for value in [
            layer.get("title"),
            layer.get("layer_key"),
            layer.get("layer_name"),
            layer.get("role"),
            layer.get("category"),
            layer.get("cartography_role"),
            layer.get("map_role"),
        ]
    )


def _layer_role(layer: dict[str, Any]) -> str:
    role = str(layer.get("map_role") or layer.get("cartography_role") or layer.get("role") or layer.get("category") or "").lower()
    blob = _layer_blob(layer)
    if "affected_parcels" in role or "affected_parcels" in blob or ("affected" in blob and "parcel" in blob):
        return "affected_parcels"
    if "commercial_zoning" in role or "commercial zoning" in blob:
        return "primary_polygon_highlight"
    if "zoning" in blob:
        return "context_polygon_muted"
    if "road" in blob or "street" in blob or "centerline" in blob:
        return "major_road" if "major" in blob else "road_context"
    if "municipal" in blob or "boundary" in blob or "district" in blob:
        return "boundary_outline"
    if "parcel" in blob:
        return "parcel_outline"
    if "flood" in blob:
        return "floodplain_overlay"
    return role or "context"


def _field_names(layer: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for field in layer.get("candidate_fields") or []:
        if field:
            names.append(str(field))
    for field in layer.get("fields") or layer.get("field_profiles") or []:
        if not isinstance(field, dict):
            continue
        name = field.get("name") or field.get("field_name")
        if name:
            names.append(str(name))
    return list(dict.fromkeys(names))


def _is_safe_major_road_text_field(field_name: str) -> bool:
    lowered = field_name.lower()
    if "id" in lowered or lowered in {"objectid", "fid", "oid"}:
        return False
    return any(token in lowered for token in ["route", "hwy", "highway", "road", "street", "name", "class", "functional", "type", "aadt"])


def major_road_definition_expression(layer: dict[str, Any]) -> str | None:
    """Return a conservative major-road filter only when route/name fields are known."""
    fields = _field_names(layer)
    if not fields:
        return None
    likely_fields = [
        field
        for field in fields
        if _is_safe_major_road_text_field(field)
    ]
    if not likely_fields:
        return None
    clauses: list[str] = []
    for field in likely_fields[:3]:
        upper_field = f"UPPER({field})"
        for token in MAJOR_ROUTE_TOKENS:
            clauses.append(f"{upper_field} LIKE '%{token.upper()}%'")
        if any(token in field.lower() for token in ["class", "functional", "type"]):
            clauses.extend([f"{upper_field} LIKE '%ARTERIAL%'", f"{upper_field} LIKE '%INTERSTATE%'", f"{upper_field} LIKE '%HIGHWAY%'"])
    return " OR ".join(dict.fromkeys(clauses)) if clauses else None


def request_wants_major_roads(recipe: dict[str, Any]) -> bool:
    text = _prompt_text(recipe)
    return "major road" in text or "high traffic" in text or any(term in text for term in ("highway", "arterial", "corridor"))


def _is_commercial_zoning_request(recipe: dict[str, Any]) -> bool:
    plan = recipe.get("request_plan") or {}
    parsed = recipe.get("parsed_request") or {}
    return (
        plan.get("request_type") == "zoning_context"
        and (
            plan.get("zoning_category") == "commercial"
            or "commercial" in (parsed.get("topic_details", {}).get("zoning_modifiers") or [])
        )
    )


def _visible(layer: dict[str, Any]) -> bool:
    if "visibility" in layer:
        return bool(layer.get("visibility"))
    if "default_visible" in layer:
        return bool(layer.get("default_visible"))
    return True


def _hide_layer(layer: dict[str, Any], reason: str) -> dict[str, Any]:
    item = deepcopy(layer)
    item["visibility"] = False
    item["default_visible"] = False
    item["visible_by_default"] = False
    item["map_role"] = "diagnostics_only"
    item["display_role"] = "diagnostics_only"
    item["diagnostics_only"] = True
    warnings = list(item.get("review_warnings") or [])
    if reason not in warnings:
        warnings.append(reason)
    item["review_warnings"] = warnings
    item["warning"] = reason
    return item


def _priority_for_layer(layer: dict[str, Any]) -> int:
    role = _layer_role(layer)
    priorities = {
        "primary_polygon_highlight": 1,
        "boundary_outline": 2,
        "major_road": 3,
        "road_context": 3,
        "floodplain_overlay": 4,
        "affected_parcels": 1,
        "context_polygon_muted": 5,
        "parcel_outline": 6,
    }
    return priorities.get(role, 8)


def _has_affected_result(recipe: dict[str, Any]) -> bool:
    if any(isinstance(overlay, dict) and overlay.get("role") == "affected_parcels" for overlay in recipe.get("derived_overlays") or []):
        return True
    execution = recipe.get("analysis_execution") if isinstance(recipe.get("analysis_execution"), dict) else {}
    try:
        return int(execution.get("output_count") or 0) > 0
    except (TypeError, ValueError):
        return False


def apply_aoi_to_layers(layers: list[dict[str, Any]], recipe: dict[str, Any], aoi: dict[str, Any]) -> list[dict[str, Any]]:
    """Attach AOI/role metadata and simplify visible layers for local maps."""
    local_aoi = aoi.get("type") not in {"county", "unknown"}
    request_type = str((recipe.get("request_plan") or {}).get("request_type") or recipe.get("request_type") or "")
    major_roads = request_wants_major_roads(recipe)
    commercial_request = _is_commercial_zoning_request(recipe)
    has_affected_result = _has_affected_result(recipe)
    parsed_topics = set((recipe.get("parsed_request") or {}).get("topics") or [])
    filter_plan = recipe.get("filter_plan") if isinstance(recipe.get("filter_plan"), dict) else {}
    has_primary_zoning_highlight = any(
        _visible(layer)
        and (
            _layer_role(layer) == "primary_polygon_highlight"
            or (commercial_request and _layer_role(layer) == "context_polygon_muted" and bool(layer.get("definition_expression")))
        )
        for layer in layers
    )
    prepared: list[dict[str, Any]] = []
    visible_role_counts: dict[str, int] = {}
    for layer in layers:
        item = deepcopy(layer)
        layer_key = item.get("layer_key")
        layer_plan = filter_plan.get(layer_key) if layer_key in filter_plan else None
        if isinstance(layer_plan, dict):
            if layer_plan.get("candidate_fields"):
                item.setdefault("candidate_fields", layer_plan.get("candidate_fields"))
            if layer_plan.get("selected_field"):
                item.setdefault("candidate_fields", [layer_plan["selected_field"], *(item.get("candidate_fields") or [])])
        role = _layer_role(item)
        if commercial_request and role == "context_polygon_muted" and item.get("definition_expression"):
            role = "primary_polygon_highlight"
            item["map_role"] = "primary_polygon_highlight"
            item["cartography_role"] = "commercial_zoning"
            item["title"] = "Commercial zoning"
            item["legend_label"] = "Commercial zoning"
        item["map_role"] = item.get("map_role") or role
        item["priority"] = item.get("priority") or _priority_for_layer(item)
        item["visible_by_default"] = _visible(item)
        item["clipped_to_aoi"] = bool(local_aoi or aoi.get("type") == "county")
        item["aoi_filter_applied"] = bool(local_aoi or aoi.get("type") == "county")
        item["aoi_summary"] = aoi.get("summary")
        item["aoi_extent"] = aoi.get("extent")
        item["max_feature_count"] = 250 if role in {"major_road", "road_context"} else 150 if "polygon" in role else 500
        item["simplification_applied"] = False
        item["aoi_filter_note"] = f"Layer bounded to {aoi.get('summary') or 'requested area'}."

        if role in {"major_road", "road_context"} and major_roads:
            expression = item.get("definition_expression") or major_road_definition_expression(item)
            if expression:
                item.update(cartography_for_role("roads", major_requested=True))
                item["definition_expression"] = expression
                item["major_road_filter_applied"] = True
                item["map_role"] = "major_road"
                item["cartography_role"] = "major_roads"
                item["title"] = "Major roads"
                item["legend_label"] = "Major roads"
            else:
                item.update(cartography_for_role("roads", major_requested=False))
                item["major_road_filter_applied"] = False
                item["map_role"] = "road_context"
                item["cartography_role"] = "roads"
                item["title"] = "Road context"
                item["legend_label"] = "Road context"
                warning = f"Major-road classification unavailable; showing road context clipped to {aoi.get('geography_name') or 'the requested area'}."
                warnings = list(item.get("review_warnings") or [])
                if warning not in warnings:
                    warnings.append(warning)
                item["review_warnings"] = warnings
                item["warning"] = warning

        if request_type == "zoning_context" and local_aoi:
            if role == "parcel_outline" and "parcel" not in parsed_topics:
                prepared.append(_hide_layer(item, "Full parcel layer hidden because this local zoning request did not ask for parcel outlines."))
                continue
            if role == "context_polygon_muted" and has_primary_zoning_highlight:
                hidden = _hide_layer(item, "Muted zoning context hidden because commercial zoning is already highlighted for the requested AOI.")
                hidden["simplification_applied"] = True
                prepared.append(hidden)
                continue
            if role in {"context", "table_only"}:
                prepared.append(_hide_layer(item, "Low-priority context layer hidden to reduce local map complexity."))
                continue
            if _visible(item):
                visible_role_counts[role] = visible_role_counts.get(role, 0) + 1
                if visible_role_counts[role] > (1 if role in {"major_road", "road_context", "boundary_outline"} else 2):
                    item["simplification_applied"] = True
                    prepared.append(_hide_layer(item, "Duplicate context layer hidden to keep the local map readable."))
                    continue
        if request_type == "floodplain_screening" and local_aoi:
            if role == "parcel_outline":
                reason = (
                    "Full parcel layer hidden because affected parcels are shown as the derived screening result."
                    if has_affected_result
                    else "Full parcel layer hidden because exact parcel-floodplain extraction is unavailable; showing floodplain context only."
                )
                prepared.append(_hide_layer(item, reason))
                continue
            if role in {"context_polygon_muted", "road_context", "major_road"}:
                reason = (
                    "Low-priority context layer hidden because this floodplain screening answers with affected parcels."
                    if has_affected_result
                    else "Low-priority context layer hidden so the floodplain context remains readable."
                )
                prepared.append(_hide_layer(item, reason))
                continue
        prepared.append(item)

    visible_layers = [item for item in prepared if _visible(item)]
    if request_type == "zoning_context" and local_aoi and len(visible_layers) > 4:
        keep_ids = {
            id(item)
            for item in sorted(visible_layers, key=lambda layer: int(layer.get("priority") or 99))[:4]
        }
        simplified: list[dict[str, Any]] = []
        for item in prepared:
            if _visible(item) and id(item) not in keep_ids:
                hidden = _hide_layer(item, "Layer hidden by visual complexity scoring; available in Diagnostics.")
                hidden["simplification_applied"] = True
                simplified.append(hidden)
            else:
                simplified.append(item)
        prepared = simplified
    return sorted(prepared, key=lambda layer: int(layer.get("priority") or 99))


def visual_complexity_score(layers: list[dict[str, Any]], aoi: dict[str, Any]) -> dict[str, Any]:
    visible_layers = [layer for layer in layers if _visible(layer)]
    polygon_layers = [layer for layer in visible_layers if _layer_role(layer) in {"primary_polygon_highlight", "context_polygon_muted", "parcel_outline", "affected_parcels", "floodplain_overlay"}]
    line_layers = [layer for layer in visible_layers if _layer_role(layer) in {"major_road", "road_context"}]
    unbounded = [layer for layer in visible_layers if not layer.get("clipped_to_aoi") and aoi.get("type") not in {"county", "unknown"}]
    score = len(visible_layers) * 8 + len(polygon_layers) * 10 + len(line_layers) * 8 + len(unbounded) * 30
    if any(float(layer.get("opacity") or 0) > 0.55 for layer in polygon_layers):
        score += 12
    status = "simple" if score < 45 else "moderate" if score < 75 else "complex"
    return {
        "score": score,
        "status": status,
        "visible_layer_count": len(visible_layers),
        "polygon_layer_count": len(polygon_layers),
        "line_layer_count": len(line_layers),
        "unbounded_visible_layer_count": len(unbounded),
        "simplified": any(layer.get("simplification_applied") for layer in layers),
    }


def apply_aoi_to_preview_config(preview_config: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    """Attach AOI metadata, constrain visible layer defaults, and set local extent."""
    config = deepcopy(preview_config)
    aoi = build_aoi_plan(recipe, config)
    for collection_key in ("context_layers", "operational_layers"):
        if isinstance(config.get(collection_key), list):
            config[collection_key] = apply_aoi_to_layers(config[collection_key], recipe, aoi)
    focus_mode = str(config.get("focus_mode") or recipe.get("focus_mode") or "")
    if aoi.get("extent") and focus_mode != "proximity" and aoi.get("type") != "unknown":
        config["initial_extent"] = aoi["extent"]
        config["focus_extent"] = aoi["extent"]
    config["aoi"] = aoi
    config["display_complexity"] = visual_complexity_score(config.get("context_layers") or config.get("operational_layers") or [], aoi)
    warnings = [str(item) for item in config.get("warnings") or [] if item]
    if aoi.get("warning"):
        warnings.append(str(aoi["warning"]))
    for layer in config.get("context_layers") or []:
        for warning in layer.get("review_warnings") or []:
            warnings.append(str(warning))
    config["warnings"] = sorted(set(warnings))
    return config
