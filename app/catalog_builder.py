"""Build layer catalog records from inspected ArcGIS REST metadata."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.arcgis_rest_inspector import (
    ArcGISRestError,
    inspect_folder,
    inspect_layer,
    inspect_mapserver,
    try_layer_count,
)
from app.layer_semantics import (
    build_layer_key,
    date_fields_from_fields,
    detect_historical_year,
    infer_layer_semantics,
)


def discover_services(sources: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Discover MapServer services from configured sources."""
    services: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for source in sorted(sources, key=lambda item: item["priority"]):
        try:
            if source["source_type"] == "arcgis_folder":
                for service in inspect_folder(source["base_url"]):
                    services.append({**service, "source": source})
            elif source["source_type"] == "arcgis_mapserver":
                service_meta = inspect_mapserver(source["base_url"])
                services.append(
                    {
                        "name": service_meta["service_name"],
                        "type": "MapServer",
                        "url": source["base_url"],
                        "source": source,
                    }
                )
        except ArcGISRestError as exc:
            failures.append({"source_key": source["source_key"], "url": source["base_url"], "error": str(exc)})
    return services, failures


def inspect_services(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Inspect configured REST services without writing to the database."""
    services, failures = discover_services(sources)
    inspected_services: list[dict[str, Any]] = []
    for service in services:
        source = service["source"]
        try:
            service_meta = inspect_mapserver(service["url"])
        except ArcGISRestError as exc:
            failures.append({"source_key": source["source_key"], "url": service["url"], "error": str(exc)})
            continue
        inspected_services.append(
            {
                "source_key": source["source_key"],
                "source_priority": source["priority"],
                "source_status": source["status"],
                "service_name": service_meta["service_name"],
                "service_url": service_meta["service_url"],
                "layer_count": len(service_meta["layers"]),
                "table_count": len(service_meta["tables"]),
            }
        )

    return {"services": inspected_services, "failures": failures}


def _layer_url(service_url: str, layer_id: int) -> str:
    return f"{service_url.rstrip('/')}/{layer_id}"


def _layer_record(
    source: dict[str, Any],
    service_meta: dict[str, Any],
    layer_ref: dict[str, Any],
    layer_meta: dict[str, Any],
    verification: dict[str, Any],
    count_result: dict[str, Any],
) -> dict[str, Any]:
    layer_id = int(layer_meta.get("layer_id") if layer_meta.get("layer_id") is not None else layer_ref["id"])
    layer_name = layer_meta.get("layer_name") or layer_ref.get("name") or f"Layer {layer_id}"
    service_name = service_meta["service_name"]
    historical_year = detect_historical_year(service_name, layer_name)
    source_status = source["status"]
    if historical_year is not None:
        source_status = "legacy_historical"
    semantics = infer_layer_semantics(service_name, layer_name)
    fields = layer_meta.get("fields", [])
    layer_url = _layer_url(service_meta["service_url"], layer_id)

    return {
        "layer_key": build_layer_key(source["source_key"], service_name, layer_id, layer_name),
        "layer_name": layer_name,
        "rest_url": layer_url,
        "category": semantics["category"],
        "aliases": semantics["aliases"],
        "description": layer_meta.get("description"),
        "geometry_type": layer_meta.get("geometry_type"),
        "date_fields": date_fields_from_fields(fields),
        "common_filters": [],
        "planning_use_cases": semantics["planning_use_cases"],
        "recommended_symbology": {},
        "known_limitations": count_result.get("count_error"),
        "is_public": True,
        "is_active": not bool(historical_year),
        "source_key": source["source_key"],
        "source_priority": source["priority"],
        "source_status": source_status,
        "service_name": service_name,
        "service_url": service_meta["service_url"],
        "layer_id": layer_id,
        "layer_url": layer_url,
        "layer_type": layer_meta.get("layer_type") or layer_ref.get("type"),
        "parent_layer_id": layer_meta.get("parent_layer_id"),
        "sublayer_ids": layer_meta.get("sublayer_ids", []),
        "is_group_layer": layer_meta.get("is_group_layer", False),
        "is_feature_layer": layer_meta.get("is_feature_layer", False),
        "spatial_reference": service_meta.get("spatial_reference"),
        "extent": layer_meta.get("extent") or service_meta.get("full_extent"),
        "supported_query_formats": service_meta.get("supported_query_formats", []),
        "capabilities": layer_meta.get("capabilities", []),
        "max_record_count": layer_meta.get("max_record_count") or service_meta.get("max_record_count"),
        "object_id_field": layer_meta.get("object_id_field"),
        "display_field": layer_meta.get("display_field"),
        "type_id_field": layer_meta.get("type_id_field"),
        "fields": fields,
        "drawing_info": layer_meta.get("drawing_info"),
        "service_item_id": service_meta.get("service_item_id"),
        "record_count": count_result.get("record_count"),
        "is_verified": verification["is_verified"],
        "verification_status": verification["verification_status"],
        "verification_error": verification["verification_error"],
        "verified_at": verification["verified_at"],
        "is_historical": bool(historical_year),
        "historical_year": historical_year,
        "canonical_topic": semantics["canonical_topic"],
        "superseded_by_layer_key": None,
        "source_notes": None,
    }


def build_catalog_records(sources: list[dict[str, Any]]) -> dict[str, Any]:
    """Crawl configured REST sources and build catalog records."""
    services, failures = discover_services(sources)
    records: list[dict[str, Any]] = []
    service_count_by_source: dict[str, int] = {}
    layer_count_by_source: dict[str, int] = {}

    for service in services:
        source = service["source"]
        source_key = source["source_key"]
        try:
            service_meta = inspect_mapserver(service["url"])
        except ArcGISRestError as exc:
            failures.append({"source_key": source_key, "url": service["url"], "error": str(exc)})
            continue

        service_count_by_source[source_key] = service_count_by_source.get(source_key, 0) + 1
        layer_count_by_source[source_key] = layer_count_by_source.get(source_key, 0) + len(service_meta["layers"])

        for layer_ref in service_meta["layers"]:
            if layer_ref.get("id") is None:
                continue
            layer_id = int(layer_ref["id"])
            layer_url = _layer_url(service_meta["service_url"], layer_id)
            verified_at = datetime.now(UTC).isoformat()
            try:
                layer_meta = inspect_layer(layer_url)
                verification = {
                    "is_verified": True,
                    "verification_status": "verified",
                    "verification_error": None,
                    "verified_at": verified_at,
                }
            except ArcGISRestError as exc:
                verification = {
                    "is_verified": False,
                    "verification_status": "failed",
                    "verification_error": str(exc),
                    "verified_at": verified_at,
                }
                failures.append({"source_key": source_key, "url": layer_url, "error": str(exc)})
                layer_meta = {
                    "layer_id": layer_id,
                    "layer_name": layer_ref.get("name"),
                    "layer_type": layer_ref.get("type"),
                    "is_group_layer": bool(layer_ref.get("subLayerIds")),
                    "is_feature_layer": False,
                }
            count_result = try_layer_count(layer_url)
            records.append(_layer_record(source, service_meta, layer_ref, layer_meta, verification, count_result))

    return {
        "records": records,
        "failures": failures,
        "service_count_by_source": service_count_by_source,
        "layer_count_by_source": layer_count_by_source,
        "verified_count": sum(1 for record in records if record["is_verified"]),
    }
