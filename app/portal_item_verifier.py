"""Verify private ArcGIS Web Map draft items created by AutoMap."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.arcgis_publisher import (
    PUBLISH_TAGS,
    connect_to_arcgis,
    load_arcgis_publish_settings,
)


PROTECTED_ITEM_MARKERS = {
    ".env",
    "arcgis_password",
    "database_url",
    "password",
    "postgres_admin_url",
    "secret",
    "token",
    "cfs",
    "cfs_dev",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _get_attr(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def _item_access(item: Any) -> str:
    return str(_get_attr(item, "access", "private") or "private").lower()


def _shared_with(item: Any) -> dict[str, Any]:
    value = _get_attr(item, "shared_with", {}) or _get_attr(item, "sharedWith", {}) or {}
    return value if isinstance(value, dict) else {}


def _item_tags(item: Any) -> list[str]:
    tags = _get_attr(item, "tags", []) or []
    if isinstance(tags, str):
        return [tag.strip() for tag in tags.split(",") if tag.strip()]
    return [str(tag) for tag in tags]


def _item_data(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        data = item.get("data") or item.get("text") or {}
    else:
        get_data = getattr(item, "get_data", None)
        data = get_data() if callable(get_data) else (_get_attr(item, "data", {}) or {})
    if isinstance(data, str):
        try:
            loaded = json.loads(data)
            return loaded if isinstance(loaded, dict) else {}
        except json.JSONDecodeError:
            return {}
    return data if isinstance(data, dict) else {}


def _iter_strings(value: Any) -> list[str]:
    values: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            values.extend(_iter_strings(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_iter_strings(item))
    elif isinstance(value, str):
        values.append(value)
    return values


def _protected_marker(value: Any) -> str | None:
    for text_value in _iter_strings(value):
        lowered = text_value.lower()
        for marker in sorted(PROTECTED_ITEM_MARKERS):
            if marker in lowered:
                return marker
    return None


def _layer_urls(webmap_json: dict[str, Any]) -> list[str]:
    urls: list[str] = []
    for layer in webmap_json.get("operationalLayers") or []:
        if not isinstance(layer, dict):
            continue
        url = layer.get("url") or layer.get("layerUrl")
        if url:
            urls.append(str(url).rstrip("/"))
    return urls


def verify_item_is_private(item: Any) -> dict[str, Any]:
    """Verify the ArcGIS item access level is private."""
    access = _item_access(item)
    return {"passed": access == "private", "access": access}


def verify_item_not_shared_public(item: Any) -> dict[str, Any]:
    """Verify the ArcGIS item is not publicly shared."""
    access = _item_access(item)
    shared = _shared_with(item)
    public_shared = access == "public" or bool(shared.get("everyone") or shared.get("public"))
    return {"passed": not public_shared, "access": access, "shared_with": shared}


def verify_item_not_shared_org(item: Any) -> dict[str, Any]:
    """Verify the ArcGIS item is not shared to the organization."""
    access = _item_access(item)
    shared = _shared_with(item)
    org_shared = access == "org" or bool(shared.get("org") or shared.get("organization"))
    return {"passed": not org_shared, "access": access, "shared_with": shared}


def verify_item_type_webmap(item: Any) -> dict[str, Any]:
    """Verify the ArcGIS item type is Web Map."""
    item_type = str(_get_attr(item, "type", "") or "")
    return {"passed": item_type == "Web Map", "type": item_type}


def verify_item_title_prefix(item: Any) -> dict[str, Any]:
    """Verify the ArcGIS item title starts with AutoMap's draft prefix."""
    title = str(_get_attr(item, "title", "") or "")
    return {"passed": title.startswith("AutoMap Draft -"), "title": title}


def verify_item_tags(item: Any) -> dict[str, Any]:
    """Verify the ArcGIS item has AutoMap's expected tags."""
    tags = _item_tags(item)
    missing = [tag for tag in PUBLISH_TAGS if tag not in tags]
    return {"passed": not missing, "tags": tags, "missing_tags": missing}


def verify_item_data_layers(item: Any, approved_webmap: dict[str, Any]) -> dict[str, Any]:
    """Verify item Web Map operational layer URLs match approved_webmap.json."""
    item_data = _item_data(item)
    item_urls = _layer_urls(item_data)
    approved_urls = _layer_urls(approved_webmap)
    missing_urls = [url for url in approved_urls if url not in item_urls]
    unexpected_urls = [url for url in item_urls if url not in approved_urls]
    return {
        "passed": bool(item_urls) and not missing_urls and not unexpected_urls,
        "item_layer_urls": item_urls,
        "approved_layer_urls": approved_urls,
        "missing_urls": missing_urls,
        "unexpected_urls": unexpected_urls,
    }


def build_verification_receipt(item: Any, approved_packet_folder: str | Path) -> dict[str, Any]:
    """Build a non-secret verification receipt for a created portal item."""
    packet_path = Path(approved_packet_folder)
    approved_webmap = _load_json(packet_path / "approved_webmap.json")
    checks = {
        "item_exists": {"passed": item is not None},
        "private": verify_item_is_private(item),
        "not_public": verify_item_not_shared_public(item),
        "not_org_shared": verify_item_not_shared_org(item),
        "webmap_type": verify_item_type_webmap(item),
        "title_prefix": verify_item_title_prefix(item),
        "tags": verify_item_tags(item),
        "layer_urls": verify_item_data_layers(item, approved_webmap),
    }
    protected_marker = _protected_marker(
        {
            "title": _get_attr(item, "title", ""),
            "tags": _item_tags(item),
            "data": _item_data(item),
        }
    )
    if protected_marker:
        checks["protected_markers"] = {
            "passed": False,
            "marker": protected_marker,
        }
    else:
        checks["protected_markers"] = {"passed": True, "marker": None}

    errors = [
        name
        for name, result in checks.items()
        if isinstance(result, dict) and result.get("passed") is not True
    ]
    return {
        "verified_at": datetime.now(UTC).isoformat(),
        "item_id": _get_attr(item, "id"),
        "item_url": _get_attr(item, "url"),
        "item_title": _get_attr(item, "title"),
        "approved_packet_path": str(packet_path),
        "checks": checks,
        "verified_private": checks["private"]["passed"],
        "verified_not_public": checks["not_public"]["passed"],
        "verified_not_org_shared": checks["not_org_shared"]["passed"],
        "verified_webmap_type": checks["webmap_type"]["passed"],
        "verified_layer_urls": checks["layer_urls"]["passed"],
        "verification_errors": errors,
    }


def verify_portal_item(item_id: str, approved_packet_folder: str | Path | None = None) -> dict[str, Any]:
    """Fetch and verify a portal item by id."""
    settings = load_arcgis_publish_settings()
    gis = connect_to_arcgis(settings)
    content = getattr(gis, "content", None)
    get_item = getattr(content, "get", None)
    if not callable(get_item):
        return {
            "verified": False,
            "item_id": item_id,
            "verification_errors": ["ArcGIS content.get is unavailable."],
        }
    item = get_item(item_id)
    if item is None:
        return {
            "verified": False,
            "item_id": item_id,
            "verification_errors": ["Item was not found."],
        }
    if approved_packet_folder is None:
        checks = {
            "item_exists": {"passed": True},
            "private": verify_item_is_private(item),
            "not_public": verify_item_not_shared_public(item),
            "not_org_shared": verify_item_not_shared_org(item),
            "webmap_type": verify_item_type_webmap(item),
            "title_prefix": verify_item_title_prefix(item),
            "tags": verify_item_tags(item),
        }
        errors = [name for name, result in checks.items() if result.get("passed") is not True]
        return {
            "verified": not errors,
            "item_id": item_id,
            "checks": checks,
            "verification_errors": errors,
        }
    receipt = build_verification_receipt(item, approved_packet_folder)
    receipt["verified"] = not receipt["verification_errors"]
    return receipt
