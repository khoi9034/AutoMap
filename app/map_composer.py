"""Simple prompt-to-preview composer workflow for AutoMap."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import csv
import json
import logging
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

from app.adjustment_engine import apply_adjustments_to_recipe, apply_adjustments_to_webmap, write_adjusted_packet
from app.adjustment_models import normalize_adjustments
from app.address_parcel_resolver import ADDRESS_NOT_MATCHED_WARNING, resolve_address_or_parcel_origin
from app.automap_brain.cartography_engine import (
    apply_visible_qa_fallbacks as brain_apply_visible_qa_fallbacks,
    cartography_for_role as brain_cartography_for_role,
    context_draw_rank as brain_context_draw_rank,
    style_context_layer as brain_style_context_layer,
)
from app.automap_brain.aoi_planner import apply_aoi_to_preview_config
from app.automap_brain.explain_plan import build_brain_explanation
from app.automap_brain.floodplain_screening import (
    LIVE_SCREENING_DISABLED_WARNING,
    attach_floodplain_screening_result,
    live_floodplain_screening_enabled,
)
from app.automap_brain.request_parser import build_brain_plan
from app.automap_brain.visible_map_qa import run_visible_map_qa
from app.ai.map_planner import plan_with_ai
from app.composer_state_models import (
    default_north_arrow_config,
    default_scale_bar_config,
    normalize_export_options,
    report_config_for_export_mode,
    utc_timestamp,
)
from app.composer_state_store import get_composer_map_state, upsert_composer_map_state
from app.geometry_utils import buffer_extent, geojson_extent
from app.map_title_generator import (
    display_origin_label as _display_origin_label,
    generate_map_title,
    map_layout_subtitle as _map_layout_subtitle,
    route_mode_label as _route_mode_label,
    target_display_label as _target_display_label,
)
from app.packet_index import build_preview_config
from app.prompt_parser import parse_prompt
from app.recipe_engine import PARCEL_NOT_MATCHED_WARNING, build_recipe
from app.report_generator import generate_report
from app.report_section_models import build_report_sections
from app.report_statistics_builder import build_report_statistics
from app.table_request_classifier import classify_table_request
from app.table_query_engine import plan_table_query, preview_table_rows
from app.review_packet_builder import (
    build_layer_review_table,
    build_review_summary,
    build_warning_report,
    save_review_packet,
)
from app.ui_models import output_file_url, repo_root
from app.webmap_builder import build_webmap_json
from app.proximity_engine import build_proximity_context, run_proximity_request


COMPOSER_ROOT = Path("outputs/composer_sessions")
LOGGER = logging.getLogger(__name__)
visible_map_qa = run_visible_map_qa

COMPOSER_TIMING_KEYS = [
    "parse_ms",
    "intelligence_ms",
    "recipe_ms",
    "address_match_ms",
    "parcel_resolve_ms",
    "nearest_facility_ms",
    "route_mode_ms",
    "route_generation_ms",
    "geojson_write_ms",
    "floodplain_screening_ms",
    "preview_config_ms",
    "review_packet_ms",
    "composer_state_ms",
]


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def _new_composer_timing() -> dict[str, Any]:
    return {key: 0 for key in COMPOSER_TIMING_KEYS}


def _planner_response_fields(planner_context: dict[str, Any] | None) -> dict[str, Any]:
    context = planner_context or {}
    return {
        "planner_used": context.get("planner_used") or "deterministic",
        "ai_status": context.get("ai_status"),
        "ai_confidence": context.get("ai_confidence"),
        "ai_error_category": context.get("ai_error_category"),
        "ai_error_code": context.get("ai_error_code"),
        "ai_error_type": context.get("ai_error_type"),
        "ai_error_message_safe": context.get("ai_error_message_safe"),
        "ai_model_used": context.get("ai_model_used"),
        "map_plan_summary": context.get("map_plan_summary"),
    }


def _finalize_composer_timing(timing: dict[str, Any], started_at: float) -> dict[str, Any]:
    for key in COMPOSER_TIMING_KEYS:
        timing.setdefault(key, 0)
    timing["total_ms"] = _elapsed_ms(started_at)
    timing["slow_steps"] = [
        key
        for key, value in timing.items()
        if key != "total_ms" and key.endswith("_ms") and isinstance(value, (int, float)) and value >= 5000
    ]
    return timing


def _merge_proximity_timing(timing: dict[str, Any], proximity_result: dict[str, Any] | None) -> None:
    proximity_timing = (proximity_result or {}).get("proximity_timing") or {}
    for source_key, target_key in [
        ("address_match_ms", "address_match_ms"),
        ("parcel_resolve_ms", "parcel_resolve_ms"),
        ("nearest_facility_ms", "nearest_facility_ms"),
        ("route_generation_ms", "route_generation_ms"),
        ("geojson_write_ms", "geojson_write_ms"),
    ]:
        value = proximity_timing.get(source_key)
        if isinstance(value, (int, float)):
            timing[target_key] = int(value)


def _attach_timing(response: dict[str, Any], timing: dict[str, Any], started_at: float) -> dict[str, Any]:
    finalized = _finalize_composer_timing(timing, started_at)
    response["composer_timing"] = finalized
    response.setdefault("debug_details", {})["composer_timing"] = finalized
    LOGGER.info("composer generate timing session=%s timing=%s", response.get("composer_session_id"), finalized)
    return response


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _session_root() -> Path:
    root = repo_root() / COMPOSER_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_path(session_id: str) -> Path:
    if not session_id.startswith("composer_"):
        raise ValueError("Invalid composer session id.")
    path = (_session_root() / session_id).resolve()
    try:
        path.relative_to(_session_root().resolve())
    except ValueError as exc:
        raise ValueError("Composer session path must stay inside AutoMap outputs.") from exc
    return path


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_relative(path: str | Path | None) -> str | None:
    if not path:
        return None
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _local_output_path(path: str | Path | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return repo_root() / candidate


def _file_link(path: str | Path, name: str | None = None) -> dict[str, str]:
    relative = _repo_relative(path) or Path(path).as_posix()
    return {"name": name or Path(path).name, "path": relative, "url": output_file_url(relative)}


def _selected_layers(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "layer_key": layer.get("layer_key"),
            "layer_name": layer.get("layer_name"),
            "category": layer.get("category"),
            "role": layer.get("role"),
            "source_status": layer.get("source_status"),
            "source_role": layer.get("source_role"),
            "confidence_score": layer.get("confidence_score"),
            "layer_url": layer.get("layer_url"),
        }
        for layer in recipe.get("selected_layers") or []
    ]


def _review_warnings(recipe: dict[str, Any], parcel_context: dict[str, Any]) -> list[str]:
    origin_context = recipe.get("origin_context") or {}
    proximity_result = recipe.get("proximity_result") or {}
    warnings = [
        *[str(item) for item in recipe.get("review_reasons") or [] if item],
        *[str(item) for item in parcel_context.get("parcel_warnings") or [] if item],
        *[str(item) for item in origin_context.get("warnings") or [] if item],
        *[str(item) for item in proximity_result.get("warnings") or [] if item],
    ]
    return sorted({warning for warning in warnings if warning})


def _preview_blockers(recipe: dict[str, Any]) -> list[str]:
    parcel_context = recipe.get("parcel_context") or {}
    if parcel_context and parcel_context.get("can_focus_map") is False:
        return [parcel_context.get("reason_if_not_focusable") or PARCEL_NOT_MATCHED_WARNING]
    origin_context = recipe.get("origin_context") or {}
    if origin_context and origin_context.get("can_preview") is False:
        origin_type = str(origin_context.get("origin_type") or "origin")
        fallback = ADDRESS_NOT_MATCHED_WARNING if origin_type == "address" else "Origin not matched. AutoMap cannot preview this focused map until the origin is matched."
        return [origin_context.get("reason_if_not_focusable") or fallback]
    primary_blocker = _primary_result_blocker(recipe)
    if primary_blocker:
        return [primary_blocker]
    validation = recipe.get("validation") or {}
    return [str(item) for item in validation.get("errors") or [] if item]


def _primary_result_blocker(recipe: dict[str, Any]) -> str | None:
    screening = recipe.get("floodplain_screening") if isinstance(recipe.get("floodplain_screening"), dict) else None
    if not screening:
        return None
    status = str(screening.get("status") or "")
    affected_count = int(screening.get("affected_feature_count") or 0)
    if status == "completed" and affected_count > 0:
        return None
    if status == "no_matches":
        return None
    return str(
        screening.get("warning")
        or "AutoMap found the Concord boundary and 100-year floodplain, but could not complete the parcel intersection."
    )


def _result_state(recipe: dict[str, Any], can_preview: bool, blockers: list[str]) -> str:
    screening = recipe.get("floodplain_screening") if isinstance(recipe.get("floodplain_screening"), dict) else None
    if screening:
        status = str(screening.get("status") or "")
        affected_count = int(screening.get("affected_feature_count") or 0)
        if status == "completed" and affected_count > 0:
            return "ready"
        if status == "no_matches":
            return "no_matches"
        return "partial"
    origin_context = recipe.get("origin_context") or {}
    parcel_context = recipe.get("parcel_context") or {}
    if origin_context.get("origin_match_status") == "unsupported_area" or parcel_context.get("match_status") == "unsupported_area":
        return "unsupported"
    if blockers:
        return "blocked"
    return "ready" if can_preview else "blocked"


def _result_truth_summary(recipe: dict[str, Any], result_state: str) -> dict[str, Any]:
    screening = recipe.get("floodplain_screening") if isinstance(recipe.get("floodplain_screening"), dict) else None
    if not screening:
        return {}
    context = ["100-year floodplain", f"{screening.get('aoi_name') or 'Concord'} boundary"]
    context_map_available = result_state in {"partial", "no_matches"} and bool(context)
    return {
        "requested_result": "Parcels in 100-year floodplain",
        "available_context": context if result_state in {"partial", "no_matches"} else [],
        "missing_operation": "Parcel-floodplain intersection" if result_state == "partial" else None,
        "primary_result_role": "affected_parcels" if result_state == "ready" else None,
        "context_map_available": context_map_available,
        "primary_result_available": result_state == "ready",
        "requested_result_missing": result_state == "partial",
    }


def _can_preview(recipe: dict[str, Any], webmap_json: dict[str, Any]) -> bool:
    if _preview_blockers(recipe):
        return False
    validation = webmap_json.get("autoMapValidation") or {}
    derived_outputs = (recipe.get("analysis_execution") or {}).get("derived_outputs") or []
    return bool(recipe.get("selected_layers") or derived_outputs) and not bool(validation.get("errors"))


def _can_analyze(recipe: dict[str, Any]) -> bool:
    if recipe.get("parcel_context"):
        return False
    analysis = recipe.get("analysis_execution") or {}
    return bool(analysis.get("executable"))


def _next_action(can_preview: bool, blockers: list[str], result_state: str = "") -> str:
    if result_state == "partial":
        return "context_preview"
    if result_state == "no_matches":
        return "review_recipe"
    if blockers:
        lowered = " ".join(blockers).lower()
        if "address" in lowered:
            return "correct_address"
        if "parcel" in lowered:
            return "correct_parcel_identifier"
        return "review_blockers"
    return "preview_map" if can_preview else "review_recipe"


def _is_proximity_prompt(prompt: str) -> bool:
    context = build_proximity_context(prompt)
    return bool(context.get("proximity_detected"))


def _append_unique_warning(recipe: dict[str, Any], warning: str) -> None:
    if not warning:
        return
    reasons = list(recipe.get("review_reasons") or [])
    if warning not in reasons:
        reasons.append(warning)
    recipe["review_reasons"] = reasons
    recipe["needs_review"] = True


def _target_layer_as_selected(target_layer: dict[str, Any]) -> dict[str, Any]:
    return {
        **target_layer,
        "role": "nearest_facility_target",
        "source_role": target_layer.get("source_role") or "official_context",
        "confidence_score": 0.9,
        "match_score": 140,
        "match_reasons": ["selected as nearest-facility target layer"],
        "why_selected": "Selected from the verified catalog for the requested nearest-facility search.",
        "review_notes": ["Review nearest-facility target layer coverage before official use."],
    }


def _extent_from_proximity_result(result: dict[str, Any]) -> dict[str, Any] | None:
    path = result.get("line_geojson_path")
    if not path:
        return None
    local_path = _local_output_path(path)
    if local_path and local_path.exists():
        return buffer_extent(geojson_extent(local_path), ratio=0.3, minimum=0.004)
    return None


def _origin_context_from_proximity(prompt: str, result: dict[str, Any]) -> dict[str, Any]:
    origin_type = result.get("origin_type") or resolve_address_or_parcel_origin(prompt, match=False).get("origin_type") or "unknown"
    status = "matched" if result.get("status") == "ok" else "needs_review"
    reason = None
    if result.get("status") != "ok":
        reason = ADDRESS_NOT_MATCHED_WARNING if origin_type == "address" else "Origin not matched. AutoMap cannot preview this focused map until the origin is matched."
    related_parcel = None
    parcel_set = result.get("parcel_set")
    if isinstance(parcel_set, dict) and parcel_set.get("matched_parcels"):
        related_parcel = parcel_set.get("matched_parcels", [None])[0]
    return {
        "origin_type": origin_type,
        "origin_input": result.get("origin_input"),
        "origin_match_status": result.get("origin_match_status") or status,
        "match_status": result.get("origin_match_status") or status,
        "candidate_matches": result.get("candidate_matches") or [],
        "related_parcel": related_parcel,
        "property_match_status": result.get("property_match_status")
        or ("not_resolved" if origin_type == "address" and status == "matched" and not related_parcel else None),
        "can_preview": result.get("status") == "ok",
        "reason_if_not_focusable": reason,
        "warnings": result.get("warnings") or [],
        "supported_area": result.get("supported_area"),
    }


def _proximity_map_title(result: dict[str, Any]) -> str:
    return generate_map_title("", proximity_result=result)


def _legend_label_for_overlay(overlay: dict[str, Any]) -> str:
    role = str(overlay.get("role") or overlay.get("geometry_role") or "").lower()
    symbol_key = str(overlay.get("symbol_key") or "")
    route_label = overlay.get("route_label")
    if overlay.get("legend_label"):
        return str(overlay["legend_label"])
    if "affected" in role and "parcel" in role:
        return "Parcels in 100-year floodplain"
    if "origin" in role:
        return "Origin Address"
    if "target" in role:
        facility_type = str(overlay.get("facility_type") or "")
        if "fire" in facility_type:
            return "Nearest Fire Station"
        if "school" in facility_type:
            return "Nearest School"
        if "library" in facility_type:
            return "Nearest Library"
        return "Nearest Facility"
    if "distance" in role or "route" in symbol_key:
        return str(route_label or "Route Draft")
    if "parcel" in role or symbol_key == "selected_parcel":
        return "Selected Parcel"
    return str(overlay.get("title") or overlay.get("id") or "Map overlay")


def _legend_symbol_fields(drawing_info: Any) -> dict[str, Any]:
    renderer = drawing_info.get("renderer") if isinstance(drawing_info, dict) else {}
    symbol = renderer.get("symbol") if isinstance(renderer, dict) else {}
    if not isinstance(symbol, dict):
        return {}
    outline = symbol.get("outline") if isinstance(symbol.get("outline"), dict) else {}
    def alpha(color: Any) -> float | None:
        if not isinstance(color, list) or len(color) < 4:
            return None
        try:
            value = float(color[3])
        except (TypeError, ValueError):
            return None
        return round(value / 255, 3) if value > 1 else round(value, 3)
    if symbol.get("type") == "esriSLS":
        return {
            "line_color": symbol.get("color"),
            "line_opacity": alpha(symbol.get("color")),
            "line_style": symbol.get("style"),
            "line_width": symbol.get("width"),
        }
    return {
        "fill_color": symbol.get("color"),
        "fill_opacity": alpha(symbol.get("color")),
        "outline_color": outline.get("color"),
        "outline_opacity": alpha(outline.get("color")),
        "outline_style": outline.get("style"),
        "outline_width": outline.get("width"),
    }


def _legend_items_from_preview(config: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not config:
        return []
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for overlay in config.get("derived_overlays") or []:
        if not isinstance(overlay, dict):
            continue
        visible = overlay.get("default_visible", overlay.get("visible", True))
        if visible is False:
            continue
        key = str(overlay.get("symbol_key") or overlay.get("role") or overlay.get("id") or "")
        label = _legend_label_for_overlay(overlay)
        dedupe_key = f"{key}:{label}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append(
            {
                "id": overlay.get("id"),
                "label": label,
                "geometry_type": overlay.get("geometry_type") or overlay.get("geometry_role"),
                "symbol_key": overlay.get("symbol_key"),
                "geometry_role": overlay.get("geometry_role") or overlay.get("role"),
                "map_role": overlay.get("map_role") or overlay.get("role"),
                "cartography_role": overlay.get("cartography_role"),
                "drawing_info": overlay.get("drawing_info"),
                "opacity": overlay.get("opacity"),
                "route_mode": overlay.get("route_mode"),
                "source": "derived_overlay",
                **_legend_symbol_fields(overlay.get("drawing_info")),
            }
        )
    for layer in config.get("context_layers") or []:
        if not isinstance(layer, dict):
            continue
        if layer.get("legend_included") is False:
            continue
        visible = layer.get("default_visible", layer.get("visibility", True))
        if visible is False:
            continue
        label = str(layer.get("legend_label") or layer.get("title") or layer.get("layer_key") or "Context layer")
        dedupe_key = f"context:{label}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append(
            {
                "id": layer.get("id") or layer.get("layer_key"),
                "label": label,
                "geometry_type": layer.get("geometry_type"),
                "geometry_role": layer.get("role") or "context",
                "map_role": layer.get("map_role"),
                "cartography_role": layer.get("cartography_role"),
                "layer_role": layer.get("layer_role"),
                "drawing_info": layer.get("drawing_info"),
                "opacity": layer.get("opacity"),
                "source": "context_layer",
                **_legend_symbol_fields(layer.get("drawing_info")),
            }
        )
    return items


def _layer_key_for_qa(layer: dict[str, Any]) -> str:
    return str(layer.get("layer_key") or layer.get("id") or layer.get("title") or "")


def _is_zero_feature_row(row: dict[str, Any], qa_status: str | None) -> bool:
    if row.get("visible") is False:
        return False
    feature_count = row.get("feature_count")
    if row.get("query_status") in {"zero_features", "query_failed", "source_unavailable"} and feature_count in {None, 0, "0"}:
        return True
    if feature_count == 0:
        return True
    return feature_count is None and qa_status in {"no_visible_features", "query_failed"}


def _apply_legend_truth_from_qa(config: dict[str, Any], qa: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Hide zero-feature planned source layers so the legend mirrors the map."""
    patched = deepcopy(config)
    summary = deepcopy(qa.get("visible_feature_summary") or [])
    qa_status = qa.get("qa_status")
    rows_by_id = {str(row.get("layer_id") or ""): row for row in summary if isinstance(row, dict)}
    legend_keys: set[str] = set()
    next_layers: list[dict[str, Any]] = []
    for layer in patched.get("context_layers") or []:
        if not isinstance(layer, dict):
            next_layers.append(layer)
            continue
        item = deepcopy(layer)
        key = _layer_key_for_qa(item)
        row = rows_by_id.get(key)
        if row and _is_zero_feature_row(row, str(qa_status or "")):
            item["visibility"] = False
            item["default_visible"] = False
            item["visible_by_default"] = False
            item["legend_included"] = False
            item["query_status"] = row.get("query_status") or "zero_features"
            warnings = list(item.get("review_warnings") or [])
            warning = row.get("warning") or "Layer returned no visible features for the requested area/filter."
            if warning not in warnings:
                warnings.append(str(warning))
            item["review_warnings"] = warnings
        else:
            visible = item.get("default_visible", item.get("visibility", True)) is not False
            item["legend_included"] = visible
            if visible:
                legend_keys.add(key)
        next_layers.append(item)
    for row in summary:
        if not isinstance(row, dict):
            continue
        key = str(row.get("layer_id") or "")
        if row.get("query_status") is None:
            row["query_status"] = "hidden" if row.get("visible") is False else "visible"
        row["legend_included"] = (
            row.get("query_status") == "generated"
            or (key in legend_keys and not _is_zero_feature_row(row, str(qa_status or "")))
        )
        row["renderer_label"] = row.get("legend_label") or row.get("layer_title")
    patched["context_layers"] = next_layers
    return patched, {**qa, "visible_feature_summary": summary}


def _has_partial_context_map(preview_config: dict[str, Any] | None) -> bool:
    if not isinstance(preview_config, dict):
        return False
    try:
        return int(preview_config.get("visible_feature_total") or 0) > 0
    except (TypeError, ValueError):
        return False


def _has_visible_feature_role(preview_config: dict[str, Any] | None, roles: set[str]) -> bool:
    if not isinstance(preview_config, dict):
        return False
    for row in preview_config.get("visible_feature_summary") or []:
        if not isinstance(row, dict) or row.get("visible") is False:
            continue
        if str(row.get("expected_role") or row.get("map_role") or "").lower() not in roles:
            continue
        try:
            if int(row.get("feature_count") or 0) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False


def _role_query_failed(preview_config: dict[str, Any] | None, roles: set[str]) -> bool:
    if not isinstance(preview_config, dict):
        return False
    return any(
        isinstance(row, dict)
        and str(row.get("expected_role") or row.get("map_role") or "").lower() in roles
        and row.get("query_status") in {"query_failed", "source_unavailable"}
        for row in preview_config.get("visible_feature_summary") or []
    )


def _has_local_map_output(recipe: dict[str, Any], preview_config: dict[str, Any] | None) -> bool:
    if isinstance(preview_config, dict) and preview_config.get("derived_overlays"):
        return True
    if recipe.get("derived_overlays"):
        return True
    if (recipe.get("analysis_execution") or {}).get("derived_outputs"):
        return True
    if (recipe.get("proximity_result") or {}).get("status") == "ok":
        return True
    screening = recipe.get("floodplain_screening") if isinstance(recipe.get("floodplain_screening"), dict) else {}
    try:
        affected_count = int(screening.get("affected_feature_count") or 0)
    except (TypeError, ValueError):
        affected_count = 0
    if screening.get("status") == "completed" and affected_count > 0:
        return True
    parcel_context = recipe.get("parcel_context") or {}
    return bool(parcel_context.get("can_focus_map") and parcel_context.get("selected_parcel_geojson_path"))


def _zoning_context_fallback_used(preview_config: dict[str, Any] | None) -> bool:
    if not isinstance(preview_config, dict):
        return False
    return any(
        isinstance(layer, dict)
        and layer.get("fallback_used")
        and str(layer.get("cartography_role") or layer.get("map_role") or "").lower() in {"zoning", "context_polygon_muted"}
        for layer in preview_config.get("context_layers") or []
    )


def _build_map_layout(recipe: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    result = recipe.get("proximity_result") or {}
    route_label = _route_mode_label(result) if result else "Draft map"
    screening = recipe.get("floodplain_screening") if isinstance(recipe.get("floodplain_screening"), dict) else None
    if result:
        title = recipe.get("map_title") or (config or {}).get("map_title") or "AutoMap Draft Map"
        subtitle = _map_layout_subtitle(result)
    elif screening:
        aoi_name = str(screening.get("aoi_name") or "Cabarrus County")
        partial_context = bool(_primary_result_blocker(recipe))
        title = f"{aoi_name} Floodplain Context" if partial_context else f"{aoi_name} Floodplain Parcel Screening"
        affected_count = int(screening.get("affected_feature_count") or 0)
        if screening.get("status") == "completed" and affected_count > 0:
            subtitle = "Parcels intersecting the 100-year floodplain. Draft only, not an official determination."
        elif screening.get("status") == "no_matches":
            subtitle = f"No {aoi_name} parcels were found intersecting the 100-year floodplain in the available data."
        else:
            subtitle = "Affected parcel extraction unavailable. Showing 100-year floodplain context only."
    else:
        title = recipe.get("map_title") or (config or {}).get("map_title") or "AutoMap Draft Map"
        subtitle = "Draft AutoMap preview, not an official county map."
    return {
        "title": title,
        "subtitle": subtitle,
        "map_purpose": recipe.get("map_purpose") or (config or {}).get("map_purpose"),
        "relationship_type": recipe.get("relationship_type") or (config or {}).get("relationship_type"),
        "how_to_read": (
            "Orange areas show affected parcels. Blue overlay shows the 100-year floodplain. Where they overlap, parcels are floodplain-affected."
            if screening and screening.get("status") == "completed" and int(screening.get("affected_feature_count") or 0) > 0
            else None
        ),
        "legend_items": _legend_items_from_preview(config),
        "scale_bar_enabled": True,
        "scale_bar_position": "bottom_center",
        "scale_bar_width_percent": 64,
        "scale_bar_style": "centered_enterprise",
        "north_arrow_enabled": True,
        "disclaimer": "Draft AutoMap preview - Local only - Not official county map",
        "route_mode_label": route_label,
        "print_ready": bool(config) and not bool(_primary_result_blocker(recipe)),
    }


def _proximity_context_layers(layers: list[dict[str, Any]], result: dict[str, Any]) -> list[dict[str, Any]]:
    """Reduce proximity preview clutter while preserving layer metadata."""
    target_layer_key = result.get("target_layer_key")
    cleaned: list[dict[str, Any]] = []
    for layer in layers:
        item = deepcopy(layer)
        blob = " ".join(
            str(value).lower()
            for value in [
                item.get("title"),
                item.get("layer_key"),
                item.get("layer_name"),
                item.get("role"),
                item.get("category"),
            ]
            if value
        )
        hide_reason = None
        if "address" in blob:
            hide_reason = "Full address layer hidden to reduce clutter."
        elif "tax parcel" in blob or "parcel" in blob:
            hide_reason = "Full parcel layer hidden because selected parcel/context is represented by derived overlays when available."
        elif target_layer_key and item.get("layer_key") == target_layer_key:
            hide_reason = "Full facility layer hidden because the nearest target is shown as a derived marker."
        elif "nearest_facility_target" in blob or ("fire" in blob and "station" in blob):
            hide_reason = "Full facility layer hidden because the nearest target is shown as a derived marker."
        if hide_reason:
            item["visibility"] = False
            item["default_visible"] = False
            item["is_context_layer"] = True
            warnings = list(item.get("review_warnings") or [])
            if hide_reason not in warnings:
                warnings.append(hide_reason)
            item["review_warnings"] = warnings
        else:
            item["default_visible"] = item.get("visibility", True)
            item["is_context_layer"] = True
        cleaned.append(item)
    return cleaned


def _composer_context_layers(layers: list[dict[str, Any]], recipe: dict[str, Any]) -> list[dict[str, Any]]:
    """Reduce non-proximity preview clutter while preserving metadata."""
    request_type = str((recipe.get("request_plan") or {}).get("request_type") or recipe.get("request_type") or "")
    parsed_topics = set((recipe.get("parsed_request") or {}).get("topics") or [])
    prompt_text = str(recipe.get("user_intent") or recipe.get("raw_prompt") or "").lower()
    roads_requested = "transportation" in parsed_topics or any(
        term in prompt_text for term in ("road", "street", "highway", "traffic", "corridor")
    )
    cleaned: list[dict[str, Any]] = []
    for layer in layers:
        item = deepcopy(layer)
        blob = " ".join(
            str(value).lower()
            for value in [
                item.get("title"),
                item.get("layer_key"),
                item.get("layer_name"),
                item.get("role"),
                item.get("category"),
            ]
            if value
        )
        hide_reason = None
        if request_type == "zoning_context" and (item.get("category") == "parcel" or "parcel" in blob) and "parcel" not in parsed_topics:
            hide_reason = "Full parcel layer hidden because this request is a zoning/road context map."
        elif request_type == "zoning_context" and not roads_requested and (
            item.get("category") == "transportation" or any(term in blob for term in ("road", "street", "centerline", "highway"))
        ):
            hide_reason = "Road context hidden because this zoning request did not ask for roads."
        elif request_type == "floodplain_screening" and (item.get("category") == "parcel" or "parcel" in blob):
            has_affected_overlay = any(
                isinstance(overlay, dict) and overlay.get("role") == "affected_parcels"
                for overlay in recipe.get("derived_overlays") or []
            )
            hide_reason = (
                "Full parcel layer hidden because affected parcels are shown as the derived screening result."
                if has_affected_overlay
                else "Full parcel layer hidden because exact parcel-floodplain screening is unavailable for this draft."
            )
        if hide_reason:
            item["visibility"] = False
            item["default_visible"] = False
            item["visible_by_default"] = False
            item["map_role"] = "diagnostics_only"
            item["display_role"] = "diagnostics_only"
            item["diagnostics_only"] = True
            warnings = list(item.get("review_warnings") or [])
            if hide_reason not in warnings:
                warnings.append(hide_reason)
            item["review_warnings"] = warnings
        else:
            item["default_visible"] = item.get("visibility", True)
        item["is_context_layer"] = True
        cleaned.append(brain_style_context_layer(item, recipe))
    return sorted(cleaned, key=brain_context_draw_rank)


def _apply_proximity_result_to_recipe(recipe: dict[str, Any], prompt: str, result: dict[str, Any]) -> None:
    """Attach proximity metadata/output to a recipe without publishing anything."""
    recipe["request_type"] = "proximity"
    if result.get("status") == "ok":
        recipe["map_title"] = _proximity_map_title(result)
    recipe["proximity_result"] = result
    recipe["origin_context"] = _origin_context_from_proximity(prompt, result)
    recipe["proximity_context"] = {
        "proximity_requested": True,
        "target_type": result.get("target_type"),
        "route_mode": result.get("route_mode") or "straight_line_fallback",
        "road_route_supported": False,
        "straight_line_supported": True,
        "route_status": result.get("route_status"),
        "route_label": result.get("route_label"),
        "route_warning": result.get("route_warning"),
        "route_refinement_available": bool(result.get("route_refinement_available")),
        "route_refinement_status": result.get("route_refinement_status"),
    }
    if result.get("derived_overlays"):
        recipe["derived_overlays"] = result["derived_overlays"]
    target_layer = result.get("target_layer")
    if isinstance(target_layer, dict) and target_layer.get("layer_key"):
        selected_keys = {layer.get("layer_key") for layer in recipe.get("selected_layers") or []}
        if target_layer["layer_key"] not in selected_keys:
            recipe.setdefault("selected_layers", []).append(_target_layer_as_selected(target_layer))
    if result.get("status") == "ok":
        line_path = result.get("line_geojson_path")
        if line_path:
            recipe.setdefault("analysis_execution", {}).setdefault("derived_outputs", []).append(
                {
                    "type": "proximity_line_geojson",
                    "path": line_path,
                    "url": result.get("line_geojson_url") or output_file_url(line_path),
                    "title": result.get("route_label") or "Straight-line fallback",
                    "layer_key": (result.get("derived_layer") or {}).get("layer_key") or f"derived_proximity_{result.get('proximity_result_id')}",
                    "derived_layer": result.get("derived_layer") or {},
                    "analysis_run_id": result.get("proximity_result_id"),
                }
            )
        extent = _extent_from_proximity_result(result)
        if extent:
            recipe["suggested_extent"] = extent
        recipe["preview_status"] = "ready_for_proximity_preview"
        recipe["focus_mode"] = "proximity"
        if result.get("route_warning"):
            _append_unique_warning(recipe, str(result["route_warning"]))
        if result.get("route_mode") in {"straight_line_fallback", "straight_line_reference"}:
            _append_unique_warning(recipe, "Straight-line fallback. Road route unavailable.")
        _append_unique_warning(recipe, "Full address layer hidden to reduce clutter.")
        if recipe["origin_context"].get("property_match_status") == "not_resolved":
            _append_unique_warning(recipe, "Address matched, but related parcel was not resolved from verified fields.")
    else:
        reason = recipe["origin_context"].get("reason_if_not_focusable")
        if reason:
            _append_unique_warning(recipe, reason)
        recipe["preview_status"] = "blocked_until_origin_matched"
        recipe.setdefault("analysis_execution", {}).update(
            {
                "analysis_status": "blocked_until_origin_matched",
                "operation_type": "proximity_preview_blocked",
                "executable": False,
                "blocked_reasons": [reason or "Origin not matched."],
            }
        )


def _preview_config_for(path: Path, can_preview: bool) -> dict[str, Any] | None:
    if not can_preview:
        return None
    return build_preview_config(path)


def _augment_preview_config(preview_config: dict[str, Any] | None, recipe: dict[str, Any], webmap_json: dict[str, Any]) -> dict[str, Any] | None:
    """Attach composer-only local overlays and focused extent metadata."""
    if not preview_config:
        return None
    config = deepcopy(preview_config)
    config["basemap"] = config.get("basemap") or "streets-vector"
    config["map_title"] = recipe.get("map_title") or webmap_json.get("title") or config.get("map_title")
    config["map_purpose"] = recipe.get("map_purpose")
    config["relationship_type"] = recipe.get("relationship_type")
    config["context_layers"] = _composer_context_layers(config.get("operational_layers") or [], recipe)
    config["warnings"] = _review_warnings(recipe, recipe.get("parcel_context") or {})
    proximity_result = recipe.get("proximity_result") or {}
    overlays = recipe.get("derived_overlays") or proximity_result.get("derived_overlays") or []
    if overlays:
        config["derived_overlays"] = overlays
    if overlays and proximity_result:
        config["context_layers"] = _proximity_context_layers(config.get("context_layers") or [], recipe.get("proximity_result") or {})
        config["focus_mode"] = recipe.get("focus_mode") or "proximity"
        config["preview_status"] = recipe.get("preview_status") or "ready_for_proximity_preview"
        config["proximity_result"] = proximity_result
        config["origin_summary"] = {
            "origin_input": proximity_result.get("origin_input"),
            "origin_type": proximity_result.get("origin_type"),
            "origin_match_status": "matched" if proximity_result.get("status") == "ok" else "needs_review",
        }
        config["target_summary"] = {
            "target_type": proximity_result.get("target_type"),
            "requested_target_type": proximity_result.get("requested_target_type"),
            "target_classification": proximity_result.get("target_classification"),
            "target_name": proximity_result.get("target_name"),
            "target_layer_key": proximity_result.get("target_layer_key"),
        }
        config["distance_summary"] = {
            "distance_value": proximity_result.get("distance_value"),
            "distance_unit": proximity_result.get("distance_unit"),
            "line_type": proximity_result.get("line_type"),
            "route_status": proximity_result.get("route_status"),
            "route_mode": proximity_result.get("route_mode"),
            "route_label": proximity_result.get("route_label"),
            "route_warning": proximity_result.get("route_warning"),
            "route_refinement_available": proximity_result.get("route_refinement_available"),
            "route_refinement_status": proximity_result.get("route_refinement_status"),
        }
        config["parcel_resolution_summary"] = {
            "property_match_status": proximity_result.get("property_match_status"),
            "related_parcel": (recipe.get("origin_context") or {}).get("related_parcel"),
        }
        suggested_extent = recipe.get("suggested_extent")
        if isinstance(suggested_extent, dict):
            config["initial_extent"] = suggested_extent
            config["focus_extent"] = suggested_extent
        else:
            target_geometry = (((webmap_json.get("initialState") or {}).get("viewpoint") or {}).get("targetGeometry") or {})
            if isinstance(target_geometry, dict) and target_geometry:
                config["initial_extent"] = target_geometry
                config["focus_extent"] = target_geometry
    elif isinstance(recipe.get("floodplain_screening"), dict):
        screening = recipe["floodplain_screening"]
        config["focus_mode"] = recipe.get("focus_mode") or "floodplain_screening"
        config["preview_status"] = recipe.get("preview_status") or "ready_for_floodplain_screening_preview"
        config["floodplain_screening"] = screening
        extent = screening.get("result_extent") or recipe.get("suggested_extent")
        if isinstance(extent, dict):
            config["initial_extent"] = extent
            config["focus_extent"] = extent
    config = apply_aoi_to_preview_config(config, recipe)
    qa = visible_map_qa(config, recipe)
    patched_config = brain_apply_visible_qa_fallbacks(config, qa, recipe)
    if qa.get("fallback_used") or patched_config != config:
        config = patched_config
        qa = visible_map_qa(config, recipe)
    else:
        config = patched_config
    config, qa = _apply_legend_truth_from_qa(config, qa)
    config["visible_feature_summary"] = qa.get("visible_feature_summary") or []
    config["visible_feature_total"] = qa.get("visible_feature_total")
    config["visible_map_qa"] = {
        "brain_version": qa.get("brain_version"),
        "qa_status": qa.get("qa_status"),
        "fallback_used": bool(qa.get("fallback_used")),
        "warnings": qa.get("warnings") or [],
        "aoi_summary": (config.get("aoi") or {}).get("summary"),
        "display_complexity": config.get("display_complexity"),
        "visual_quality": qa.get("visual_quality"),
    }
    if isinstance(qa.get("visible_extent"), dict) and qa["visible_extent"]:
        config["initial_extent"] = qa["visible_extent"]
        config["focus_extent"] = qa["visible_extent"]
    config["warnings"] = sorted({*[str(item) for item in config.get("warnings") or []], *[str(item) for item in qa.get("warnings") or []]})
    config["brain_explanation"] = build_brain_explanation(recipe, config)
    config["map_layout"] = _build_map_layout(recipe, config)
    return config


def _save_session_payload(session_folder: Path, payload: dict[str, Any]) -> None:
    _write_json(session_folder / "composer_session.json", payload)


def _layer_identifier(layer: dict[str, Any], index: int) -> str:
    return str(layer.get("layer_key") or layer.get("id") or layer.get("title") or f"layer_{index}")


def _layer_visible(layer: dict[str, Any], *, derived: bool = False) -> bool:
    if "visibility" in layer:
        return bool(layer.get("visibility"))
    if "visible" in layer:
        return bool(layer.get("visible"))
    if "default_visible" in layer:
        return bool(layer.get("default_visible"))
    if derived:
        return True
    return True


def _preview_layer_entry(layer: dict[str, Any], index: int, *, derived: bool = False) -> dict[str, Any]:
    entry = deepcopy(layer)
    key = _layer_identifier(entry, index)
    entry["layer_key"] = key
    entry["id"] = entry.get("id") or key
    entry["title"] = entry.get("title") or entry.get("layer_name") or key
    entry["visibility"] = _layer_visible(entry, derived=derived)
    entry["opacity"] = float(entry.get("opacity") if isinstance(entry.get("opacity"), (int, float)) else 1)
    entry["role"] = entry.get("role") or entry.get("geometry_role") or entry.get("display_role") or ("derived_output" if derived else "context")
    entry["is_derived"] = derived
    if derived:
        entry["source_role"] = "derived local"
        entry["source_status"] = entry.get("source_status") or "derived local"
        entry["local_output"] = True
    return entry


def _all_preview_layers(preview_config: dict[str, Any], selected_layers: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for index, overlay in enumerate(preview_config.get("derived_overlays") or []):
        if isinstance(overlay, dict):
            layers.append(_preview_layer_entry(overlay, index, derived=True))
    offset = len(layers)
    for collection_key in ("operational_layers", "context_layers"):
        for index, layer in enumerate(preview_config.get(collection_key) or []):
            if isinstance(layer, dict):
                layers.append(_preview_layer_entry(layer, offset + index))
        offset = len(layers)
    if not layers:
        for index, layer in enumerate(selected_layers or []):
            if isinstance(layer, dict):
                layers.append(_preview_layer_entry(layer, index))
    return layers


def _payload_layer_index(payload: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]], list[str]]:
    indexed: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for layer in (payload or {}).get("layers") or []:
        if not isinstance(layer, dict):
            continue
        key = str(layer.get("layer_key") or layer.get("id") or layer.get("title") or "").strip()
        if not key:
            continue
        indexed[key] = layer
        order.append(key)
    for key in (payload or {}).get("layer_order") or []:
        if isinstance(key, str) and key and key not in order:
            order.append(key)
    return indexed, order


def _apply_payload_to_preview_config(preview_config: dict[str, Any], payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return deepcopy(preview_config)
    config = deepcopy(preview_config)
    indexed, order = _payload_layer_index(payload)

    def patch_layer(layer: dict[str, Any], index: int, *, derived: bool = False) -> dict[str, Any]:
        key = _layer_identifier(layer, index)
        patch = indexed.get(key) or indexed.get(str(layer.get("id") or "")) or indexed.get(str(layer.get("title") or ""))
        if not patch:
            return layer
        next_layer = deepcopy(layer)
        if patch.get("title"):
            next_layer["title"] = patch["title"]
        if "visibility" in patch:
            next_layer["visibility"] = bool(patch["visibility"])
            next_layer["visible"] = bool(patch["visibility"])
            next_layer["default_visible"] = bool(patch["visibility"])
        if isinstance(patch.get("opacity"), (int, float)):
            next_layer["opacity"] = float(patch["opacity"])
        if patch.get("role"):
            next_layer["role"] = patch["role"]
        if patch.get("definition_expression"):
            next_layer["definition_expression"] = patch["definition_expression"]
        if patch.get("line_style"):
            next_layer["line_style"] = patch["line_style"]
        if isinstance(patch.get("line_thickness"), (int, float)):
            next_layer["line_thickness"] = float(patch["line_thickness"])
        if derived:
            next_layer["local_output"] = True
        return next_layer

    for collection_key in ("derived_overlays", "operational_layers", "context_layers"):
        collection = config.get(collection_key)
        if not isinstance(collection, list):
            continue
        derived = collection_key == "derived_overlays"
        patched = [patch_layer(layer, index, derived=derived) if isinstance(layer, dict) else layer for index, layer in enumerate(collection)]
        if order:
            rank = {key: index for index, key in enumerate(order)}
            patched.sort(
                key=lambda layer: rank.get(
                    _layer_identifier(layer, 9999) if isinstance(layer, dict) else str(layer),
                    9999,
                )
            )
        config[collection_key] = patched
    return config


def _map_extent_from_response(
    response: dict[str, Any],
    preview_config: dict[str, Any],
    payload: dict[str, Any] | None = None,
    incoming_state: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if isinstance((payload or {}).get("active_map_extent"), dict):
        return (payload or {})["active_map_extent"]
    for key in ("map_extent", "current_extent", "extent"):
        if isinstance((incoming_state or {}).get(key), dict) and (incoming_state or {})[key]:
            return (incoming_state or {})[key]
    for key in ("focus_extent", "initial_extent"):
        if isinstance(preview_config.get(key), dict) and preview_config[key]:
            return preview_config[key]
    webmap = response.get("webmap_json") or {}
    target_geometry = (((webmap.get("initialState") or {}).get("viewpoint") or {}).get("targetGeometry") or {})
    return target_geometry if isinstance(target_geometry, dict) and target_geometry else None


def _build_composer_map_state(response: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    incoming_state = (payload or {}).get("map_state") if isinstance((payload or {}).get("map_state"), dict) else {}
    preview_source = incoming_state.get("preview_config") if isinstance(incoming_state.get("preview_config"), dict) else response.get("preview_config") or {}
    preview_config = _apply_payload_to_preview_config(preview_source, payload)
    layout = deepcopy(response.get("map_layout") or preview_config.get("map_layout") or {})
    map_title = str((payload or {}).get("map_title") or incoming_state.get("map_title") or layout.get("title") or response.get("map_title") or "AutoMap Draft Map")
    map_subtitle = str((payload or {}).get("map_description") or incoming_state.get("map_subtitle") or layout.get("subtitle") or "Draft preview only. Not an official map.")
    layout["title"] = map_title
    layout["subtitle"] = map_subtitle
    layout.setdefault("scale_bar_enabled", True)
    layout.setdefault("scale_bar_position", "bottom_center")
    layout.setdefault("scale_bar_width_percent", 64)
    layout.setdefault("scale_bar_style", "centered_enterprise")
    layout.setdefault("north_arrow_enabled", True)
    preview_config["map_title"] = map_title
    preview_config["map_layout"] = layout
    extent = _map_extent_from_response(response, preview_config, payload, incoming_state)

    layers = _all_preview_layers(preview_config, response.get("selected_layers") or [])
    payload_layers, _ = _payload_layer_index(payload)
    for index, layer in enumerate(layers):
        patch = payload_layers.get(_layer_identifier(layer, index)) or payload_layers.get(str(layer.get("title") or ""))
        if not patch:
            continue
        if patch.get("title"):
            layer["title"] = patch["title"]
        if "visibility" in patch:
            layer["visibility"] = bool(patch["visibility"])
        if isinstance(patch.get("opacity"), (int, float)):
            layer["opacity"] = float(patch["opacity"])
        if patch.get("role"):
            layer["role"] = patch["role"]
        if patch.get("line_style"):
            layer["line_style"] = patch["line_style"]
        if isinstance(patch.get("line_thickness"), (int, float)):
            layer["line_thickness"] = float(patch["line_thickness"])
    visible_layers = [layer for layer in layers if layer.get("visibility") and not layer.get("remove_layer")]
    hidden_layers = [layer for layer in layers if not layer.get("visibility") or layer.get("remove_layer")]
    layer_order = [_layer_identifier(layer, index) for index, layer in enumerate(layers)]
    layer_opacity = {_layer_identifier(layer, index): layer.get("opacity", 1) for index, layer in enumerate(layers)}
    layer_titles = {_layer_identifier(layer, index): layer.get("title") for index, layer in enumerate(layers)}
    layer_roles = {_layer_identifier(layer, index): layer.get("role") for index, layer in enumerate(layers)}
    layer_symbology = {
        _layer_identifier(layer, index): {
            "symbol_key": layer.get("symbol_key"),
            "line_style": layer.get("line_style"),
            "line_thickness": layer.get("line_thickness"),
            "geometry_role": layer.get("geometry_role"),
        }
        for index, layer in enumerate(layers)
    }
    proximity = response.get("proximity_result") or preview_config.get("proximity_result") or {}
    route_summary = {
        "route_mode": proximity.get("route_mode") if isinstance(proximity, dict) else None,
        "route_label": proximity.get("route_label") if isinstance(proximity, dict) else None,
        "route_warning": proximity.get("route_warning") if isinstance(proximity, dict) else None,
        "distance_value": proximity.get("distance_value") if isinstance(proximity, dict) else None,
        "distance_unit": proximity.get("distance_unit") if isinstance(proximity, dict) else None,
    }
    export_options_payload = {
        **(incoming_state.get("export_options") if isinstance(incoming_state.get("export_options"), dict) else {}),
        **((payload or {}).get("export_options") if isinstance((payload or {}).get("export_options"), dict) else {}),
    }
    if (payload or {}).get("export_mode"):
        export_options_payload["export_mode"] = (payload or {}).get("export_mode")
    export_options = normalize_export_options(export_options_payload)
    report_config_payload = (payload or {}).get("report_config")
    if report_config_payload is None and not ((payload or {}).get("export_mode") or (payload or {}).get("export_options")):
        report_config_payload = incoming_state.get("report_section_config") or (response.get("composer_map_state") or {}).get("report_section_config")
    report_config = report_config_for_export_mode(report_config_payload, export_options)
    state = {
        "composer_session_id": response.get("composer_session_id"),
        "map_title": map_title,
        "map_subtitle": map_subtitle,
        "raw_prompt": response.get("raw_prompt") or response.get("prompt"),
        "request_type": response.get("request_type"),
        "preview_config": preview_config,
        "map_extent": extent,
        "current_center": incoming_state.get("current_center"),
        "current_zoom": incoming_state.get("current_zoom"),
        "current_scale": incoming_state.get("current_scale"),
        "current_rotation": incoming_state.get("current_rotation", 0),
        "basemap": preview_config.get("basemap") or "streets-vector",
        "visible_layers": visible_layers,
        "hidden_layers": hidden_layers,
        "layer_order": layer_order,
        "layer_opacity": layer_opacity,
        "layer_titles": layer_titles,
        "layer_roles": layer_roles,
        "layer_symbology": layer_symbology,
        "derived_overlays": preview_config.get("derived_overlays") or [],
        "legend_items": layout.get("legend_items") or [],
        "scale_bar_config": default_scale_bar_config(layout),
        "north_arrow_config": default_north_arrow_config(layout),
        "route_summary": route_summary,
        "proximity_summary": proximity if isinstance(proximity, dict) else {},
        "parcel_context": response.get("parcel_context") or {},
        "table_context": response.get("table_context") or (response.get("composer_map_state") or {}).get("table_context") or {},
        "warnings": response.get("warnings") or [],
        "missing_data": response.get("missing_data") or [],
        "reviewer_notes": (payload or {}).get("notes") or (response.get("composer_map_state") or {}).get("reviewer_notes") or "",
        "adjusted_state_applied": bool((payload or {}).get("layers") or response.get("applied_adjustments")),
        "export_mode": export_options.get("export_mode"),
        "export_options": export_options,
        "print_export_options": export_options,
        "report_section_config": report_config,
        "updated_at": utc_timestamp(),
    }
    statistics = build_report_statistics(state)
    sections = build_report_sections(state, statistics, report_config)
    state["report_statistics"] = statistics
    state["report_sections"] = sections
    return state


def _attach_composer_map_state(
    response: dict[str, Any],
    session_folder: Path,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    had_preview_config = response.get("preview_config") is not None
    map_state = _build_composer_map_state(response, payload)
    response["composer_map_state"] = map_state
    if had_preview_config:
        response["preview_config"] = map_state["preview_config"]
        response["map_layout"] = map_state["preview_config"].get("map_layout")
    else:
        response["preview_config"] = None
        response["map_layout"] = response.get("map_layout")
    response["map_title"] = map_state["map_title"]
    response["report_statistics"] = map_state["report_statistics"]
    response["report_sections"] = map_state["report_sections"]
    _write_json(session_folder / "composer_map_state.json", map_state)
    try:
        upsert_composer_map_state(str(response["composer_session_id"]), map_state)
        response["composer_map_state_persisted"] = True
    except Exception:
        response["composer_map_state_persisted"] = False
        response["composer_map_state_persist_error"] = "database persistence unavailable"
    return response


def _base_session_response(
    *,
    session_id: str,
    raw_prompt: str,
    session_folder: Path,
    recipe: dict[str, Any],
    webmap_json: dict[str, Any],
    preview_config: dict[str, Any] | None,
    review_packet_path: Path | None,
    adjusted_packet_path: Path | None = None,
    report_package: Any | None = None,
    export_files: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    parcel_context = recipe.get("parcel_context") or {}
    origin_context = recipe.get("origin_context") or {}
    proximity_result = recipe.get("proximity_result") or None
    screening = recipe.get("floodplain_screening") if isinstance(recipe.get("floodplain_screening"), dict) else {}
    blockers = _preview_blockers(recipe)
    can_preview = _can_preview(recipe, webmap_json)
    if blockers:
        can_preview = False
    result_state = _result_state(recipe, can_preview, blockers)
    visible_map_qa = (preview_config or {}).get("visible_map_qa") if isinstance(preview_config, dict) else {}
    qa_status = (visible_map_qa or {}).get("qa_status")
    if can_preview and preview_config and qa_status in {"no_visible_features", "query_failed"} and not _has_local_map_output(recipe, preview_config):
        result_state = "blocked" if qa_status == "query_failed" else "no_matches"
        can_preview = False
        if result_state == "blocked":
            blockers = [
                *blockers,
                "AutoMap found relevant layers but could not verify visible features for the requested area/filter.",
            ]
    elif result_state == "ready" and (
        recipe.get("request_type") or (recipe.get("request_plan") or {}).get("request_type")
    ) == "zoning_context" and not recipe.get("parcel_context") and not _has_visible_feature_role(preview_config, {"zoning"}):
        result_state = "blocked" if _role_query_failed(preview_config, {"zoning"}) else "no_matches"
        can_preview = False
        geography = (
            ((preview_config or {}).get("aoi") or {}).get("geography_name")
            or (((recipe.get("request_plan") or {}).get("parameters") or {}).get("geography"))
            or "requested"
        )
        blockers = [
            *blockers,
            f"AutoMap found the {geography} area but could not load usable zoning features for this request."
            if result_state == "blocked"
            else "No visible zoning features found for this request.",
        ]
    elif result_state == "ready" and _zoning_context_fallback_used(preview_config):
        result_state = "partial"
    result_truth = _result_truth_summary(recipe, result_state)
    if result_state in {"partial", "no_matches"} and "context_map_available" not in result_truth:
        result_truth["context_map_available"] = result_state == "partial" and _has_partial_context_map(preview_config)
    if result_state == "no_matches":
        result_truth["context_map_available"] = False
    map_available = result_state == "ready" or (result_state == "partial" and bool(result_truth.get("context_map_available")))
    packet_path = adjusted_packet_path or review_packet_path
    packet_id = packet_path.name if packet_path else None
    webmap_path = session_folder / ("adjusted_webmap.json" if (session_folder / "adjusted_webmap.json").exists() else "webmap.json")
    response = {
        "composer_session_id": session_id,
        "prompt": raw_prompt,
        "raw_prompt": raw_prompt,
        "map_title": recipe.get("map_title") or webmap_json.get("title"),
        "request_type": recipe.get("request_type") or ("proximity" if proximity_result else (parcel_context.get("request_type") if parcel_context else "general_map")),
        "origin_type": origin_context.get("origin_type") or parcel_context.get("origin_type"),
        "origin_match_status": origin_context.get("origin_match_status") or parcel_context.get("origin_match_status") or parcel_context.get("match_status"),
        "supported_area": origin_context.get("supported_area") or parcel_context.get("supported_area") or (proximity_result or {}).get("supported_area"),
        "origin_candidates": origin_context.get("candidate_matches") or parcel_context.get("candidate_matches") or [],
        "related_parcel": origin_context.get("related_parcel"),
        "proximity_result": proximity_result,
        "analysis_type": screening.get("analysis_type"),
        "map_purpose": recipe.get("map_purpose"),
        "relationship_type": recipe.get("relationship_type"),
        "result_state": result_state,
        **result_truth,
        "analysis_status": (recipe.get("analysis_execution") or {}).get("analysis_status") or screening.get("status"),
        "spatial_relationship": screening.get("spatial_relationship"),
        "result_layer_role": screening.get("result_layer_role"),
        "affected_feature_count": screening.get("affected_feature_count"),
        "floodplain_type": screening.get("floodplain_type"),
        "aoi_name": screening.get("aoi_name"),
        "aoi_type": screening.get("aoi_type"),
        "floodplain_screening": screening or None,
        "request_plan": recipe.get("request_plan"),
        "automap_brain": recipe.get("automap_brain"),
        "brain_explanation": (preview_config or {}).get("brain_explanation") if isinstance(preview_config, dict) else None,
        "route_refinement_available": bool((proximity_result or {}).get("route_refinement_available")),
        "route_refinement_status": (proximity_result or {}).get("route_refinement_status"),
        "recipe": recipe,
        "webmap_json": webmap_json,
        "preview_config": preview_config,
        "preview_status": recipe.get("preview_status"),
        "preview_quality": recipe.get("preview_quality"),
        "map_layout": (preview_config or {}).get("map_layout") if isinstance(preview_config, dict) else None,
        "visible_feature_summary": (preview_config or {}).get("visible_feature_summary") if isinstance(preview_config, dict) else [],
        "visible_feature_total": (preview_config or {}).get("visible_feature_total") if isinstance(preview_config, dict) else None,
        "visible_map_qa": visible_map_qa or None,
        "selected_layers": _selected_layers(recipe),
        "warnings": sorted(
            {
                *[str(item) for item in _review_warnings(recipe, parcel_context)],
                *[str(item) for item in ((preview_config or {}).get("visible_map_qa") or {}).get("warnings") or []],
            }
        ),
        "missing_data": recipe.get("missing_data_needed") or [],
        "parcel_context": parcel_context,
        "can_preview": can_preview,
        "can_analyze": _can_analyze(recipe),
        "can_report": bool(packet_path),
        "preview_blockers": blockers,
        "next_action": _next_action(can_preview, blockers, result_state),
        "simple_steps": [
            {"step": "Request", "status": "complete"},
            {"step": "Preview", "status": "complete" if map_available else "blocked"},
            {"step": "Adjust", "status": "pending" if map_available else "blocked"},
            {"step": "Print / Export", "status": "pending" if map_available else "blocked"},
        ],
        "debug_details": {"recipe_timing": recipe.get("recipe_timing")},
        "review_packet_id": review_packet_path.name if review_packet_path else None,
        "review_packet_path": _repo_relative(review_packet_path),
        "adjusted_packet_id": adjusted_packet_path.name if adjusted_packet_path else None,
        "adjusted_packet_path": _repo_relative(adjusted_packet_path),
        "packet_id": packet_id,
        "packet_path": _repo_relative(packet_path),
        "preview_url": f"/preview/{packet_id}" if packet_id and can_preview else None,
        "webmap_path": _repo_relative(webmap_path),
        "composer_session_path": _repo_relative(session_folder),
        "export": None,
        "draft_only": True,
        "published": False,
        "created_at": _utc_now(),
    }
    if report_package:
        response["export"] = {
            "report_id": report_package.report_id,
            "report_path": _repo_relative(report_package.report_path),
            "report_title": report_package.report_title,
            "files": export_files or [],
            "validation": report_package.validation,
        }
    return response


def _write_layer_csv(path: Path, recipe: dict[str, Any], webmap_json: dict[str, Any]) -> None:
    rows = build_layer_review_table(recipe, webmap_json)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["title", "layer_key", "role", "source_status", "opacity", "visibility", "layer_url"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})


def _write_session_files(session_folder: Path, recipe: dict[str, Any], webmap_json: dict[str, Any]) -> None:
    warnings = build_warning_report(recipe, webmap_json)
    summary = build_review_summary(recipe, webmap_json)
    _write_json(session_folder / "recipe.json", recipe)
    _write_json(session_folder / "webmap.json", webmap_json)
    _write_json(session_folder / "warnings.json", warnings)
    _write_json(session_folder / "layer_review.json", build_layer_review_table(recipe, webmap_json))
    (session_folder / "review_summary.md").write_text(summary, encoding="utf-8")
    _write_layer_csv(session_folder / "layer_list.csv", recipe, webmap_json)


def _is_fast_floodplain_fallback_prompt(prompt: str) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    parsed = parse_prompt(prompt)
    plan = build_brain_plan(prompt, parsed)
    if plan.get("request_type") != "floodplain_screening":
        return None, None
    if live_floodplain_screening_enabled():
        return None, None
    return parsed, plan


def _fast_floodplain_layers() -> list[dict[str, Any]]:
    return [
        {
            "layer_key": "cabarrus_new_tax_parcels_1_tax_parcels",
            "layer_name": "Tax Parcels",
            "title": "Tax Parcels",
            "category": "parcel",
            "role": "base_layer",
            "map_role": "diagnostics_only",
            "layer_url": "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Tax_Parcels/MapServer/1",
            "service_url": "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Tax_Parcels/MapServer",
            "layer_id": 1,
            "is_public": True,
            "is_active": True,
            "is_verified": True,
            "is_feature_layer": True,
            "geometry_type": "esriGeometryPolygon",
            "confidence_score": 0.9,
            "source_status": "verified_public",
            "visibility": False,
            "opacity": 0.12,
            "review_warnings": [
                "Full parcel layer hidden because exact parcel-floodplain screening is unavailable for this draft."
            ],
        },
        {
            "layer_key": "cabarrus_new_flood_hazard_areas_2_floodplain100year",
            "layer_name": "FloodPlain100year",
            "title": "100-year floodplain",
            "category": "flood",
            "role": "constraint_overlay",
            "map_role": "floodplain_overlay",
            "legend_label": "100-year floodplain",
            "layer_url": "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Flood_Hazard_Areas/MapServer/2",
            "service_url": "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/Flood_Hazard_Areas/MapServer",
            "layer_id": 2,
            "is_public": True,
            "is_active": True,
            "is_verified": True,
            "is_feature_layer": True,
            "geometry_type": "esriGeometryPolygon",
            "confidence_score": 0.94,
            "source_status": "verified_public",
            "visibility": True,
            "opacity": 0.34,
        },
        {
            "layer_key": "cabarrus_new_municipaldistrict_0_municipaldistrict",
            "layer_name": "MunicipalDistrict",
            "title": "Concord boundary",
            "category": "jurisdiction",
            "role": "jurisdiction_filter",
            "map_role": "boundary_outline",
            "legend_label": "Concord boundary",
            "layer_url": "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/MunicipalDistrict/MapServer/0",
            "service_url": "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData/MunicipalDistrict/MapServer",
            "layer_id": 0,
            "is_public": True,
            "is_active": True,
            "is_verified": True,
            "is_feature_layer": True,
            "geometry_type": "esriGeometryPolygon",
            "confidence_score": 0.96,
            "source_status": "verified_public",
            "visibility": True,
            "opacity": 0.88,
            "definition_expression": "DISTRICT = 'CITY OF CONCORD'",
        },
    ]


def _fast_floodplain_webmap(recipe: dict[str, Any]) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    for index, layer in enumerate(recipe.get("selected_layers") or []):
        layer_url = layer.get("layer_url")
        definition_expression = layer.get("definition_expression")
        drawing_info = layer.get("drawing_info") or {}
        if not drawing_info:
            if layer.get("map_role") == "boundary_outline":
                drawing_info = brain_cartography_for_role("boundary")["drawing_info"]
            elif layer.get("map_role") == "floodplain_overlay":
                drawing_info = brain_cartography_for_role("flood")["drawing_info"]
            else:
                drawing_info = brain_cartography_for_role("parcel_context")["drawing_info"]
        layer_definition: dict[str, Any] = {"drawingInfo": drawing_info}
        if definition_expression:
            layer_definition["definitionExpression"] = definition_expression
        layers.append(
            {
                "id": f"automap_{layer['layer_key']}",
                "title": layer.get("title") or layer.get("layer_name"),
                "url": layer_url,
                "serviceUrl": layer.get("service_url"),
                "layerUrl": layer_url,
                "layerType": "ArcGISFeatureLayer",
                "visibility": bool(layer.get("visibility", True)),
                "opacity": layer.get("opacity", 1),
                "layerId": layer.get("layer_id"),
                "layerDefinition": layer_definition,
                "showLegend": bool(layer.get("visibility", True)),
                "autoMapRole": layer.get("role"),
                "autoMapCategory": layer.get("category"),
                "autoMapLayerKey": layer.get("layer_key"),
                "autoMapSourceStatus": layer.get("source_status"),
                "autoMapDisplayRole": layer.get("map_role") or layer.get("role"),
                "autoMapDrawOrder": index,
                "autoMapReviewWarnings": layer.get("review_warnings") or [],
            }
        )
    return {
        "title": recipe.get("map_title") or "Concord Floodplain Parcel Screening",
        "description": "Draft AutoMap WebMap JSON. Exact affected-parcel intersection is disabled for this deployment.",
        "operationalLayers": layers,
        "baseMap": {
            "title": "Light Gray Canvas",
            "baseMapLayers": [
                {
                    "id": "World_Light_Gray_Base",
                    "layerType": "ArcGISTiledMapServiceLayer",
                    "url": "https://services.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer",
                    "visibility": True,
                    "opacity": 1,
                    "title": "Light Gray Base",
                }
            ],
        },
        "spatialReference": {"wkid": 4326},
        "version": "2.31",
        "authoringApp": "AutoMap",
        "authoringAppVersion": "0.4",
        "applicationProperties": {"viewing": {"search": {"enabled": False}, "routing": {"enabled": False}}},
        "initialState": {"viewpoint": {"targetGeometry": recipe["suggested_extent"]}},
        "autoMapPublicationStatus": "draft_only_not_published",
        "autoMapGeneratedAt": _utc_now(),
        "autoMapRecipeSummary": {
            "user_intent": recipe.get("user_intent"),
            "confidence_score": recipe.get("confidence_score"),
            "needs_review": recipe.get("needs_review"),
            "review_reasons": recipe.get("review_reasons") or [],
            "missing_data_needed": recipe.get("missing_data_needed") or [],
            "suggested_extent": recipe.get("suggested_extent") or {},
            "preview_status": recipe.get("preview_status"),
            "focus_mode": recipe.get("focus_mode"),
            "floodplain_screening": recipe.get("floodplain_screening"),
        },
        "autoMapWarnings": recipe.get("review_reasons") or [],
        "autoMapValidation": {"is_valid": True, "errors": [], "warnings": []},
    }


def _fast_floodplain_preview_config(recipe: dict[str, Any], webmap_json: dict[str, Any], session_folder: Path) -> dict[str, Any]:
    layers: list[dict[str, Any]] = []
    for index, layer in enumerate(webmap_json.get("operationalLayers") or []):
        layer_definition = layer.get("layerDefinition") if isinstance(layer.get("layerDefinition"), dict) else {}
        drawing_info = layer_definition.get("drawingInfo") if isinstance(layer_definition.get("drawingInfo"), dict) else {}
        layer_url = layer.get("layerUrl") or layer.get("url")
        layers.append(
            {
                "id": layer.get("id"),
                "layer_key": layer.get("autoMapLayerKey") or layer.get("id"),
                "title": layer.get("title"),
                "category": layer.get("autoMapCategory"),
                "role": layer.get("autoMapRole"),
                "map_role": layer.get("autoMapDisplayRole"),
                "display_role": layer.get("autoMapDisplayRole"),
                "url": layer.get("url"),
                "layerUrl": layer_url,
                "layer_url": layer_url,
                "service_url": layer.get("serviceUrl"),
                "layer_id": layer.get("layerId"),
                "preview_type": "feature_layer",
                "visibility": bool(layer.get("visibility", True)),
                "opacity": layer.get("opacity", 1),
                "show_legend": bool(layer.get("showLegend", True)),
                "definition_expression": layer_definition.get("definitionExpression"),
                "drawing_info": drawing_info,
                "review_warnings": [str(item) for item in layer.get("autoMapReviewWarnings") or []],
                "draw_order": layer.get("autoMapDrawOrder", index),
            }
        )
    return {
        "map_title": recipe.get("map_title") or webmap_json.get("title") or "AutoMap Draft Preview",
        "original_prompt": recipe.get("user_intent") or "",
        "initial_extent": recipe.get("suggested_extent") or {},
        "operational_layers": layers,
        "warnings": {"warnings": recipe.get("review_reasons") or [], "publish_ready": False},
        "missing_data": recipe.get("missing_data_needed") or [],
        "data_gaps": [],
        "packet_id": session_folder.name,
        "packet_path": _repo_relative(session_folder),
        "webmap_path": _repo_relative(session_folder / "webmap.json"),
        "draft_status": "composer_fast_floodplain_fallback",
        "preview_status": recipe.get("preview_status"),
        "preview_quality": recipe.get("preview_quality"),
        "focus_mode": recipe.get("focus_mode"),
        "can_focus_map": True,
        "parcel_preview_blocked": False,
        "derived_overlays": recipe.get("derived_overlays") or [],
        "publish_ready": False,
        "preview_only": True,
    }


def _fast_floodplain_fallback_response(
    *,
    prompt: str,
    parsed: dict[str, Any],
    plan: dict[str, Any],
    session_id: str,
    session_folder: Path,
    timing: dict[str, Any],
    started_at: float,
) -> dict[str, Any]:
    extent = {
        "xmin": -80.79068056612213,
        "ymin": 35.25827116710974,
        "xmax": -80.41497340288814,
        "ymax": 35.5178193006496,
        "spatialReference": {"wkid": 4326, "latestWkid": 4326},
    }
    warning = LIVE_SCREENING_DISABLED_WARNING
    recipe = {
        "map_title": "Concord Floodplain Context",
        "request_type": "floodplain_screening",
        "user_intent": prompt,
        "parsed_request": parsed,
        "request_plan": {
            **plan,
            "request_type": "floodplain_screening",
            "primary_domain": "parcels",
            "secondary_domains": sorted({"floodplain", *[str(item) for item in plan.get("secondary_domains") or []]}),
            "spatial_relationships": ["intersects"],
            "constraint_domain": "floodplain",
            "result_layer": "affected_parcels",
            "floodplain_type": "100_year",
        },
        "selected_layers": _fast_floodplain_layers(),
        "rejected_layers": [],
        "filters": [{"topic": "floodplain", "value": "100_year"}],
        "spatial_operations": [{"operation": "intersect", "target": "Tax Parcels", "overlay": "FloodPlain100year", "output": "affected_parcels"}],
        "symbology_recommendations": [
            "Affected parcels should be highlighted when live intersection is enabled.",
            "Show 100-year floodplain as a light blue context layer.",
        ],
        "suggested_extent": extent,
        "confidence_score": plan.get("confidence", 0.84),
        "needs_review": True,
        "review_reasons": [warning],
        "missing_data_needed": [],
        "filter_plan": {},
        "validation": {},
        "analysis_execution": {
            "analysis_status": "partial_context_only",
            "operation_type": "floodplain_parcel_screening",
            "blocked_reasons": [warning],
            "derived_outputs": [],
            "output_count": 0,
            "live_intersection_enabled": False,
        },
        "floodplain_screening": {
            "analysis_type": "floodplain_parcel_screening",
            "status": "partial_context_only",
            "spatial_relationship": "intersects",
            "result_layer_role": "affected_parcels",
            "affected_feature_count": 0,
            "floodplain_type": "100_year",
            "aoi_name": plan.get("geography") or "Concord",
            "aoi_type": plan.get("geography_type") or "municipality",
            "analysis_run_id": None,
            "result_extent": extent,
            "summary_label": "Parcels intersecting the 100-year floodplain",
            "draft_note": "Draft screening only. Not an official flood determination.",
            "warning": warning,
        },
        "focus_mode": "floodplain_screening",
        "preview_status": "partial_floodplain_context_only",
        "preview_quality": "partial_context_only",
        "recipe_timing": {
            "parse_ms": timing.get("parse_ms", 0),
            "intelligence_ms": timing.get("intelligence_ms", 0),
            "layer_match_ms": 0,
            "field_filter_ms": 0,
            "parcel_context_ms": 0,
            "analysis_planning_ms": 0,
            "brain_v2_ms": 0,
            "total_ms": 0,
        },
        "created_at": _utc_now(),
        "notes": [
            "Fast floodplain screening fallback used verified public layer URLs only.",
            "No parcel geometry was downloaded and no ArcGIS item was created.",
        ],
    }
    webmap_json = _fast_floodplain_webmap(recipe)
    _write_session_files(session_folder, recipe, webmap_json)
    preview_started = time.perf_counter()
    preview_config = _augment_preview_config(_fast_floodplain_preview_config(recipe, webmap_json, session_folder), recipe, webmap_json)
    timing["preview_config_ms"] = _elapsed_ms(preview_started)
    response = _base_session_response(
        session_id=session_id,
        raw_prompt=prompt,
        session_folder=session_folder,
        recipe=recipe,
        webmap_json=webmap_json,
        preview_config=preview_config,
        review_packet_path=None,
    )
    state_started = time.perf_counter()
    response = _attach_composer_map_state(response, session_folder)
    timing["composer_state_ms"] = _elapsed_ms(state_started)
    response = _attach_timing(response, timing, started_at)
    _save_session_payload(session_folder, response)
    return response


def _can_use_fast_floodplain_fallback(session_folder: Path) -> bool:
    """Use the production fast path only for normal AutoMap output sessions."""
    try:
        session_folder.resolve().relative_to((repo_root() / COMPOSER_ROOT).resolve())
        return True
    except ValueError:
        return False


def generate_composer_draft(prompt: str) -> dict[str, Any]:
    """Generate one clean composer response without running analysis or publishing."""
    started_at = time.perf_counter()
    timing = _new_composer_timing()
    session_id = f"composer_{uuid4().hex[:12]}"
    session_folder = _session_path(session_id)
    session_folder.mkdir(parents=True, exist_ok=False)

    planner_started = time.perf_counter()
    planner_context = plan_with_ai(prompt)
    request_plan_override = planner_context.get("request_plan") if isinstance(planner_context, dict) else None
    ai_request_type = str((request_plan_override or {}).get("request_type") or "")
    if planner_context.get("planner_used") != "deterministic":
        timing["intelligence_ms"] += _elapsed_ms(planner_started)

    parse_started = time.perf_counter()
    table_classification = classify_table_request(prompt)
    if ai_request_type == "table_request":
        table_classification["table_requested"] = True
        table_classification.setdefault("map_and_table", (request_plan_override or {}).get("output_mode") == "map_and_table")
    timing["parse_ms"] = _elapsed_ms(parse_started)
    table_context: dict[str, Any] | None = None
    if table_classification.get("table_requested"):
        table_started = time.perf_counter()
        table_recipe = plan_table_query(prompt)
        preview = preview_table_rows(table_recipe)
        timing["intelligence_ms"] = _elapsed_ms(table_started)
        table_context = {
            "table_requested": True,
            "table_recipe": table_recipe,
            "preview_rows": preview.get("preview_rows") or [],
            "preview_status": "table_preview_live",
            "export_status": "export_ready" if table_recipe.get("export_ready") else "csv_export_draft_needs_refinement",
            "export_links": [],
            "warnings": table_recipe.get("warnings") or [],
            "status_message": (
                "Table preview live. CSV export ready."
                if table_recipe.get("export_ready")
                else "Table preview live. CSV export needs refinement before download."
            ),
        }
        if not table_classification.get("map_and_table"):
            response = {
                "composer_session_id": session_id,
                "prompt": prompt,
                "raw_prompt": prompt,
                "map_title": table_recipe.get("table_title"),
                "request_type": "table_request",
                "recipe": None,
                "webmap_json": None,
                "preview_config": None,
                "map_layout": None,
                "selected_layers": [],
                "warnings": table_recipe.get("warnings") or ["This looks like a table/data request."],
                "missing_data": table_recipe.get("missing_data_needed") or [],
                "can_preview": False,
                "can_analyze": False,
                "can_report": False,
                "preview_blockers": [],
                "next_action": "open_table_center",
                "table_context": table_context,
                "draft_only": True,
                "published": False,
                "created_at": _utc_now(),
            }
            response.update(_planner_response_fields(planner_context))
            response = _attach_timing(response, timing, started_at)
            _save_session_payload(session_folder, response)
            return response

    if _can_use_fast_floodplain_fallback(session_folder) and not live_floodplain_screening_enabled():
        fast_started = time.perf_counter()
        fast_parsed, fast_plan = _is_fast_floodplain_fallback_prompt(prompt)
        timing["intelligence_ms"] += _elapsed_ms(fast_started)
        if fast_parsed and fast_plan:
            return _fast_floodplain_fallback_response(
                prompt=prompt,
                parsed=fast_parsed,
                plan=fast_plan,
                session_id=session_id,
                session_folder=session_folder,
                timing=timing,
                started_at=started_at,
            )

    recipe_started = time.perf_counter()
    recipe = build_recipe(prompt, request_plan_override=request_plan_override) if request_plan_override else build_recipe(prompt)
    recipe["planner_used"] = planner_context.get("planner_used") or "deterministic"
    if planner_context.get("map_plan_summary"):
        recipe["map_plan_summary"] = planner_context["map_plan_summary"]
    timing["recipe_ms"] = _elapsed_ms(recipe_started)
    if _is_proximity_prompt(prompt) or ai_request_type == "proximity":
        try:
            proximity_started = time.perf_counter()
            proximity_result = run_proximity_request(
                prompt,
                allow_route_draft=True,
                resolve_property=False,
            )
            timing["nearest_facility_ms"] = _elapsed_ms(proximity_started)
            _merge_proximity_timing(timing, proximity_result)
        except Exception as exc:
            proximity_result = {
                "status": "needs_review",
                "raw_prompt": prompt,
                "origin_type": resolve_address_or_parcel_origin(prompt, match=False).get("origin_type"),
                "target_type": build_proximity_context(prompt).get("target_type"),
                "warnings": [f"Proximity workflow could not complete safely: {exc}"],
                "published": False,
            }
        _apply_proximity_result_to_recipe(recipe, prompt, proximity_result)
    else:
        floodplain_started = time.perf_counter()
        recipe = attach_floodplain_screening_result(recipe)
        timing["floodplain_screening_ms"] = _elapsed_ms(floodplain_started)
    recipe["map_title"] = generate_map_title(prompt, recipe=recipe, proximity_result=recipe.get("proximity_result"))
    preview_started = time.perf_counter()
    webmap_json = build_webmap_json(recipe)
    _write_session_files(session_folder, recipe, webmap_json)
    blockers = _preview_blockers(recipe)
    can_preview = _can_preview(recipe, webmap_json) and not blockers

    review_packet_path: Path | None = None
    if can_preview:
        review_started = time.perf_counter()
        review_packet_path = save_review_packet(prompt, recipe, webmap_json)
        timing["review_packet_ms"] = _elapsed_ms(review_started)
    preview_config = _augment_preview_config(_preview_config_for(review_packet_path or session_folder, can_preview), recipe, webmap_json)
    timing["preview_config_ms"] = _elapsed_ms(preview_started)

    response = _base_session_response(
        session_id=session_id,
        raw_prompt=prompt,
        session_folder=session_folder,
        recipe=recipe,
        webmap_json=webmap_json,
        preview_config=preview_config,
        review_packet_path=review_packet_path,
    )
    response.update(_planner_response_fields(planner_context))
    if table_context:
        response["table_context"] = table_context
        response["warnings"] = sorted({*[str(item) for item in response.get("warnings") or []], *[str(item) for item in table_context.get("warnings") or []]})
    state_started = time.perf_counter()
    response = _attach_composer_map_state(response, session_folder)
    timing["composer_state_ms"] = _elapsed_ms(state_started)
    response = _attach_timing(response, timing, started_at)
    _save_session_payload(session_folder, response)
    return response


def refine_composer_route(session_id: str) -> dict[str, Any]:
    """Attempt a slower road-following route after the initial composer preview is already available."""
    started_at = time.perf_counter()
    timing = _new_composer_timing()
    session = get_composer_session(session_id)
    session_folder = _session_path(session_id)
    prompt = str(session.get("raw_prompt") or session.get("prompt") or "").strip()
    if not prompt or not _is_proximity_prompt(prompt):
        raise ValueError("Route refinement requires a saved proximity composer session.")

    recipe = deepcopy(session.get("recipe") or {})
    if not recipe:
        recipe_started = time.perf_counter()
        recipe = build_recipe(prompt)
        timing["recipe_ms"] = _elapsed_ms(recipe_started)

    try:
        proximity_started = time.perf_counter()
        proximity_result = run_proximity_request(
            prompt,
            allow_route_draft=True,
            resolve_property=False,
        )
        timing["nearest_facility_ms"] = _elapsed_ms(proximity_started)
        _merge_proximity_timing(timing, proximity_result)
    except Exception as exc:
        previous_result = recipe.get("proximity_result") or {}
        proximity_result = {
            **previous_result,
            "status": previous_result.get("status") or "needs_review",
            "raw_prompt": prompt,
            "warnings": [
                *(previous_result.get("warnings") or []),
                f"Road-following route refinement could not complete safely: {exc}",
            ],
            "route_refinement_available": True,
            "route_refinement_status": "failed",
            "published": False,
        }

    _apply_proximity_result_to_recipe(recipe, prompt, proximity_result)
    recipe["map_title"] = generate_map_title(prompt, recipe=recipe, proximity_result=recipe.get("proximity_result"))
    preview_started = time.perf_counter()
    webmap_json = build_webmap_json(recipe)
    _write_session_files(session_folder, recipe, webmap_json)
    blockers = _preview_blockers(recipe)
    can_preview = _can_preview(recipe, webmap_json) and not blockers
    review_packet_path: Path | None = None
    if can_preview:
        review_started = time.perf_counter()
        review_packet_path = save_review_packet(prompt, recipe, webmap_json)
        timing["review_packet_ms"] = _elapsed_ms(review_started)
    preview_config = _augment_preview_config(_preview_config_for(review_packet_path or session_folder, can_preview), recipe, webmap_json)
    timing["preview_config_ms"] = _elapsed_ms(preview_started)

    response = _base_session_response(
        session_id=session_id,
        raw_prompt=prompt,
        session_folder=session_folder,
        recipe=recipe,
        webmap_json=webmap_json,
        preview_config=preview_config,
        review_packet_path=review_packet_path,
    )
    response["route_refinement_attempted"] = True
    response["route_refinement_status"] = proximity_result.get("route_refinement_status") or proximity_result.get("route_status")
    state_started = time.perf_counter()
    response = _attach_composer_map_state(response, session_folder)
    timing["composer_state_ms"] = _elapsed_ms(state_started)
    response = _attach_timing(response, timing, started_at)
    _save_session_payload(session_folder, response)
    return response


def get_composer_session(session_id: str) -> dict[str, Any]:
    """Return a previously created composer session."""
    session_folder = _session_path(session_id)
    path = session_folder / "composer_session.json"
    if not path.exists():
        raise FileNotFoundError(f"Composer session not found: {session_id}")
    session = _read_json(path)
    if not session.get("composer_map_state"):
        state_path = session_folder / "composer_map_state.json"
        if state_path.exists():
            session["composer_map_state"] = _read_json(state_path)
        else:
            try:
                saved_state = get_composer_map_state(session_id)
            except Exception:
                saved_state = None
            if saved_state:
                session["composer_map_state"] = saved_state
    return session


def update_composer_map_state_for_session(session_id: str, state_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persist current frontend map state options for a composer session."""
    session = get_composer_session(session_id)
    session_folder = _session_path(session_id)
    response = _attach_composer_map_state(session, session_folder, state_payload or {})
    _save_session_payload(session_folder, response)
    return response


def _simple_adjustments_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    layer_adjustments: dict[str, Any] = {}
    definition_expression_overrides: dict[str, str] = {}
    layer_order: list[str] = []
    for layer in payload.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        key = str(layer.get("layer_key") or layer.get("title") or "").strip()
        if not key:
            continue
        layer_order.append(key)
        adjustment: dict[str, Any] = {}
        for source_key in ("visibility", "opacity", "title", "role", "showLegend", "remove_layer"):
            if source_key in layer:
                adjustment[source_key] = layer[source_key]
        if adjustment:
            layer_adjustments[key] = adjustment
        expression = layer.get("definition_expression")
        if isinstance(expression, str) and expression.strip():
            definition_expression_overrides[key] = expression.strip()
    adjustments = {
        "map_title": payload.get("map_title"),
        "map_description": payload.get("map_description"),
        "layer_order": payload.get("layer_order") or layer_order,
        "layer_adjustments": layer_adjustments,
        "definition_expression_overrides": definition_expression_overrides,
        "reviewer_notes": [payload["notes"]] if payload.get("notes") else [],
        "publish_ready": False,
    }
    return normalize_adjustments(adjustments)


def apply_composer_adjustments(session_id: str, adjustment_payload: dict[str, Any]) -> dict[str, Any]:
    """Apply simple UI adjustments and return an updated preview response."""
    session = get_composer_session(session_id)
    session_folder = _session_path(session_id)
    recipe = deepcopy(session.get("recipe") or {})
    webmap_json = deepcopy(session.get("webmap_json") or {})
    adjustments = _simple_adjustments_from_payload(adjustment_payload)
    adjusted_recipe = apply_adjustments_to_recipe(recipe, adjustments)
    adjusted_webmap = apply_adjustments_to_webmap(webmap_json, adjustments)

    _write_json(session_folder / "adjusted_recipe.json", adjusted_recipe)
    _write_json(session_folder / "adjusted_webmap.json", adjusted_webmap)
    _write_json(session_folder / "applied_adjustments.json", adjustments)
    _write_layer_csv(session_folder / "adjusted_layer_list.csv", adjusted_recipe, adjusted_webmap)

    review_packet_path = Path(session["review_packet_path"]) if session.get("review_packet_path") else None
    adjusted_packet_path: Path | None = None
    if review_packet_path:
        adjusted_packet_path = write_adjusted_packet(review_packet_path, adjusted_recipe, adjusted_webmap, adjustments)
    can_preview = _can_preview(adjusted_recipe, adjusted_webmap)
    preview_config = _augment_preview_config(_preview_config_for(adjusted_packet_path or session_folder, can_preview), adjusted_recipe, adjusted_webmap)

    response = _base_session_response(
        session_id=session_id,
        raw_prompt=str(session.get("raw_prompt") or adjusted_recipe.get("user_intent") or ""),
        session_folder=session_folder,
        recipe=adjusted_recipe,
        webmap_json=adjusted_webmap,
        preview_config=preview_config,
        review_packet_path=review_packet_path,
        adjusted_packet_path=adjusted_packet_path,
    )
    response["applied_adjustments"] = adjustments
    response["next_action"] = "preview_adjusted_map" if can_preview else response["next_action"]
    response = _attach_composer_map_state(response, session_folder, adjustment_payload)
    _save_session_payload(session_folder, response)
    return response


def export_composer_session(session_id: str, export_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create local draft report/export links for a composer session."""
    session = update_composer_map_state_for_session(session_id, export_payload or {})
    packet_path = session.get("adjusted_packet_path") or session.get("review_packet_path")
    if not packet_path:
        raise ValueError("Composer export requires a preview-ready review packet.")
    package = generate_report(packet_path)
    report_files = [
        _file_link(path, name)
        for name, path in sorted(package.files.items())
    ]
    session_folder = _session_path(session_id)
    webmap_path = session_folder / ("adjusted_webmap.json" if (session_folder / "adjusted_webmap.json").exists() else "webmap.json")
    local_files = [
        _file_link(webmap_path, "webmap.json"),
        _file_link(session_folder / "review_summary.md", "review_summary.md"),
        _file_link(session_folder / "layer_list.csv", "layer_list.csv"),
    ]
    response = {
        **session,
        "export": {
            "report_id": package.report_id,
            "report_path": _repo_relative(package.report_path),
            "report_title": package.report_title,
            "files": [*report_files, *local_files],
            "validation": package.validation,
        },
        "can_report": True,
        "next_action": "print_or_export",
    }
    response = _attach_composer_map_state(response, session_folder, export_payload or {})
    _save_session_payload(session_folder, response)
    return response
