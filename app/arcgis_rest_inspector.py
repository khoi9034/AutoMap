"""ArcGIS REST metadata inspector for AutoMap layer catalogs."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


DEFAULT_TIMEOUT_SECONDS = 30


class ArcGISRestError(RuntimeError):
    """Raised when an ArcGIS REST endpoint cannot provide valid JSON metadata."""


def _with_pjson(url: str) -> str:
    parsed = urlparse(url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
    if not any(key.lower() == "f" for key, _value in query_pairs):
        query_pairs.append(("f", "pjson"))
    return urlunparse(parsed._replace(query=urlencode(query_pairs)))


def fetch_json(url: str, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Fetch ArcGIS REST JSON with f=pjson, timeout, and clear errors."""
    request_url = _with_pjson(url)
    request = Request(request_url, headers={"User-Agent": "AutoMap REST Inspector"})

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise ArcGISRestError(f"HTTP {exc.code} for {request_url}") from exc
    except URLError as exc:
        raise ArcGISRestError(f"Unable to reach {request_url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise ArcGISRestError(f"Timed out fetching {request_url}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ArcGISRestError(f"Endpoint did not return valid JSON: {request_url}") from exc

    if not isinstance(data, dict):
        raise ArcGISRestError(f"Endpoint returned non-object JSON: {request_url}")

    if "error" in data:
        error = data["error"]
        message = error.get("message", "ArcGIS REST error") if isinstance(error, dict) else str(error)
        raise ArcGISRestError(f"{message}: {request_url}")

    return data


def _service_name_from_mapserver_url(mapserver_url: str) -> str:
    parts = [part for part in urlparse(mapserver_url).path.split("/") if part]
    if parts and parts[-1].lower() == "mapserver" and len(parts) >= 2:
        return parts[-2]
    return parts[-1] if parts else "unknown_service"


def _service_url_from_folder(folder_url: str, service: dict[str, Any]) -> str:
    service_name = service.get("name", "")
    service_type = service.get("type", "MapServer")
    short_name = service_name.split("/")[-1]
    return f"{folder_url.rstrip('/')}/{short_name}/{service_type}"


def _as_list_from_csv(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _layer_ids(items: Any) -> list[int]:
    ids: list[int] = []
    if not isinstance(items, list):
        return ids
    for item in items:
        if isinstance(item, dict) and item.get("id") is not None:
            ids.append(int(item["id"]))
        elif isinstance(item, int):
            ids.append(item)
    return ids


def inspect_folder(folder_url: str) -> list[dict[str, Any]]:
    """Return available MapServer services from an ArcGIS REST folder."""
    data = fetch_json(folder_url)
    services: list[dict[str, Any]] = []
    for service in data.get("services", []):
        if service.get("type") != "MapServer":
            continue
        services.append(
            {
                "name": service.get("name"),
                "type": service.get("type"),
                "url": _service_url_from_folder(folder_url, service),
            }
        )
    return services


def inspect_mapserver(mapserver_url: str) -> dict[str, Any]:
    """Extract service-level metadata and layer/table arrays from a MapServer."""
    data = fetch_json(mapserver_url)
    full_extent = data.get("fullExtent")
    spatial_reference = data.get("spatialReference")
    if spatial_reference is None and isinstance(full_extent, dict):
        spatial_reference = full_extent.get("spatialReference")

    return {
        "service_name": _service_name_from_mapserver_url(mapserver_url),
        "service_url": mapserver_url.rstrip("/"),
        "service_item_id": data.get("serviceItemId"),
        "spatial_reference": spatial_reference,
        "supported_query_formats": _as_list_from_csv(data.get("supportedQueryFormats")),
        "max_record_count": data.get("maxRecordCount"),
        "full_extent": full_extent,
        "layers": data.get("layers", []),
        "tables": data.get("tables", []),
    }


def inspect_layer(layer_url: str) -> dict[str, Any]:
    """Extract layer metadata without downloading feature geometry."""
    data = fetch_json(layer_url)
    parent_layer = data.get("parentLayer")
    parent_layer_id = None
    if isinstance(parent_layer, dict) and parent_layer.get("id") is not None:
        parent_layer_id = int(parent_layer["id"])
    elif data.get("parentLayerId") is not None:
        parent_layer_id = int(data["parentLayerId"])

    sublayer_ids = _layer_ids(data.get("subLayers")) or _layer_ids(data.get("subLayerIds"))
    advanced_query = data.get("advancedQueryCapabilities") or {}
    layer_type = data.get("type")
    geometry_type = data.get("geometryType")
    is_group_layer = layer_type == "Group Layer" or bool(sublayer_ids and not geometry_type)

    return {
        "layer_id": data.get("id"),
        "layer_name": data.get("name"),
        "layer_type": layer_type,
        "parent_layer_id": parent_layer_id,
        "sublayer_ids": sublayer_ids,
        "geometry_type": geometry_type,
        "fields": data.get("fields", []),
        "display_field": data.get("displayField"),
        "object_id_field": data.get("objectIdField"),
        "type_id_field": data.get("typeIdField"),
        "extent": data.get("extent"),
        "drawing_info": data.get("drawingInfo"),
        "capabilities": _as_list_from_csv(data.get("capabilities")),
        "max_record_count": data.get("maxRecordCount"),
        "supports_statistics": bool(
            data.get("supportsStatistics")
            or advanced_query.get("supportsStatistics")
        ),
        "supports_advanced_queries": bool(
            data.get("supportsAdvancedQueries")
            or advanced_query.get("supportsAdvancedQueries")
        ),
        "is_group_layer": is_group_layer,
        "is_feature_layer": bool(geometry_type and not is_group_layer),
        "description": data.get("description"),
    }


def verify_layer_exists(layer_url: str) -> dict[str, Any]:
    """Verify that a layer metadata endpoint returns valid ArcGIS JSON."""
    verified_at = datetime.now(UTC).isoformat()
    try:
        inspect_layer(layer_url)
    except ArcGISRestError as exc:
        return {
            "is_verified": False,
            "verification_status": "failed",
            "verification_error": str(exc),
            "verified_at": verified_at,
        }

    return {
        "is_verified": True,
        "verification_status": "verified",
        "verification_error": None,
        "verified_at": verified_at,
    }


def try_layer_count(layer_url: str) -> dict[str, Any]:
    """Safely attempt a returnCountOnly query without downloading features."""
    query_url = (
        f"{layer_url.rstrip('/')}/query?"
        "where=1%3D1&returnCountOnly=true&f=pjson"
    )
    try:
        data = fetch_json(query_url)
    except ArcGISRestError as exc:
        return {"record_count": None, "count_error": str(exc)}

    count = data.get("count")
    return {
        "record_count": int(count) if isinstance(count, int) else None,
        "count_error": None if isinstance(count, int) else "Count response did not include an integer count.",
    }

