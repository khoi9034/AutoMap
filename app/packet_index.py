"""Local output packet discovery and sanitized map preview config helpers."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.data_gap_registry import data_gap_records_from_recipe
from app.ui_models import repo_root


OUTPUTS_ROOT = Path("outputs")
REVIEW_PACKET_FOLDER = "review_packets"
ADJUSTED_PACKET_FOLDER = "review_packets_adjusted"
APPROVED_PACKET_FOLDER = "review_packets_approved"
WEBMAP_FOLDER = "webmaps"

PROTECTED_PREVIEW_MARKERS = {
    ".env",
    "arcgis_password",
    "arcgis_username",
    "cfs",
    "cfs_dev",
    "database_url",
    "password",
    "postgres_admin_url",
    "secret",
    "token",
}


def _outputs_root() -> Path:
    root = OUTPUTS_ROOT
    return root.resolve() if root.is_absolute() else (repo_root() / root).resolve()


def _safe_output_path(path: str | Path) -> Path:
    candidate = Path(path)
    output_root = _outputs_root()
    if not candidate.is_absolute():
        parts = candidate.parts
        if parts and parts[0].lower() == "outputs":
            candidate = output_root.joinpath(*parts[1:])
        elif parts and parts[0] in {REVIEW_PACKET_FOLDER, ADJUSTED_PACKET_FOLDER, APPROVED_PACKET_FOLDER, WEBMAP_FOLDER}:
            candidate = output_root / candidate
        else:
            candidate = repo_root() / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise ValueError("Preview paths must stay inside AutoMap outputs.") from exc
    return resolved


def _output_relative_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        try:
            return (Path("outputs") / resolved.relative_to(_outputs_root())).as_posix()
        except ValueError:
            return Path(resolved.name).as_posix()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _folder_updated_at(path: Path) -> datetime:
    candidates = [path, *[item for item in path.iterdir() if item.is_file()]]
    latest = max(item.stat().st_mtime for item in candidates)
    return datetime.fromtimestamp(latest, tz=UTC)


def _packet_json_name(packet_type: str, kind: str) -> str:
    if packet_type == "approved":
        return "approved_webmap.json" if kind == "webmap" else "approved_recipe.json"
    if packet_type == "adjusted":
        return "adjusted_webmap.json" if kind == "webmap" else "adjusted_recipe.json"
    return "webmap.json" if kind == "webmap" else "recipe.json"


def _packet_type(path: Path) -> str | None:
    if (path / "approved_webmap.json").exists():
        return "approved"
    if (path / "adjusted_webmap.json").exists():
        return "adjusted"
    if (path / "webmap.json").exists():
        return "review"
    return None


def _packet_info(path: Path, packet_type: str) -> dict[str, Any]:
    webmap_path = path / _packet_json_name(packet_type, "webmap")
    recipe_path = path / _packet_json_name(packet_type, "recipe")
    webmap = _load_json(webmap_path) if webmap_path.exists() else {}
    recipe = _load_json(recipe_path) if recipe_path.exists() else {}
    approval_receipt = _load_json(path / "approval_receipt.json") if (path / "approval_receipt.json").exists() else {}
    publish_receipt = _load_json(path / "publish_receipt.json") if (path / "publish_receipt.json").exists() else {}
    smoke_receipt = _load_json(path / "smoke_test_receipt.json") if (path / "smoke_test_receipt.json").exists() else {}
    updated_at = _folder_updated_at(path)
    return {
        "packet_id": path.name,
        "packet_type": packet_type,
        "packet_path": _output_relative_path(path),
        "webmap_path": _output_relative_path(webmap_path),
        "recipe_path": _output_relative_path(recipe_path) if recipe_path.exists() else None,
        "map_title": recipe.get("map_title") or webmap.get("title") or path.name,
        "updated_at": updated_at.isoformat(),
        "preview_url": f"/preview/{path.name}",
        "final_publish_ready": approval_receipt.get("final_publish_ready"),
        "approval_block_reasons": approval_receipt.get("block_reasons") or [],
        "latest_publish_receipt": {
            "exists": bool(publish_receipt),
            "status": publish_receipt.get("status"),
            "published": publish_receipt.get("published"),
            "created_item": publish_receipt.get("created_item"),
            "real_publish_attempted": publish_receipt.get("real_publish_attempted"),
        },
        "latest_smoke_test_receipt": {
            "exists": bool(smoke_receipt),
            "dry_run": smoke_receipt.get("dry_run"),
            "item_created": smoke_receipt.get("item_created"),
            "blocked": smoke_receipt.get("blocked"),
        },
    }


def _list_packet_dirs(folder_name: str, packet_type: str) -> list[dict[str, Any]]:
    root = _outputs_root() / folder_name
    if not root.exists():
        return []
    packets = [
        _packet_info(path, packet_type)
        for path in root.iterdir()
        if path.is_dir() and _packet_type(path) == packet_type
    ]
    return sorted(packets, key=lambda item: item["updated_at"], reverse=True)


def list_review_packets() -> list[dict[str, Any]]:
    """List local review packet folders newest first."""
    return _list_packet_dirs(REVIEW_PACKET_FOLDER, "review")


def list_adjusted_packets() -> list[dict[str, Any]]:
    """List local adjusted packet folders newest first."""
    return _list_packet_dirs(ADJUSTED_PACKET_FOLDER, "adjusted")


def list_approved_packets() -> list[dict[str, Any]]:
    """List local approved packet folders newest first."""
    return _list_packet_dirs(APPROVED_PACKET_FOLDER, "approved")


def _list_webmap_files() -> list[dict[str, Any]]:
    root = _outputs_root() / WEBMAP_FOLDER
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in root.glob("*.json"):
        try:
            webmap = _load_json(path)
        except json.JSONDecodeError:
            continue
        updated_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
        rows.append(
            {
                "packet_id": path.stem,
                "packet_type": "webmap_json",
                "packet_path": _output_relative_path(path),
                "webmap_path": _output_relative_path(path),
                "recipe_path": None,
                "map_title": webmap.get("title") or path.stem,
                "updated_at": updated_at.isoformat(),
                "preview_url": f"/preview?path={_output_relative_path(path)}",
            }
        )
    return sorted(rows, key=lambda item: item["updated_at"], reverse=True)


def find_latest_packet() -> dict[str, Any] | None:
    """Return the latest adjusted, review, or generated WebMap draft."""
    packets = [*list_approved_packets(), *list_adjusted_packets(), *list_review_packets(), *_list_webmap_files()]
    if not packets:
        return None
    return sorted(packets, key=lambda item: item["updated_at"], reverse=True)[0]


def resolve_packet_id(packet_id: str | None) -> Path:
    """Resolve a packet id, output-relative path, or latest marker to a safe output path."""
    if not packet_id or packet_id == "latest":
        latest = find_latest_packet()
        if not latest:
            raise FileNotFoundError("No local AutoMap packets or WebMap drafts were found.")
        return _safe_output_path(latest["packet_path"])

    if any(separator in packet_id for separator in {"/", "\\"}) or packet_id.endswith(".json"):
        path = _safe_output_path(packet_id)
        if path.exists():
            return path
        raise FileNotFoundError(f"AutoMap preview source not found: {packet_id}")

    for folder_name in (APPROVED_PACKET_FOLDER, ADJUSTED_PACKET_FOLDER, REVIEW_PACKET_FOLDER):
        path = _outputs_root() / folder_name / packet_id
        if path.exists():
            return path.resolve()

    for item in _list_webmap_files():
        if item["packet_id"] == packet_id:
            return _safe_output_path(item["packet_path"])

    raise FileNotFoundError(f"AutoMap packet id not found: {packet_id}")


def get_packet_webmap_json(packet_folder: str | Path) -> dict[str, Any]:
    """Load the WebMap JSON for a review packet, adjusted packet, or WebMap file."""
    path = _safe_output_path(packet_folder)
    if path.is_file():
        return _load_json(path)
    for file_name in ("approved_webmap.json", "adjusted_webmap.json", "webmap.json"):
        candidate = path / file_name
        if candidate.exists():
            return _load_json(candidate)
    raise FileNotFoundError(f"No WebMap JSON found for preview source: {packet_folder}")


def get_packet_recipe_json(packet_folder: str | Path) -> dict[str, Any]:
    """Load the recipe JSON for a review or adjusted packet, if present."""
    path = _safe_output_path(packet_folder)
    if path.is_file():
        return {}
    for file_name in ("approved_recipe.json", "adjusted_recipe.json", "recipe.json"):
        candidate = path / file_name
        if candidate.exists():
            return _load_json(candidate)
    return {}


def _packet_warnings(path: Path, webmap_json: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    if path.is_dir() and (path / "adjusted_warnings.json").exists():
        return _load_json(path / "adjusted_warnings.json")
    if path.is_dir() and (path / "approved_warnings.json").exists():
        approved_warnings = _load_json(path / "approved_warnings.json")
        if "publish_ready" not in approved_warnings and "final_publish_ready" in approved_warnings:
            approved_warnings["publish_ready"] = approved_warnings["final_publish_ready"]
        return approved_warnings
    if path.is_dir() and (path / "warnings.json").exists():
        return _load_json(path / "warnings.json")
    warnings = [
        *[str(item) for item in recipe.get("review_reasons") or []],
        *[str(item) for item in webmap_json.get("autoMapWarnings") or []],
    ]
    return {"preview_warnings": sorted({warning for warning in warnings if warning})}


def _definition_expression(layer: dict[str, Any]) -> str | None:
    layer_definition = layer.get("layerDefinition") or {}
    expression = layer_definition.get("definitionExpression")
    if isinstance(expression, str) and expression.strip():
        return expression.strip()
    return None


def _drawing_info(layer: dict[str, Any]) -> dict[str, Any] | None:
    layer_definition = layer.get("layerDefinition") or {}
    drawing_info = layer_definition.get("drawingInfo") if isinstance(layer_definition, dict) else None
    return drawing_info if isinstance(drawing_info, dict) else None


def _parent_service_url(url: str | None) -> str | None:
    if not url:
        return None
    parts = url.rstrip("/").split("/")
    if parts and parts[-1].isdigit():
        return "/".join(parts[:-1])
    return url.rstrip("/")


def _layer_id_from_url(url: str | None) -> int | None:
    if not url:
        return None
    last = url.rstrip("/").split("/")[-1]
    if last.isdigit():
        return int(last)
    return None


def _preview_layer_type(layer: dict[str, Any], layer_url: str | None, service_url: str | None, layer_id: int | None) -> str:
    if layer.get("autoMapDerivedAnalysis") or str(layer.get("layerType") or "").lower() == "geojsonlayer":
        return "local_geojson"
    text = f"{layer_url or ''} {service_url or ''}".lower()
    if "featureserver" in text:
        return "feature_layer"
    if "mapserver" in text and layer_id is not None:
        return "map_image_sublayer"
    if "mapserver" in text:
        return "map_image_layer"
    return "unsupported"


def _preview_layers(webmap_json: dict[str, Any]) -> list[dict[str, Any]]:
    layers: list[dict[str, Any]] = []
    for index, layer in enumerate(webmap_json.get("operationalLayers") or []):
        layer_url = layer.get("layerUrl") or layer.get("url")
        layer_id = layer.get("layerId")
        if layer_id is None:
            layer_id = _layer_id_from_url(str(layer_url) if layer_url else None)
        try:
            layer_id = int(layer_id) if layer_id is not None else None
        except (TypeError, ValueError):
            layer_id = None
        service_url = layer.get("serviceUrl") or _parent_service_url(str(layer_url) if layer_url else None)
        preview_type = _preview_layer_type(layer, str(layer_url) if layer_url else None, str(service_url) if service_url else None, layer_id)
        layers.append(
            {
                "id": layer.get("id") or f"automap_preview_{index}",
                "title": layer.get("title") or layer.get("autoMapLayerKey") or f"Layer {index + 1}",
                "layer_key": layer.get("autoMapLayerKey"),
                "role": layer.get("autoMapRole"),
                "category": layer.get("autoMapCategory"),
                "source_status": layer.get("autoMapSourceStatus"),
                "source_priority": layer.get("autoMapSourcePriority"),
                "confidence_score": layer.get("autoMapConfidence"),
                "url": layer.get("url"),
                "layer_url": layer_url,
                "service_url": service_url,
                "layer_id": layer_id,
                "preview_type": preview_type,
                "visibility": bool(layer.get("visibility", True)),
                "opacity": layer.get("opacity", 1),
                "show_legend": bool(layer.get("showLegend", True)),
                "definition_expression": _definition_expression(layer),
                "drawing_info": _drawing_info(layer),
                "review_warnings": [str(item) for item in layer.get("autoMapReviewWarnings") or []],
                "derived_local_analysis": bool(layer.get("autoMapDerivedAnalysis") or preview_type == "local_geojson"),
                "analysis_run_id": layer.get("autoMapAnalysisRunId"),
                "display_role": layer.get("autoMapDisplayRole"),
                "draw_order": layer.get("autoMapDrawOrder", index),
            }
        )
    return layers


def _initial_extent(webmap_json: dict[str, Any], recipe: dict[str, Any]) -> dict[str, Any]:
    viewpoint = ((webmap_json.get("initialState") or {}).get("viewpoint") or {})
    target = viewpoint.get("targetGeometry")
    if isinstance(target, dict):
        return target
    suggested = recipe.get("suggested_extent")
    return suggested if isinstance(suggested, dict) else {}


def _iter_strings(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            values.append(str(key))
            values.extend(_iter_strings(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_iter_strings(item))
    elif isinstance(value, str):
        values.append(value)
    return values


def _protected_preview_marker(value: Any) -> str | None:
    for text in _iter_strings(value):
        lowered = text.lower()
        for marker in sorted(PROTECTED_PREVIEW_MARKERS):
            if marker in lowered:
                return marker
    return None


def _redact_preview_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            safe_key = "[redacted]" if any(marker in key_text.lower() for marker in PROTECTED_PREVIEW_MARKERS) else key
            redacted[safe_key] = _redact_preview_value(item)
        return redacted
    if isinstance(value, list):
        return [_redact_preview_value(item) for item in value]
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker in lowered for marker in PROTECTED_PREVIEW_MARKERS):
            return "[redacted]"
    return value


def build_preview_config(packet_source: str | Path | None = None) -> dict[str, Any]:
    """Build a browser-safe preview config from local AutoMap output artifacts."""
    path = resolve_packet_id(str(packet_source) if packet_source else "latest")
    webmap_json = get_packet_webmap_json(path)
    recipe = get_packet_recipe_json(path)
    warnings = _packet_warnings(path, webmap_json, recipe)
    packet_type = "webmap_json" if path.is_file() else (_packet_type(path) or "unknown")
    recipe_summary = webmap_json.get("autoMapRecipeSummary") or {}
    parcel_context = recipe.get("parcel_context") or recipe_summary.get("parcel_context") or {}
    derived_overlays = recipe.get("derived_overlays") or recipe_summary.get("derived_overlays") or []
    proximity_result = recipe.get("proximity_result") or recipe_summary.get("proximity_result") or {}
    preview_status = recipe.get("preview_status") or recipe_summary.get("preview_status")
    focus_mode = recipe.get("focus_mode") or recipe_summary.get("focus_mode")
    can_focus_map = parcel_context.get("can_focus_map") if isinstance(parcel_context, dict) else None
    parcel_preview_blocked = bool(parcel_context and can_focus_map is False)
    config = {
        "map_title": recipe.get("map_title") or webmap_json.get("title") or "AutoMap Draft Preview",
        "original_prompt": recipe.get("user_intent") or recipe.get("parsed_request", {}).get("raw_prompt") or "",
        "initial_extent": _initial_extent(webmap_json, recipe),
        "operational_layers": _preview_layers(webmap_json),
        "warnings": warnings,
        "missing_data": recipe.get("missing_data_needed") or webmap_json.get("autoMapRecipeSummary", {}).get("missing_data_needed") or [],
        "data_gaps": data_gap_records_from_recipe(recipe) if recipe else [],
        "packet_id": path.stem if path.is_file() else path.name,
        "packet_path": _output_relative_path(path),
        "webmap_path": _output_relative_path(
            path if path.is_file() else path / _packet_json_name(packet_type if packet_type in {"approved", "adjusted"} else "review", "webmap")
        ),
        "draft_status": (
            "approved_review"
            if packet_type == "approved"
            else ("adjusted_review" if packet_type == "adjusted" else ("webmap_draft" if packet_type == "webmap_json" else "review_packet"))
        ),
        "parcel_context": parcel_context,
        "preview_status": preview_status,
        "focus_mode": focus_mode,
        "can_focus_map": can_focus_map,
        "parcel_preview_blocked": parcel_preview_blocked,
        "derived_overlays": derived_overlays,
        "proximity_result": proximity_result,
        "publish_ready": warnings.get("publish_ready") if isinstance(warnings, dict) else None,
        "preview_only": True,
    }
    config = _redact_preview_value(config)
    marker = _protected_preview_marker(config)
    if marker:
        raise ValueError(f"Preview config contains protected marker: {marker}")
    return config
