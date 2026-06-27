"""Floodplain parcel screening helpers for composer previews.

This module turns a parcel + floodplain intent into a bounded derived result
layer. It reuses the existing analysis executor so parcel geometry is only
downloaded after server-side narrowing finds a safe affected parcel set.
"""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
from typing import Any

from app.automap_brain.cartography_engine import cartography_for_role
from app.geometry_utils import buffer_extent, geojson_extent
from app.spatial_query_client import SpatialQueryClient
from app.ui_models import output_file_url


FLOODPLAIN_SCREENING_WARNING = (
    "AutoMap found the parcel and floodplain layers, but could not complete the "
    "parcel-floodplain intersection. Showing floodplain context only."
)
LIVE_SCREENING_DISABLED_WARNING = (
    "Live parcel-floodplain intersection is not enabled for this deployment. "
    "Showing 100-year floodplain context only."
)


def live_floodplain_screening_enabled() -> bool:
    """Return whether production should run the slower exact intersection path."""
    return os.getenv("AUTOMAP_ENABLE_LIVE_FLOODPLAIN_SCREENING", "").strip().lower() in {"1", "true", "yes"}


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


def _derived_overlay(result: dict[str, Any], extent: dict[str, Any] | None) -> dict[str, Any] | None:
    path = result.get("output_geojson_path")
    if not path:
        return None
    style = cartography_for_role("affected_parcels")
    return {
        "id": f"affected_floodplain_parcels_{result.get('analysis_run_id') or 'analysis'}",
        "title": "Parcels in 100-year floodplain",
        "type": "geojson",
        "url": output_file_url(path),
        "path": path,
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
        "feature_count": int(result.get("output_count") or 0),
        "extent": extent,
        "legend_label": "Parcels in 100-year floodplain",
        "analysis_type": "floodplain_parcel_screening",
        "floodplain_type": "100_year",
    }


def _derived_output(result: dict[str, Any], extent: dict[str, Any] | None) -> dict[str, Any] | None:
    path = result.get("output_geojson_path")
    if not path:
        return None
    return {
        "type": "floodplain_affected_parcels_geojson",
        "path": path,
        "url": output_file_url(path),
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
            "map_role": "affected_parcels",
            "cartography_role": "affected_parcels",
            "opacity": 0.84,
        },
    }


def _geojson_extent_from_result(path: str | Path) -> dict[str, Any] | None:
    source = Path(path)
    candidates = [source]
    if not source.is_absolute():
        try:
            from app.analysis_executor import repo_root as analysis_repo_root

            candidates.append(analysis_repo_root() / source)
        except Exception:
            pass
    for candidate in candidates:
        if candidate.exists():
            return geojson_extent(candidate)
    return geojson_extent(source)


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
    max_features: int = 1000,
) -> dict[str, Any]:
    """Execute and attach a bounded affected-parcels layer when appropriate."""
    next_recipe = deepcopy(recipe)
    if not is_floodplain_screening_recipe(next_recipe):
        return next_recipe

    next_recipe["request_type"] = "floodplain_screening"
    plan = next_recipe.setdefault("request_plan", {})
    plan["request_type"] = "floodplain_screening"
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
            query_client=query_client or SpatialQueryClient(max_features=max_features, timeout=2),
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
        extent = buffer_extent(_geojson_extent_from_result(result["output_geojson_path"]), ratio=0.12, minimum=0.003)
        derived_output = _derived_output(result, extent)
        overlay = _derived_overlay(result, extent)
        if derived_output:
            outputs = next_recipe.setdefault("analysis_execution", {}).setdefault("derived_outputs", [])
            outputs[:] = [
                item
                for item in outputs
                if not (isinstance(item, dict) and item.get("type") == "floodplain_affected_parcels_geojson")
            ]
            outputs.append(derived_output)
        if overlay:
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
            }
        )
        if extent:
            next_recipe["suggested_extent"] = extent
        next_recipe["focus_mode"] = "floodplain_screening"
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
