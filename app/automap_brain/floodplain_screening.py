"""Floodplain parcel screening helpers for composer previews.

This module turns a parcel + floodplain intent into a bounded derived result
layer. It reuses the existing analysis executor so parcel geometry is only
downloaded after server-side narrowing finds a safe affected parcel set.
"""

from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any

from app.automap_brain.cartography_engine import cartography_for_role, display_mode_for_role, map_purpose_for_recipe
from app.analysis_models import HARD_MAX_FEATURES
from app.geometry_utils import buffer_extent, geojson_extent, make_generalized_display_geojson
from app.spatial_query_client import SpatialQueryClient
from app.ui_models import output_file_url


FLOODPLAIN_SCREENING_WARNING = (
    "AutoMap found the parcel and floodplain layers, but could not complete the "
    "parcel-floodplain intersection. Showing floodplain context only."
)
LIVE_SCREENING_DISABLED_WARNING = (
    "Live parcel-floodplain intersection is disabled for this deployment. "
    "Showing 100-year floodplain context only."
)


def live_floodplain_screening_enabled() -> bool:
    """Return whether production should run the bounded exact intersection path."""
    disabled = os.getenv("AUTOMAP_DISABLE_LIVE_FLOODPLAIN_SCREENING", "").strip().lower()
    if disabled in {"1", "true", "yes", "on"}:
        return False
    enabled = os.getenv("AUTOMAP_ENABLE_LIVE_FLOODPLAIN_SCREENING", "").strip().lower()
    if enabled in {"0", "false", "no", "off"}:
        return False
    return True


def is_floodplain_screening_recipe(recipe: dict[str, Any]) -> bool:
    plan = recipe.get("request_plan") or {}
    return str(plan.get("request_type") or recipe.get("request_type") or "") == "floodplain_screening"


def _floodplain_type(recipe: dict[str, Any]) -> str:
    plan = recipe.get("request_plan") or {}
    parsed = recipe.get("parsed_request") or {}
    for item in plan.get("filters") or []:
        if isinstance(item, dict) and item.get("domain") == "floodplain" and item.get("value"):
            return str(item["value"])
    return str((parsed.get("topic_details") or {}).get("flood_frequency") or "100_year")


def _aoi_name(recipe: dict[str, Any]) -> str:
    plan = recipe.get("request_plan") or {}
    params = plan.get("parameters") if isinstance(plan.get("parameters"), dict) else {}
    return str(plan.get("geography") or params.get("geography") or "Cabarrus County")


def _aoi_type(recipe: dict[str, Any]) -> str:
    plan = recipe.get("request_plan") or {}
    return str(plan.get("geography_type") or ("municipality" if _aoi_name(recipe) != "Cabarrus County" else "county"))


def _append_unique(values: list[str], value: str) -> list[str]:
    if value and value not in values:
        values.append(value)
    return values


def _resolve_output_path(path: str | Path) -> Path:
    source = Path(path)
    if source.is_absolute():
        return source
    try:
        from app.analysis_executor import repo_root as analysis_repo_root

        return analysis_repo_root() / source
    except Exception:
        return source


def _display_path_value(path: str | Path) -> str:
    source = Path(path)
    return str(source.with_name(f"{source.stem}_display{source.suffix or '.geojson'}"))


def _display_metadata(result: dict[str, Any]) -> dict[str, Any]:
    path = result.get("output_geojson_path")
    feature_count = int(result.get("output_count") or 0)
    mode = display_mode_for_role(
        "affected_parcels",
        feature_count=feature_count,
        geometry_type="polygon",
        focus_mode="result_focused_with_aoi_context",
    )
    metadata = {
        **mode,
        "analysis_geojson_path": path,
        "display_geojson_path": path,
        "path": path,
        "display_generalized": False,
        "display_feature_count": feature_count,
    }
    if not path or mode.get("display_mode") != "dissolved_result_area":
        return metadata
    display_value = _display_path_value(path)
    try:
        display_path = _resolve_output_path(display_value)
        display_path.parent.mkdir(parents=True, exist_ok=True)
        display_geojson = make_generalized_display_geojson(
            _resolve_output_path(path),
            max_features=HARD_MAX_FEATURES,
            name="Parcels in 100-year floodplain display",
            display_mode=str(mode["display_mode"]),
            simplify_tolerance=float(mode.get("simplification_tolerance") or 0),
        )
        display_path.write_text(json.dumps(display_geojson, separators=(",", ":")), encoding="utf-8")
        metadata.update(
            {
                "path": display_value,
                "display_geojson_path": display_value,
                "display_generalized": True,
                "display_feature_count": len(display_geojson.get("features") or []),
            }
        )
    except Exception as exc:
        metadata.update(
            {
                "display_mode": "simplified_features",
                "display_generalized": False,
                "diagnostic_note": f"Display generalization unavailable; using thin affected parcel outlines. {exc.__class__.__name__}",
            }
        )
    return metadata


def _feature_collection_from_path(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    try:
        data = json.loads(_resolve_output_path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) and data.get("type") == "FeatureCollection" and isinstance(data.get("features"), list) else None


def _derived_overlay(
    result: dict[str, Any],
    extent: dict[str, Any] | None,
    display: dict[str, Any] | None = None,
    recipe: dict[str, Any] | None = None,
    feature_collection: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    display = display or _display_metadata(result)
    path = display.get("path") or result.get("output_geojson_path")
    if not path:
        return None
    feature_collection = feature_collection or _feature_collection_from_path(path)
    if not feature_collection:
        return None
    style = cartography_for_role("affected_parcels", map_purpose=map_purpose_for_recipe(recipe or {}))
    return {
        "id": f"affected_floodplain_parcels_{result.get('analysis_run_id') or 'analysis'}",
        "title": "Parcels in 100-year floodplain",
        "source_kind": "derived_feature_collection",
        "kind": "derived_overlay",
        "layer_type": "graphics_overlay",
        "type": "geojson",
        "path": path,
        "geojson": feature_collection,
        "feature_collection": feature_collection,
        "analysis_geojson_path": display.get("analysis_geojson_path") or result.get("output_geojson_path"),
        "display_geojson_path": display.get("display_geojson_path") or path,
        "role": "affected_parcels",
        "geometry_role": "affected_parcels",
        "symbol_key": "affected_floodplain_parcel",
        "visible": True,
        "default_visible": True,
        "local_output": True,
        "source_status": "derived_local",
        "map_role": style["map_role"],
        "cartography_role": style["cartography_role"],
        "opacity": style["opacity"],
        "drawing_info": style["drawing_info"],
        "draw_order": style.get("draw_order"),
        "relationship_role": style.get("relationship_role"),
        "compositing_mode": style.get("compositing_mode"),
        "min_stroke_width": style.get("min_stroke_width"),
        "scale_behavior": style.get("scale_behavior"),
        "feature_count": int(result.get("output_count") or 0),
        "display_feature_count": int(display.get("display_feature_count") or result.get("output_count") or 0),
        "display_mode": display.get("display_mode"),
        "display_generalized": bool(display.get("display_generalized")),
        "simplification_applied": bool(display.get("display_generalized")),
        "visual_density_score": display.get("visual_density_score"),
        "diagnostic_note": display.get("diagnostic_note"),
        "extent": extent,
        "legend_label": "Parcels in 100-year floodplain",
        "analysis_type": "floodplain_parcel_screening",
        "floodplain_type": "100_year",
    }


def _derived_output(
    result: dict[str, Any],
    extent: dict[str, Any] | None,
    display: dict[str, Any] | None = None,
    recipe: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    display = display or _display_metadata(result)
    path = result.get("output_geojson_path")
    if not path:
        return None
    style = cartography_for_role("affected_parcels", map_purpose=map_purpose_for_recipe(recipe or {}))
    return {
        "type": "floodplain_affected_parcels_geojson",
        "path": path,
        "url": output_file_url(path),
        "display_path": display.get("display_geojson_path") or path,
        "display_url": output_file_url(display.get("display_geojson_path") or path),
        "display_mode": display.get("display_mode"),
        "display_generalized": bool(display.get("display_generalized")),
        "display_feature_count": int(display.get("display_feature_count") or result.get("output_count") or 0),
        "diagnostic_note": display.get("diagnostic_note"),
        "title": "Parcels in 100-year floodplain",
        "layer_key": f"affected_floodplain_parcels_{result.get('analysis_run_id') or 'analysis'}",
        "role": "affected_parcels",
        "geometry_role": "affected_parcels",
        "symbol_key": "affected_floodplain_parcel",
        "analysis_run_id": result.get("analysis_run_id"),
        "feature_count": int(result.get("output_count") or 0),
        "extent": extent,
        "derived_layer": {
            "title": "Parcels in 100-year floodplain",
            "layer_key": f"affected_floodplain_parcels_{result.get('analysis_run_id') or 'analysis'}",
            "role": "affected_parcels",
            "map_role": style["map_role"],
            "cartography_role": style["cartography_role"],
            "opacity": style["opacity"],
            "drawing_info": style["drawing_info"],
            "draw_order": style.get("draw_order"),
            "relationship_role": style.get("relationship_role"),
            "display_mode": display.get("display_mode"),
        },
    }


def _geojson_extent_from_result(path: str | Path) -> dict[str, Any] | None:
    source = _resolve_output_path(path)
    if source.exists():
        return geojson_extent(source)
    return geojson_extent(path)


def _screening_summary(
    recipe: dict[str, Any],
    *,
    status: str,
    affected_count: int = 0,
    extent: dict[str, Any] | None = None,
    warning: str | None = None,
    analysis_run_id: str | None = None,
) -> dict[str, Any]:
    floodplain_type = _floodplain_type(recipe)
    aoi_name = _aoi_name(recipe)
    aoi_type = _aoi_type(recipe)
    return {
        "analysis_type": "floodplain_parcel_screening",
        "status": status,
        "spatial_relationship": "intersects",
        "result_layer_role": "affected_parcels",
        "affected_feature_count": affected_count,
        "floodplain_type": floodplain_type,
        "aoi_name": aoi_name,
        "aoi_type": aoi_type,
        "analysis_run_id": analysis_run_id,
        "result_extent": extent,
        "summary_label": "Parcels intersecting the 100-year floodplain",
        "draft_note": "Draft screening only. Not an official flood determination.",
        "warning": warning,
    }


def attach_floodplain_screening_result(
    recipe: dict[str, Any],
    *,
    catalog_records: list[dict[str, Any]] | None = None,
    query_client: Any | None = None,
    max_features: int = HARD_MAX_FEATURES,
) -> dict[str, Any]:
    """Execute and attach a bounded affected-parcels layer when appropriate."""
    next_recipe = deepcopy(recipe)
    if not is_floodplain_screening_recipe(next_recipe):
        return next_recipe

    next_recipe["request_type"] = "floodplain_screening"
    next_recipe["map_purpose"] = "relationship_overlay"
    next_recipe["relationship_type"] = "target_intersects_constraint"
    plan = next_recipe.setdefault("request_plan", {})
    plan["request_type"] = "floodplain_screening"
    plan["map_purpose"] = "relationship_overlay"
    plan["relationship_type"] = "target_intersects_constraint"
    plan["primary_domain"] = "parcels"
    secondary_domains = list(plan.get("secondary_domains") or [])
    if "floodplain" not in secondary_domains:
        secondary_domains.append("floodplain")
    plan["secondary_domains"] = secondary_domains
    plan["spatial_relationships"] = ["intersects" if item == "intersecting" else item for item in (plan.get("spatial_relationships") or ["intersects"])]
    plan["floodplain_type"] = _floodplain_type(next_recipe)
    plan["constraint_domain"] = "floodplain"
    plan["result_layer"] = "affected_parcels"
    params = plan.setdefault("parameters", {})
    if isinstance(params, dict):
        params["spatial_relationship"] = "intersects"
        params["floodplain_type"] = plan["floodplain_type"]
        params["result_layer"] = "affected_parcels"

    if query_client is None and not live_floodplain_screening_enabled():
        warning = LIVE_SCREENING_DISABLED_WARNING
        next_recipe.setdefault("review_reasons", [])
        _append_unique(next_recipe["review_reasons"], warning)
        next_recipe["needs_review"] = True
        next_recipe["floodplain_screening"] = _screening_summary(next_recipe, status="partial_context_only", warning=warning)
        next_recipe.setdefault("analysis_execution", {}).update(
            {
                "analysis_status": "partial_context_only",
                "operation_type": "floodplain_parcel_screening",
                "blocked_reasons": [warning],
                "derived_outputs": [],
                "output_count": 0,
                "live_intersection_enabled": False,
            }
        )
        return next_recipe

    try:
        from app.analysis_executor import execute_analysis

        analysis_catalog = catalog_records if catalog_records is not None else [dict(layer) for layer in next_recipe.get("selected_layers") or []]
        result = execute_analysis(
            next_recipe,
            catalog_records=analysis_catalog,
            query_client=query_client or SpatialQueryClient(max_features=max_features, timeout=30),
            max_features=max_features,
            estimate_counts=False,
        )
    except Exception as exc:  # pragma: no cover - production safety fallback
        warning = FLOODPLAIN_SCREENING_WARNING
        next_recipe.setdefault("review_reasons", [])
        _append_unique(next_recipe["review_reasons"], warning)
        next_recipe["needs_review"] = True
        next_recipe["floodplain_screening"] = _screening_summary(next_recipe, status="partial_context_only", warning=warning)
        next_recipe.setdefault("analysis_execution", {}).update(
            {
                "analysis_status": "partial_context_only",
                "operation_type": "floodplain_parcel_screening",
                "error_category": exc.__class__.__name__,
                "derived_outputs": [],
                "output_count": 0,
            }
        )
        return next_recipe

    output_count = int(result.get("output_count") or 0)
    if result.get("status") == "completed" and output_count > 0 and result.get("output_geojson_path"):
        display = _display_metadata(result)
        feature_collection = _feature_collection_from_path(display.get("path") or result["output_geojson_path"])
        if not feature_collection:
            warning = "Affected parcel display geometry unavailable; showing 100-year floodplain context only."
            next_recipe.setdefault("review_reasons", [])
            _append_unique(next_recipe["review_reasons"], warning)
            next_recipe["needs_review"] = True
            next_recipe["floodplain_screening"] = _screening_summary(next_recipe, status="partial_context_only", warning=warning)
            next_recipe.setdefault("analysis_execution", {}).update(
                {
                    "analysis_status": "partial_context_only",
                    "operation_type": "floodplain_parcel_screening",
                    "blocked_reasons": [warning],
                    "derived_outputs": [],
                    "output_count": 0,
                }
            )
            return next_recipe
        extent = buffer_extent(_geojson_extent_from_result(result["output_geojson_path"]), ratio=0.06, minimum=0.002)
        derived_output = _derived_output(result, extent, display, next_recipe)
        overlay = _derived_overlay(result, extent, display, next_recipe, feature_collection=feature_collection)
        if derived_output:
            outputs = next_recipe.setdefault("analysis_execution", {}).setdefault("derived_outputs", [])
            outputs[:] = [
                item
                for item in outputs
                if not (isinstance(item, dict) and item.get("type") == "floodplain_affected_parcels_geojson")
            ]
            outputs.append(derived_output)
        overlays = next_recipe.setdefault("derived_overlays", [])
        overlays[:] = [
            item
            for item in overlays
            if not (isinstance(item, dict) and item.get("role") == "affected_parcels")
        ]
        overlays.append(overlay)
        next_recipe["floodplain_screening"] = _screening_summary(
            next_recipe,
            status="completed",
            affected_count=output_count,
            extent=extent,
            analysis_run_id=result.get("analysis_run_id"),
        )
        next_recipe["analysis_execution"].update(
            {
                "analysis_run_id": result.get("analysis_run_id"),
                "analysis_status": "completed",
                "operation_type": "floodplain_parcel_screening",
                "output_count": output_count,
                "result_layer_role": "affected_parcels",
                "display_mode": display.get("display_mode"),
                "display_generalized": bool(display.get("display_generalized")),
                "display_feature_count": int(display.get("display_feature_count") or output_count),
            }
        )
        if extent:
            next_recipe["suggested_extent"] = extent
        next_recipe["focus_mode"] = "result_focused_with_aoi_context"
        next_recipe["preview_status"] = "ready_for_floodplain_screening_preview"
        return next_recipe

    if output_count == 0 and result.get("status") == "completed":
        warning = "No parcels in the requested area intersected the selected 100-year floodplain layer."
        status = "no_matches"
    else:
        blocked = "; ".join(str(item) for item in result.get("blocked_reasons") or [] if item)
        warning = f"{FLOODPLAIN_SCREENING_WARNING}{f' {blocked}' if blocked else ''}"
        status = "partial_context_only"
    next_recipe.setdefault("review_reasons", [])
    _append_unique(next_recipe["review_reasons"], warning)
    next_recipe["needs_review"] = True
    next_recipe["floodplain_screening"] = _screening_summary(next_recipe, status=status, warning=warning)
    next_recipe.setdefault("analysis_execution", {}).update(
        {
            "analysis_status": "no_matching_parcels" if status == "no_matches" else "partial_context_only",
            "operation_type": "floodplain_parcel_screening",
            "blocked_reasons": result.get("blocked_reasons") or [warning],
            "derived_outputs": [],
            "output_count": 0,
        }
    )
    return next_recipe
