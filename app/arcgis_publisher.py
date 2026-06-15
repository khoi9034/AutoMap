"""Safe ArcGIS draft publisher for AutoMap approved packets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from app.portal_profiles import get_portal_profile, real_publish_profile_block_reasons


REQUIRED_ADJUSTED_PUBLISH_FILES = {
    "adjusted_recipe.json",
    "adjusted_webmap.json",
    "applied_adjustments.json",
    "adjusted_warnings.json",
}

REQUIRED_APPROVED_PUBLISH_FILES = {
    "approved_recipe.json",
    "approved_webmap.json",
    "approval_file.json",
    "approval_receipt.json",
    "approved_warnings.json",
}

PUBLISH_TAGS = [
    "AutoMap",
    "Draft",
    "GIS Request Engine",
    "Cabarrus County",
    "Human Review Required",
]

PROTECTED_RECEIPT_MARKERS = {
    "password",
    "token",
    "secret",
    "cfs",
    "cfs_dev",
    "database_url",
    "postgres_admin_url",
}


@dataclass(frozen=True)
class ArcGISPublishSettings:
    """ArcGIS publishing settings loaded from environment variables."""

    portal_url: str
    username: str | None
    password: str | None
    target_folder: str
    publish_env: str
    dry_run: bool
    allow_real_publish: bool


def _parse_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _all_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            strings.extend(_all_strings(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(_all_strings(item))
    elif isinstance(value, str):
        strings.append(value)
    return strings


def _contains_protected_reference(value: Any) -> str | None:
    combined = "\n".join(_all_strings(value)).lower()
    for marker in sorted(PROTECTED_RECEIPT_MARKERS):
        if marker in combined:
            return marker
    return None


def _packet_type(packet_path: Path) -> str:
    if (packet_path / "approved_webmap.json").exists():
        return "approved"
    return "adjusted"


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text_value = str(value).strip()
        if text_value and text_value not in seen:
            deduped.append(text_value)
            seen.add(text_value)
    return deduped


def _selected_layers(recipe: dict[str, Any], webmap: dict[str, Any]) -> list[dict[str, Any]]:
    recipe_lookup = {
        layer.get("layer_key"): layer
        for layer in recipe.get("selected_layers") or []
        if isinstance(layer, dict) and layer.get("layer_key")
    }
    rows: list[dict[str, Any]] = []
    for layer in webmap.get("operationalLayers") or []:
        layer_key = layer.get("autoMapLayerKey")
        recipe_layer = recipe_lookup.get(layer_key, {})
        rows.append(
            {
                "layer_key": layer_key,
                "title": layer.get("title") or recipe_layer.get("layer_name"),
                "role": layer.get("autoMapRole") or recipe_layer.get("role"),
                "url": layer.get("url") or layer.get("layerUrl") or recipe_layer.get("layer_url"),
                "source_status": layer.get("autoMapSourceStatus") or recipe_layer.get("source_status"),
            }
        )
    return rows


def _definition_expressions(webmap: dict[str, Any]) -> list[dict[str, str]]:
    expressions: list[dict[str, str]] = []
    for layer in webmap.get("operationalLayers") or []:
        expression = (layer.get("layerDefinition") or {}).get("definitionExpression")
        if isinstance(expression, str) and expression.strip():
            expressions.append(
                {
                    "layer": str(layer.get("title") or layer.get("autoMapLayerKey") or "Layer"),
                    "expression": expression.strip(),
                }
            )
    return expressions


def _warning_summary(warnings_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "final_publish_ready": warnings_payload.get("final_publish_ready"),
        "active": warnings_payload.get("active") or {},
        "block_reasons": warnings_payload.get("block_reasons") or [],
        "resolved_warnings": warnings_payload.get("resolved_warnings") or [],
        "accepted_warnings": warnings_payload.get("accepted_warnings") or [],
        "kept_non_blocking_warnings": warnings_payload.get("kept_non_blocking_warnings") or [],
    }


def _approval_receipt_summary(approval_receipt: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": approval_receipt.get("decision"),
        "final_publish_ready": approval_receipt.get("final_publish_ready"),
        "approved_at": approval_receipt.get("approved_at"),
        "block_reasons": approval_receipt.get("block_reasons") or [],
        "reviewer_notes": approval_receipt.get("reviewer_notes") or [],
        "accepted_risks": approval_receipt.get("accepted_risks") or [],
    }


def _load_packet_payload(packet_path: Path, packet_type: str) -> dict[str, Any]:
    if packet_type == "approved":
        return {
            "recipe": _load_json(packet_path / "approved_recipe.json") if (packet_path / "approved_recipe.json").exists() else {},
            "webmap": _load_json(packet_path / "approved_webmap.json") if (packet_path / "approved_webmap.json").exists() else {},
            "warnings": _load_json(packet_path / "approved_warnings.json") if (packet_path / "approved_warnings.json").exists() else {},
            "approval_receipt": _load_json(packet_path / "approval_receipt.json") if (packet_path / "approval_receipt.json").exists() else {},
        }
    return {
        "recipe": _load_json(packet_path / "adjusted_recipe.json") if (packet_path / "adjusted_recipe.json").exists() else {},
        "webmap": _load_json(packet_path / "adjusted_webmap.json") if (packet_path / "adjusted_webmap.json").exists() else {},
        "warnings": _load_json(packet_path / "adjusted_warnings.json") if (packet_path / "adjusted_warnings.json").exists() else {},
        "approval_receipt": {},
    }


def load_arcgis_publish_settings(load_env_file: bool = True) -> ArcGISPublishSettings:
    """Load ArcGIS publishing settings without printing or exposing secrets."""
    if load_env_file:
        load_dotenv()
    return ArcGISPublishSettings(
        portal_url=os.getenv("ARCGIS_PORTAL_URL", "https://www.arcgis.com").rstrip("/"),
        username=os.getenv("ARCGIS_USERNAME"),
        password=os.getenv("ARCGIS_PASSWORD"),
        target_folder=os.getenv("ARCGIS_TARGET_FOLDER", "AutoMap Drafts"),
        publish_env=get_portal_profile(os.getenv("ARCGIS_PUBLISH_ENV", "dev")).name,
        dry_run=_parse_bool(os.getenv("AUTOMAP_PUBLISH_DRY_RUN"), default=True),
        allow_real_publish=_parse_bool(os.getenv("AUTOMAP_ALLOW_REAL_PUBLISH"), default=False),
    )


def connect_to_arcgis(settings: ArcGISPublishSettings | None = None) -> Any:
    """Connect to ArcGIS only for explicitly confirmed real publishing."""
    loaded_settings = settings or load_arcgis_publish_settings()
    if not loaded_settings.username or not loaded_settings.password:
        raise ValueError("ArcGIS username/password are not configured.")
    try:
        from arcgis.gis import GIS
    except ImportError as exc:
        raise ValueError("ArcGIS API for Python is not installed.") from exc
    return GIS(loaded_settings.portal_url, loaded_settings.username, loaded_settings.password)


def check_arcgis_connection(settings: ArcGISPublishSettings | None = None) -> dict[str, Any]:
    """Check ArcGIS credentials safely and return non-secret status."""
    loaded_settings = settings or load_arcgis_publish_settings()
    if not loaded_settings.username or not loaded_settings.password:
        return {
            "connected": False,
            "portal_url": loaded_settings.portal_url,
            "publish_env": loaded_settings.publish_env,
            "username_configured": bool(loaded_settings.username),
            "password_configured": bool(loaded_settings.password),
            "target_folder": loaded_settings.target_folder,
            "dry_run_default": loaded_settings.dry_run,
            "real_publish_enabled": loaded_settings.allow_real_publish,
            "error": "ArcGIS credentials are not fully configured.",
        }
    try:
        gis = connect_to_arcgis(loaded_settings)
        user = getattr(getattr(gis, "users", None), "me", None)
        username = getattr(user, "username", loaded_settings.username)
    except Exception as exc:
        return {
            "connected": False,
            "portal_url": loaded_settings.portal_url,
            "publish_env": loaded_settings.publish_env,
            "username_configured": True,
            "password_configured": True,
            "target_folder": loaded_settings.target_folder,
            "dry_run_default": loaded_settings.dry_run,
            "real_publish_enabled": loaded_settings.allow_real_publish,
            "error": str(exc),
        }
    return {
        "connected": True,
        "portal_url": loaded_settings.portal_url,
        "publish_env": loaded_settings.publish_env,
        "username": username,
        "target_folder": loaded_settings.target_folder,
        "dry_run_default": loaded_settings.dry_run,
        "real_publish_enabled": loaded_settings.allow_real_publish,
    }


def validate_publish_packet(adjusted_packet_folder: str | Path, *, require_approved: bool = False) -> dict[str, Any]:
    """Validate an adjusted or approved packet before dry-run or real publishing."""
    packet_path = Path(adjusted_packet_folder)
    errors: list[str] = []
    warnings: list[str] = []

    if not packet_path.exists() or not packet_path.is_dir():
        return {
            "is_valid": False,
            "errors": [f"Adjusted packet folder not found: {packet_path}"],
            "warnings": [],
            "packet_path": str(packet_path),
        }

    packet_type = _packet_type(packet_path)
    required_files = REQUIRED_APPROVED_PUBLISH_FILES if packet_type == "approved" else REQUIRED_ADJUSTED_PUBLISH_FILES
    missing_files = sorted(file_name for file_name in required_files if not (packet_path / file_name).exists())
    if missing_files:
        errors.append(f"Missing required {packet_type} publish files: {', '.join(missing_files)}")
    raw_review_files = {"recipe.json", "webmap.json"} & {path.name for path in packet_path.iterdir() if path.is_file()}
    if raw_review_files:
        errors.append("Raw review packets cannot be published; create an adjusted and approved packet first.")
    if require_approved and packet_type != "approved":
        errors.append("Real publishing requires an approved packet with final_publish_ready=true.")

    recipe: dict[str, Any] = {}
    webmap: dict[str, Any] = {}
    warnings_payload: dict[str, Any] = {}
    approval_receipt: dict[str, Any] = {}
    if not missing_files:
        try:
            if packet_type == "approved":
                recipe = _load_json(packet_path / "approved_recipe.json")
                webmap = _load_json(packet_path / "approved_webmap.json")
                _load_json(packet_path / "approval_file.json")
                warnings_payload = _load_json(packet_path / "approved_warnings.json")
                approval_receipt = _load_json(packet_path / "approval_receipt.json")
            else:
                recipe = _load_json(packet_path / "adjusted_recipe.json")
                webmap = _load_json(packet_path / "adjusted_webmap.json")
                _load_json(packet_path / "applied_adjustments.json")
                warnings_payload = _load_json(packet_path / "adjusted_warnings.json")
        except json.JSONDecodeError as exc:
            errors.append(f"{packet_type.title()} packet JSON is invalid: {exc}")

    webmap_file_name = "approved_webmap.json" if packet_type == "approved" else "adjusted_webmap.json"
    if webmap and not webmap.get("operationalLayers"):
        errors.append(f"{webmap_file_name} has no operationalLayers.")
    for index, layer in enumerate(webmap.get("operationalLayers") or []):
        if not layer.get("title"):
            errors.append(f"Operational layer {index} is missing title.")
        if not layer.get("url"):
            errors.append(f"Operational layer {layer.get('title') or index} is missing URL.")

    if packet_type == "approved":
        if approval_receipt.get("final_publish_ready") is not True:
            errors.append("Approved packet final_publish_ready must be true before publishing.")
        if approval_receipt.get("block_reasons"):
            errors.append("Publishing blocked because approval block reasons remain.")
    elif warnings_payload:
        if warnings_payload.get("publish_ready") is not True:
            errors.append("Adjusted packet publish_ready must be true before publishing.")
        active = warnings_payload.get("active") or {}
        unresolved = {group: values for group, values in active.items() if values}
        if unresolved:
            errors.append("Publishing blocked because unresolved warnings or blockers remain.")

    protected_marker = _contains_protected_reference(
        {
            "recipe": recipe,
            "webmap": webmap,
            "warnings": warnings_payload,
            "approval_receipt": approval_receipt,
        }
    )
    if protected_marker:
        errors.append(f"{packet_type.title()} packet contains protected reference: {protected_marker}")

    return {
        "is_valid": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "packet_path": str(packet_path),
        "packet_type": packet_type,
        "publish_ready": approval_receipt.get("final_publish_ready") if packet_type == "approved" else warnings_payload.get("publish_ready"),
        "operational_layer_count": len(webmap.get("operationalLayers") or []),
    }


def build_item_properties(
    adjusted_recipe: dict[str, Any],
    adjusted_webmap: dict[str, Any],
    approval_receipt: dict[str, Any] | None = None,
    warnings_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build private ArcGIS Web Map item properties from approved draft content."""
    raw_title = adjusted_recipe.get("map_title") or adjusted_webmap.get("title") or "Untitled AutoMap Draft"
    title = str(raw_title)
    if not title.startswith("AutoMap Draft -"):
        title = f"AutoMap Draft - {title}"
    approval = approval_receipt or {}
    warning_summary = _warning_summary(warnings_payload or {})
    selected = _selected_layers(adjusted_recipe, adjusted_webmap)
    selected_layer_lines = [
        f"- {layer.get('title') or layer.get('layer_key')}: {layer.get('url') or 'URL unavailable'}"
        for layer in selected
    ]
    reviewer_notes = [str(note) for note in approval.get("reviewer_notes") or []]
    block_reasons = [
        *[str(reason) for reason in approval.get("block_reasons") or []],
        *[str(reason) for reason in warning_summary.get("block_reasons") or []],
    ]
    description_lines = [
        adjusted_recipe.get("map_description") or adjusted_webmap.get("description") or "AutoMap approved draft Web Map.",
        "",
        "Draft-only disclaimer: this private Web Map requires GIS review before official use.",
        "",
        "Reviewer approval notes:",
        *(f"- {note}" for note in reviewer_notes),
        *(["- No reviewer notes recorded."] if not reviewer_notes else []),
        "",
        "Selected layers:",
        *(selected_layer_lines or ["- No selected layers recorded."]),
        "",
        "Warnings and block reasons:",
        *(f"- {reason}" for reason in block_reasons),
        *(["- No unresolved block reasons recorded."] if not block_reasons else []),
    ]
    snippet = "Draft web map generated by AutoMap. Requires GIS review before official use."
    return {
        "title": title,
        "type": "Web Map",
        "typeKeywords": "Web Map, Map, Online Map, AutoMap, Draft",
        "tags": list(PUBLISH_TAGS),
        "snippet": snippet,
        "description": "\n".join(description_lines).strip(),
        "text": json.dumps(adjusted_webmap, indent=2, default=str),
        "accessInformation": "AutoMap draft generated from verified ArcGIS REST metadata.",
        "licenseInfo": "Private internal draft. Human review required before any external use.",
    }


def _private_publish_result(
    *,
    packet_path: Path,
    item_properties: dict[str, Any],
    dry_run: bool,
    validation: dict[str, Any],
    settings: ArcGISPublishSettings | None,
    payload: dict[str, Any],
    block_reasons: list[str] | None = None,
    real_publish_attempted: bool = False,
    item: Any | None = None,
) -> dict[str, Any]:
    block_reason_list = _dedupe([str(reason) for reason in block_reasons or []])
    created_item = item is not None and not dry_run and not block_reason_list
    item_url = getattr(item, "url", None) if item is not None else None
    if item_url is None and item is not None and getattr(item, "id", None):
        portal = (settings.portal_url if settings else "").rstrip("/")
        item_url = f"{portal}/home/item.html?id={getattr(item, 'id', None)}" if portal else None
    packet_type = validation.get("packet_type")
    approval_receipt = payload.get("approval_receipt") or {}
    webmap = payload.get("webmap") or {}
    recipe = payload.get("recipe") or {}
    result = {
        "status": "blocked" if block_reason_list else ("dry_run" if dry_run else "published_private_draft"),
        "dry_run": dry_run,
        "real_publish_attempted": real_publish_attempted,
        "published": created_item,
        "created_item": created_item,
        "item_id": getattr(item, "id", None) if item is not None else None,
        "item_url": item_url,
        "portal_url": settings.portal_url if settings else None,
        "publish_env": settings.publish_env if settings else None,
        "target_folder": settings.target_folder if settings else None,
        "item_title": item_properties["title"],
        "shared_public": False,
        "shared_organization": False,
        "overwrite_used": False,
        "delete_used": False,
        "approved_packet_path": str(packet_path) if packet_type == "approved" else None,
        "packet_path": str(packet_path),
        "title": item_properties["title"],
        "item_type": item_properties["type"],
        "tags": PUBLISH_TAGS,
        "approval_receipt_summary": _approval_receipt_summary(approval_receipt),
        "selected_layers": _selected_layers(recipe, webmap),
        "definition_expressions": _definition_expressions(webmap),
        "warnings": _warning_summary(payload.get("warnings") or {}),
        "reviewer_name": approval_receipt.get("reviewer_name"),
        "validation": validation,
        "published_at": datetime.now(UTC).isoformat(),
        "block_reasons": block_reason_list,
        "cfs_database_not_touched": True,
    }
    return result


def write_publish_receipt(adjusted_packet_folder: str | Path, publish_result: dict[str, Any]) -> Path:
    """Write a non-secret publish receipt inside the adjusted packet folder."""
    packet_path = Path(adjusted_packet_folder)
    safe_result = dict(publish_result)
    safe_result.pop("password", None)
    safe_result.pop("token", None)
    safe_result.pop("credentials", None)
    protected_marker = _contains_protected_reference(safe_result)
    if protected_marker:
        raise ValueError(f"Publish receipt contains protected or secret marker: {protected_marker}")
    receipt_path = packet_path / "publish_receipt.json"
    _write_json(receipt_path, safe_result)
    return receipt_path


def _credential_missing_or_placeholder(value: str | None) -> bool:
    if value is None:
        return True
    stripped = value.strip()
    if not stripped:
        return True
    return stripped.lower() in {"your_username", "your_password", "username", "password"}


def _real_publish_block_reasons(
    *,
    validation: dict[str, Any],
    settings: ArcGISPublishSettings,
    confirm_publish: bool,
) -> list[str]:
    reasons: list[str] = [str(error) for error in validation.get("errors") or []]
    if validation.get("packet_type") != "approved":
        reasons.append("Real publishing requires an approved packet with final_publish_ready=true.")
    if validation.get("publish_ready") is not True:
        reasons.append("Approved packet final_publish_ready must be true before real publishing.")
    if not confirm_publish:
        reasons.append("Real publishing requires --confirm-publish.")
    if not settings.allow_real_publish:
        reasons.append("AUTOMAP_ALLOW_REAL_PUBLISH must be true for real publishing.")
    if settings.dry_run:
        reasons.append("AUTOMAP_PUBLISH_DRY_RUN must be false for real publishing.")
    if _credential_missing_or_placeholder(settings.username) or _credential_missing_or_placeholder(settings.password):
        reasons.append("ArcGIS credentials are not fully configured.")
    if not settings.target_folder or not settings.target_folder.strip():
        reasons.append("ARCGIS_TARGET_FOLDER must be configured.")
    reasons.extend(
        real_publish_profile_block_reasons(
            settings.publish_env,
            allow_real_publish=settings.allow_real_publish,
            confirm_publish=confirm_publish,
        )
    )
    return _dedupe(reasons)


def _ensure_target_folder(gis: Any, target_folder: str) -> str:
    """Create or reuse an ArcGIS content folder without touching existing items."""
    folder_name = target_folder.strip()
    if not folder_name:
        raise ValueError("ARCGIS_TARGET_FOLDER must be configured.")

    user = getattr(getattr(gis, "users", None), "me", None)
    folders = getattr(user, "folders", None) or []
    for folder in folders:
        title = folder.get("title") if isinstance(folder, dict) else getattr(folder, "title", None)
        if title == folder_name:
            return "existing"

    content = getattr(gis, "content", None)
    create_folder = getattr(content, "create_folder", None)
    if callable(create_folder):
        create_folder(folder_name)
        return "created"

    user_create_folder = getattr(user, "create_folder", None)
    if callable(user_create_folder):
        user_create_folder(folder_name)
        return "created"

    return "not_checked"


def publish_webmap_draft(
    adjusted_packet_folder: str | Path,
    dry_run: bool = True,
    confirm_publish: bool = False,
) -> dict[str, Any]:
    """Publish an approved packet as a private draft, or dry-run by default."""
    packet_path = Path(adjusted_packet_folder)
    validation = validate_publish_packet(packet_path, require_approved=not dry_run)
    packet_type = validation.get("packet_type") or _packet_type(packet_path)
    payload = _load_packet_payload(packet_path, packet_type) if packet_path.exists() and packet_path.is_dir() else {
        "recipe": {},
        "webmap": {},
        "warnings": {},
        "approval_receipt": {},
    }
    item_properties = build_item_properties(
        payload["recipe"],
        payload["webmap"],
        payload.get("approval_receipt"),
        payload.get("warnings"),
    )
    settings: ArcGISPublishSettings | None = None
    settings_errors: list[str] = []
    try:
        settings = load_arcgis_publish_settings()
    except ValueError as exc:
        settings_errors.append(str(exc))

    if settings_errors:
        result = {
            "status": "blocked",
            "dry_run": dry_run,
            "real_publish_attempted": False,
            "created_item": False,
            "published": False,
            "item_id": None,
            "item_url": None,
            "portal_url": None,
            "target_folder": None,
            "item_title": item_properties["title"],
            "shared_public": False,
            "shared_organization": False,
            "overwrite_used": False,
            "delete_used": False,
            "approved_packet_path": str(packet_path) if packet_type == "approved" else None,
            "packet_path": str(packet_path),
            "title": item_properties["title"],
            "item_type": item_properties["type"],
            "tags": PUBLISH_TAGS,
            "approval_receipt_summary": _approval_receipt_summary(payload.get("approval_receipt") or {}),
            "selected_layers": _selected_layers(payload.get("recipe") or {}, payload.get("webmap") or {}),
            "definition_expressions": _definition_expressions(payload.get("webmap") or {}),
            "warnings": _warning_summary(payload.get("warnings") or {}),
            "reviewer_name": (payload.get("approval_receipt") or {}).get("reviewer_name"),
            "validation": validation,
            "block_reasons": _dedupe([*settings_errors, *[str(error) for error in validation.get("errors") or []]]),
            "cfs_database_not_touched": True,
            "blocked_at": datetime.now(UTC).isoformat(),
        }
        if packet_path.exists() and packet_path.is_dir():
            write_publish_receipt(packet_path, result)
        return result

    if settings is None:
        raise ValueError("ArcGIS publish settings could not be loaded.")

    if dry_run:
        block_reasons = [] if validation["is_valid"] else [str(error) for error in validation.get("errors") or []]
        result = _private_publish_result(
            packet_path=packet_path,
            item_properties=item_properties,
            dry_run=True,
            validation=validation,
            settings=settings,
            payload=payload,
            block_reasons=block_reasons,
        )
        result["message"] = (
            "Dry-run only. No ArcGIS connection was opened and no item was created."
            if not block_reasons
            else "Dry-run blocked by packet validation. No ArcGIS connection was opened."
        )
        if packet_path.exists() and packet_path.is_dir():
            write_publish_receipt(packet_path, result)
        return result

    block_reasons = _real_publish_block_reasons(
        validation=validation,
        settings=settings,
        confirm_publish=confirm_publish,
    )
    if block_reasons:
        result = _private_publish_result(
            packet_path=packet_path,
            item_properties=item_properties,
            dry_run=False,
            validation=validation,
            settings=settings,
            payload=payload,
            block_reasons=block_reasons,
            real_publish_attempted=False,
        )
        result["message"] = "Real publish blocked. No ArcGIS connection was opened and no item was created."
        if packet_path.exists() and packet_path.is_dir():
            write_publish_receipt(packet_path, result)
        return result

    folder_status = "not_checked"
    try:
        gis = connect_to_arcgis(settings)
        folder_status = _ensure_target_folder(gis, settings.target_folder)
        item = gis.content.add(
            item_properties=item_properties,
            data=None,
            folder=settings.target_folder,
        )
    except Exception:
        result = _private_publish_result(
            packet_path=packet_path,
            item_properties=item_properties,
            dry_run=False,
            validation=validation,
            settings=settings,
            payload=payload,
            block_reasons=["ArcGIS connection or item creation failed before a private draft item was confirmed."],
            real_publish_attempted=True,
        )
        result["target_folder_status"] = folder_status
        result["message"] = "Real publish failed safely. No public or organization sharing was performed."
        write_publish_receipt(packet_path, result)
        return result

    result = _private_publish_result(
        packet_path=packet_path,
        item_properties=item_properties,
        dry_run=False,
        validation=validation,
        settings=settings,
        payload=payload,
        real_publish_attempted=True,
        item=item,
    )
    result["target_folder_status"] = folder_status
    result["message"] = "Private draft Web Map item created. No sharing was performed."
    write_publish_receipt(packet_path, result)
    return result
