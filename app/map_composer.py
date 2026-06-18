"""Simple prompt-to-preview composer workflow for AutoMap."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import csv
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.adjustment_engine import apply_adjustments_to_recipe, apply_adjustments_to_webmap, write_adjusted_packet
from app.adjustment_models import normalize_adjustments
from app.address_parcel_resolver import ADDRESS_NOT_MATCHED_WARNING, resolve_address_or_parcel_origin
from app.composer_state_models import (
    default_north_arrow_config,
    default_scale_bar_config,
    normalize_report_section_config,
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
from app.recipe_engine import PARCEL_NOT_MATCHED_WARNING, build_recipe
from app.report_generator import generate_report
from app.report_section_models import build_report_sections
from app.report_statistics_builder import build_report_statistics
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
    validation = recipe.get("validation") or {}
    return [str(item) for item in validation.get("errors") or [] if item]


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


def _next_action(can_preview: bool, blockers: list[str]) -> str:
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
        "origin_match_status": status,
        "match_status": status,
        "candidate_matches": result.get("candidate_matches") or [],
        "related_parcel": related_parcel,
            "property_match_status": result.get("property_match_status") or ("not_resolved" if origin_type == "address" and status == "matched" and not related_parcel else None),
        "can_preview": result.get("status") == "ok",
        "reason_if_not_focusable": reason,
        "warnings": result.get("warnings") or [],
    }


def _proximity_map_title(result: dict[str, Any]) -> str:
    return generate_map_title("", proximity_result=result)


def _legend_label_for_overlay(overlay: dict[str, Any]) -> str:
    role = str(overlay.get("role") or overlay.get("geometry_role") or "").lower()
    symbol_key = str(overlay.get("symbol_key") or "")
    route_label = overlay.get("route_label")
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
                "label": label,
                "symbol_key": overlay.get("symbol_key"),
                "geometry_role": overlay.get("geometry_role") or overlay.get("role"),
                "route_mode": overlay.get("route_mode"),
                "source": "derived_overlay",
            }
        )
    for layer in config.get("context_layers") or []:
        if not isinstance(layer, dict):
            continue
        visible = layer.get("default_visible", layer.get("visibility", True))
        if visible is False:
            continue
        label = str(layer.get("title") or layer.get("layer_key") or "Context layer")
        dedupe_key = f"context:{label}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        items.append(
            {
                "label": label,
                "geometry_role": layer.get("role") or "context",
                "source": "context_layer",
            }
        )
    return items


def _build_map_layout(recipe: dict[str, Any], config: dict[str, Any] | None) -> dict[str, Any]:
    result = recipe.get("proximity_result") or {}
    route_label = _route_mode_label(result) if result else "Draft map"
    subtitle = _map_layout_subtitle(result) if result else "Draft AutoMap preview, not an official county map."
    return {
        "title": recipe.get("map_title") or (config or {}).get("map_title") or "AutoMap Draft Map",
        "subtitle": subtitle,
        "legend_items": _legend_items_from_preview(config),
        "scale_bar_enabled": True,
        "scale_bar_position": "bottom_center",
        "scale_bar_width_percent": 64,
        "scale_bar_style": "centered_enterprise",
        "north_arrow_enabled": True,
        "disclaimer": "Draft AutoMap preview - Local only - Not official county map",
        "route_mode_label": route_label,
        "print_ready": bool(config),
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
        "route_mode": result.get("route_mode") or "straight_line_reference",
        "road_route_supported": False,
        "straight_line_supported": True,
        "route_status": result.get("route_status"),
        "route_label": result.get("route_label"),
        "route_warning": result.get("route_warning"),
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
                    "title": result.get("route_label") or "Straight-line reference",
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
        if result.get("route_mode") == "straight_line_reference":
            _append_unique_warning(recipe, "Straight-line reference, not a driving route.")
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
    config["context_layers"] = config.get("operational_layers") or []
    config["warnings"] = _review_warnings(recipe, recipe.get("parcel_context") or {})
    overlays = recipe.get("derived_overlays") or (recipe.get("proximity_result") or {}).get("derived_overlays") or []
    if overlays:
        config["derived_overlays"] = overlays
        config["context_layers"] = _proximity_context_layers(config.get("context_layers") or [], recipe.get("proximity_result") or {})
        config["focus_mode"] = recipe.get("focus_mode") or "proximity"
        config["preview_status"] = recipe.get("preview_status") or "ready_for_proximity_preview"
        proximity_result = recipe.get("proximity_result") or {}
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


def _map_extent_from_response(response: dict[str, Any], preview_config: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
    if isinstance((payload or {}).get("active_map_extent"), dict):
        return (payload or {})["active_map_extent"]
    for key in ("focus_extent", "initial_extent"):
        if isinstance(preview_config.get(key), dict) and preview_config[key]:
            return preview_config[key]
    webmap = response.get("webmap_json") or {}
    target_geometry = (((webmap.get("initialState") or {}).get("viewpoint") or {}).get("targetGeometry") or {})
    return target_geometry if isinstance(target_geometry, dict) and target_geometry else None


def _build_composer_map_state(response: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    preview_config = _apply_payload_to_preview_config(response.get("preview_config") or {}, payload)
    layout = deepcopy(response.get("map_layout") or preview_config.get("map_layout") or {})
    map_title = str((payload or {}).get("map_title") or layout.get("title") or response.get("map_title") or "AutoMap Draft Map")
    map_subtitle = str((payload or {}).get("map_description") or layout.get("subtitle") or "Draft preview only. Not an official map.")
    layout["title"] = map_title
    layout["subtitle"] = map_subtitle
    layout.setdefault("scale_bar_enabled", True)
    layout.setdefault("scale_bar_position", "bottom_center")
    layout.setdefault("scale_bar_width_percent", 64)
    layout.setdefault("scale_bar_style", "centered_enterprise")
    layout.setdefault("north_arrow_enabled", True)
    preview_config["map_title"] = map_title
    preview_config["map_layout"] = layout
    extent = _map_extent_from_response(response, preview_config, payload)

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
    report_config = normalize_report_section_config((payload or {}).get("report_config") or (response.get("composer_map_state") or {}).get("report_section_config"))
    state = {
        "composer_session_id": response.get("composer_session_id"),
        "map_title": map_title,
        "map_subtitle": map_subtitle,
        "raw_prompt": response.get("raw_prompt") or response.get("prompt"),
        "request_type": response.get("request_type"),
        "preview_config": preview_config,
        "map_extent": extent,
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
        "warnings": response.get("warnings") or [],
        "missing_data": response.get("missing_data") or [],
        "reviewer_notes": (payload or {}).get("notes") or (response.get("composer_map_state") or {}).get("reviewer_notes") or "",
        "adjusted_state_applied": bool((payload or {}).get("layers") or response.get("applied_adjustments")),
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
    blockers = _preview_blockers(recipe)
    can_preview = _can_preview(recipe, webmap_json)
    if blockers:
        can_preview = False
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
        "origin_candidates": origin_context.get("candidate_matches") or parcel_context.get("candidate_matches") or [],
        "related_parcel": origin_context.get("related_parcel"),
        "proximity_result": proximity_result,
        "recipe": recipe,
        "webmap_json": webmap_json,
        "preview_config": preview_config,
        "map_layout": (preview_config or {}).get("map_layout") if isinstance(preview_config, dict) else None,
        "selected_layers": _selected_layers(recipe),
        "warnings": _review_warnings(recipe, parcel_context),
        "missing_data": recipe.get("missing_data_needed") or [],
        "parcel_context": parcel_context,
        "can_preview": can_preview,
        "can_analyze": _can_analyze(recipe),
        "can_report": bool(packet_path),
        "preview_blockers": blockers,
        "next_action": _next_action(can_preview, blockers),
        "simple_steps": [
            {"step": "Request", "status": "complete"},
            {"step": "Preview", "status": "blocked" if blockers else "complete" if can_preview else "pending"},
            {"step": "Adjust", "status": "pending" if can_preview else "blocked"},
            {"step": "Print / Export", "status": "pending" if can_preview else "blocked"},
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


def generate_composer_draft(prompt: str) -> dict[str, Any]:
    """Generate one clean composer response without running analysis or publishing."""
    session_id = f"composer_{uuid4().hex[:12]}"
    session_folder = _session_path(session_id)
    session_folder.mkdir(parents=True, exist_ok=False)

    recipe = build_recipe(prompt)
    if _is_proximity_prompt(prompt):
        try:
            proximity_result = run_proximity_request(prompt)
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
    recipe["map_title"] = generate_map_title(prompt, recipe=recipe, proximity_result=recipe.get("proximity_result"))
    webmap_json = build_webmap_json(recipe)
    _write_session_files(session_folder, recipe, webmap_json)
    blockers = _preview_blockers(recipe)
    can_preview = _can_preview(recipe, webmap_json) and not blockers

    review_packet_path: Path | None = None
    if can_preview:
        review_packet_path = save_review_packet(prompt, recipe, webmap_json)
    preview_config = _augment_preview_config(_preview_config_for(review_packet_path or session_folder, can_preview), recipe, webmap_json)

    response = _base_session_response(
        session_id=session_id,
        raw_prompt=prompt,
        session_folder=session_folder,
        recipe=recipe,
        webmap_json=webmap_json,
        preview_config=preview_config,
        review_packet_path=review_packet_path,
    )
    response = _attach_composer_map_state(response, session_folder)
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
