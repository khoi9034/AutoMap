"""Safe ArcGIS draft publisher for adjusted AutoMap packets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


REQUIRED_ADJUSTED_PUBLISH_FILES = {
    "adjusted_recipe.json",
    "adjusted_webmap.json",
    "applied_adjustments.json",
    "adjusted_warnings.json",
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
    dry_run: bool


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


def load_arcgis_publish_settings(load_env_file: bool = True) -> ArcGISPublishSettings:
    """Load ArcGIS publishing settings without printing or exposing secrets."""
    if load_env_file:
        load_dotenv()
    return ArcGISPublishSettings(
        portal_url=os.getenv("ARCGIS_PORTAL_URL", "https://www.arcgis.com").rstrip("/"),
        username=os.getenv("ARCGIS_USERNAME"),
        password=os.getenv("ARCGIS_PASSWORD"),
        target_folder=os.getenv("ARCGIS_TARGET_FOLDER", "AutoMap Drafts"),
        dry_run=_parse_bool(os.getenv("AUTOMAP_PUBLISH_DRY_RUN"), default=True),
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
            "username_configured": bool(loaded_settings.username),
            "password_configured": bool(loaded_settings.password),
            "target_folder": loaded_settings.target_folder,
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
            "username_configured": True,
            "password_configured": True,
            "target_folder": loaded_settings.target_folder,
            "error": str(exc),
        }
    return {
        "connected": True,
        "portal_url": loaded_settings.portal_url,
        "username": username,
        "target_folder": loaded_settings.target_folder,
    }


def validate_publish_packet(adjusted_packet_folder: str | Path) -> dict[str, Any]:
    """Validate an adjusted packet before dry-run or real publishing."""
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

    missing_files = sorted(file_name for file_name in REQUIRED_ADJUSTED_PUBLISH_FILES if not (packet_path / file_name).exists())
    if missing_files:
        errors.append(f"Missing required adjusted publish files: {', '.join(missing_files)}")
    raw_review_files = {"recipe.json", "webmap.json"} & {path.name for path in packet_path.iterdir() if path.is_file()}
    if raw_review_files:
        errors.append("Only adjusted packets can be published; raw review packet files were found.")

    adjusted_recipe: dict[str, Any] = {}
    adjusted_webmap: dict[str, Any] = {}
    adjusted_warnings: dict[str, Any] = {}
    if not missing_files:
        try:
            adjusted_recipe = _load_json(packet_path / "adjusted_recipe.json")
            adjusted_webmap = _load_json(packet_path / "adjusted_webmap.json")
            _load_json(packet_path / "applied_adjustments.json")
            adjusted_warnings = _load_json(packet_path / "adjusted_warnings.json")
        except json.JSONDecodeError as exc:
            errors.append(f"Adjusted packet JSON is invalid: {exc}")

    if adjusted_webmap and not adjusted_webmap.get("operationalLayers"):
        errors.append("adjusted_webmap.json has no operationalLayers.")
    for index, layer in enumerate(adjusted_webmap.get("operationalLayers") or []):
        if not layer.get("title"):
            errors.append(f"Operational layer {index} is missing title.")
        if not layer.get("url"):
            errors.append(f"Operational layer {layer.get('title') or index} is missing URL.")

    if adjusted_warnings:
        if adjusted_warnings.get("publish_ready") is not True:
            errors.append("Adjusted packet publish_ready must be true before publishing.")
        active = adjusted_warnings.get("active") or {}
        unresolved = {
            group: values
            for group, values in active.items()
            if values
        }
        if unresolved:
            errors.append("Publishing blocked because unresolved warnings or blockers remain.")

    protected_marker = _contains_protected_reference(
        {
            "adjusted_recipe": adjusted_recipe,
            "adjusted_webmap": adjusted_webmap,
            "adjusted_warnings": adjusted_warnings,
        }
    )
    if protected_marker:
        errors.append(f"Adjusted packet contains protected reference: {protected_marker}")

    return {
        "is_valid": not errors,
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "packet_path": str(packet_path),
        "publish_ready": adjusted_warnings.get("publish_ready"),
        "operational_layer_count": len(adjusted_webmap.get("operationalLayers") or []),
    }


def build_item_properties(adjusted_recipe: dict[str, Any], adjusted_webmap: dict[str, Any]) -> dict[str, Any]:
    """Build private ArcGIS Web Map item properties from adjusted draft content."""
    raw_title = adjusted_recipe.get("map_title") or adjusted_webmap.get("title") or "Untitled AutoMap Draft"
    title = str(raw_title)
    if not title.startswith("AutoMap Draft -"):
        title = f"AutoMap Draft - {title}"
    description = adjusted_recipe.get("map_description") or adjusted_webmap.get("description") or "AutoMap adjusted draft Web Map."
    snippet = "Private AutoMap draft for human review; not public-facing."
    return {
        "title": title,
        "type": "Web Map",
        "typeKeywords": "Web Map, Map, Online Map, AutoMap, Draft",
        "tags": list(PUBLISH_TAGS),
        "snippet": snippet,
        "description": description,
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
    item: Any | None = None,
) -> dict[str, Any]:
    result = {
        "status": "dry_run" if dry_run else "published_private_draft",
        "dry_run": dry_run,
        "created_item": not dry_run,
        "published": not dry_run,
        "shared_public": False,
        "shared_organization": False,
        "overwrite_used": False,
        "delete_used": False,
        "packet_path": str(packet_path),
        "title": item_properties["title"],
        "item_type": item_properties["type"],
        "tags": PUBLISH_TAGS,
        "validation": validation,
        "published_at": datetime.now(UTC).isoformat(),
    }
    if item is not None:
        result["item_id"] = getattr(item, "id", None)
        result["item_url"] = getattr(item, "url", None)
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


def publish_webmap_draft(
    adjusted_packet_folder: str | Path,
    dry_run: bool = True,
    confirm_publish: bool = False,
) -> dict[str, Any]:
    """Publish an adjusted packet as a private draft, or dry-run by default."""
    packet_path = Path(adjusted_packet_folder)
    validation = validate_publish_packet(packet_path)
    adjusted_recipe = _load_json(packet_path / "adjusted_recipe.json") if (packet_path / "adjusted_recipe.json").exists() else {}
    adjusted_webmap = _load_json(packet_path / "adjusted_webmap.json") if (packet_path / "adjusted_webmap.json").exists() else {}
    item_properties = build_item_properties(adjusted_recipe, adjusted_webmap)

    if not validation["is_valid"]:
        result = {
            "status": "blocked",
            "dry_run": dry_run,
            "created_item": False,
            "published": False,
            "shared_public": False,
            "shared_organization": False,
            "overwrite_used": False,
            "delete_used": False,
            "packet_path": str(packet_path),
            "title": item_properties["title"],
            "item_type": item_properties["type"],
            "tags": PUBLISH_TAGS,
            "validation": validation,
            "blocked_at": datetime.now(UTC).isoformat(),
        }
        write_publish_receipt(packet_path, result)
        return result

    if dry_run:
        result = _private_publish_result(
            packet_path=packet_path,
            item_properties=item_properties,
            dry_run=True,
            validation=validation,
        )
        result["message"] = "Dry-run only. No ArcGIS connection was opened and no item was created."
        write_publish_receipt(packet_path, result)
        return result

    if not confirm_publish:
        raise ValueError("Real publishing requires --confirm-publish.")

    settings = load_arcgis_publish_settings()
    gis = connect_to_arcgis(settings)
    item = gis.content.add(
        item_properties=item_properties,
        data=None,
        folder=settings.target_folder,
    )
    result = _private_publish_result(
        packet_path=packet_path,
        item_properties=item_properties,
        dry_run=False,
        validation=validation,
        item=item,
    )
    result["message"] = "Private draft Web Map item created. No sharing was performed."
    write_publish_receipt(packet_path, result)
    return result
