"""Metadata-only ArcGIS service discovery for external AutoMap source review."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse

from app.arcgis_rest_inspector import ArcGISRestError, fetch_json, inspect_layer, try_layer_count, verify_layer_exists
from app.layer_semantics import slugify


SERVICE_TYPES = {"MapServer", "FeatureServer"}
MAX_DISCOVERY_DEPTH = 2
MAX_LAYERS_PER_SERVICE = 35
SAMPLE_RECORD_COUNT = 3

GAP_KEYWORDS = {
    "current_permits": {
        "permit",
        "permits",
        "building permit",
        "building permits",
        "inspection",
        "issued permit",
    },
    "current_planning_cases": {
        "planning",
        "planning case",
        "planning cases",
        "rezoning",
        "zoning case",
        "zoning cases",
        "case",
        "cases",
    },
    "current_development_pipeline": {
        "plan review",
        "plan reviews",
        "accela",
        "development",
        "subdivision",
        "current project",
        "current projects",
        "pipeline",
    },
    "traffic_counts": {"aadt", "traffic count", "traffic counts", "traffic", "volume"},
    "stip_projects": {"stip", "transportation improvement", "planned project", "road project", "project"},
}


def _normalize_keywords(keywords: str | list[str] | tuple[str, ...] | None) -> list[str]:
    if keywords is None:
        return []
    if isinstance(keywords, str):
        return [keywords.lower().strip()] if keywords.strip() else []
    return [str(keyword).lower().strip() for keyword in keywords if str(keyword).strip()]


def _service_name_from_url(service_url: str) -> str:
    parts = [part for part in urlparse(service_url).path.split("/") if part]
    if parts and parts[-1] in SERVICE_TYPES and len(parts) >= 2:
        return parts[-2]
    return parts[-1] if parts else "unknown_service"


def _service_url(folder_url: str, service: dict[str, Any]) -> str | None:
    name = str(service.get("name") or "").strip()
    service_type = str(service.get("type") or "").strip()
    if not name or service_type not in SERVICE_TYPES:
        return None
    if "/" in name and not folder_url.rstrip("/").lower().endswith(name.split("/")[0].lower()):
        path = name
    else:
        path = name.split("/")[-1]
    return f"{folder_url.rstrip('/')}/{path}/{service_type}"


def _metadata_blob(*items: Any) -> str:
    parts: list[str] = []
    for item in items:
        if item is None:
            continue
        if isinstance(item, dict):
            parts.extend(str(value) for value in item.values())
        elif isinstance(item, list):
            for value in item:
                if isinstance(value, dict):
                    parts.extend(str(inner) for inner in value.values())
                else:
                    parts.append(str(value))
        else:
            parts.append(str(item))
    return " ".join(parts).lower()


def discover_arcgis_services(root_url: str, *, max_depth: int = MAX_DISCOVERY_DEPTH) -> list[dict[str, Any]]:
    """Discover ArcGIS MapServer/FeatureServer services from a REST root/folder."""
    seen_services: set[str] = set()
    seen_folders: set[str] = set()
    discovered: list[dict[str, Any]] = []

    def walk(folder_url: str, depth: int) -> None:
        clean_folder = folder_url.rstrip("/")
        if clean_folder in seen_folders or depth > max_depth:
            return
        seen_folders.add(clean_folder)
        try:
            data = fetch_json(clean_folder)
        except ArcGISRestError as exc:
            discovered.append(
                {
                    "root_url": root_url,
                    "folder_url": clean_folder,
                    "service_name": None,
                    "service_type": None,
                    "service_url": None,
                    "discovery_status": "failed",
                    "error": str(exc),
                }
            )
            return

        for service in data.get("services") or []:
            if not isinstance(service, dict):
                continue
            url = _service_url(clean_folder, service)
            if not url or url in seen_services:
                continue
            seen_services.add(url)
            discovered.append(
                {
                    "root_url": root_url,
                    "folder_url": clean_folder,
                    "service_name": service.get("name"),
                    "service_type": service.get("type"),
                    "service_url": url,
                    "discovery_status": "discovered",
                }
            )

        for folder in data.get("folders") or []:
            folder_name = str(folder or "").strip()
            if not folder_name or folder_name.lower() in {"system", "utilities"}:
                continue
            walk(f"{clean_folder}/{folder_name}", depth + 1)

    walk(root_url, 0)
    return discovered


def search_services_by_keyword(root_url: str, keywords: str | list[str] | tuple[str, ...]) -> list[dict[str, Any]]:
    """Find discovered services whose names or URLs match review keywords."""
    normalized = _normalize_keywords(keywords)
    services = discover_arcgis_services(root_url)
    if not normalized:
        return services
    matches: list[dict[str, Any]] = []
    for service in services:
        blob = _metadata_blob(service.get("service_name"), service.get("service_url"))
        matched_keywords = [keyword for keyword in normalized if keyword in blob]
        if matched_keywords:
            matches.append({**service, "matched_keywords": matched_keywords})
    return matches


def _sample_layer_attributes(layer_url: str, layer_metadata: dict[str, Any]) -> dict[str, Any]:
    fields = layer_metadata.get("fields") or []
    field_names = [str(field.get("name")) for field in fields if isinstance(field, dict) and field.get("name")]
    object_id = layer_metadata.get("object_id_field")
    selected_fields = [object_id] if object_id else []
    selected_fields.extend(name for name in field_names if name not in selected_fields)
    out_fields = ",".join(selected_fields[:8]) if selected_fields else "*"
    query = urlencode(
        {
            "where": "1=1",
            "outFields": out_fields,
            "returnGeometry": "false",
            "resultRecordCount": str(SAMPLE_RECORD_COUNT),
            "f": "pjson",
        }
    )
    try:
        data = fetch_json(f"{layer_url.rstrip('/')}/query?{query}")
    except ArcGISRestError as exc:
        return {
            "sample_status": "failed",
            "sample_error": str(exc),
            "return_geometry": False,
            "sample_records": [],
        }
    records: list[dict[str, Any]] = []
    for feature in data.get("features") or []:
        if isinstance(feature, dict):
            attributes = feature.get("attributes") or feature.get("properties") or {}
            if isinstance(attributes, dict):
                records.append(attributes)
    return {
        "sample_status": "sampled",
        "return_geometry": False,
        "sample_record_count": len(records),
        "sample_records": records[:SAMPLE_RECORD_COUNT],
    }


def inspect_candidate_layer(layer_url: str) -> dict[str, Any]:
    """Inspect one candidate layer with metadata, count, and tiny attribute-only sample."""
    try:
        layer_metadata = inspect_layer(layer_url)
        verification = verify_layer_exists(layer_url)
        count = try_layer_count(layer_url)
        sample = _sample_layer_attributes(layer_url, layer_metadata)
    except ArcGISRestError as exc:
        return {
            "inspection_status": "failed",
            "is_verified": False,
            "verification_status": "failed",
            "verification_error": str(exc),
            "layer_url": layer_url.rstrip("/"),
            "downloaded_geometry": False,
        }

    layer_metadata = {
        **layer_metadata,
        "record_count": count.get("record_count"),
        "is_verified": bool(verification.get("is_verified")),
        "verification_status": verification.get("verification_status"),
        "verification_error": verification.get("verification_error"),
    }
    return {
        "inspection_status": "inspected",
        "is_verified": bool(verification.get("is_verified")),
        "verification_status": verification.get("verification_status"),
        "verification_error": verification.get("verification_error"),
        "record_count": count.get("record_count"),
        "count_error": count.get("count_error"),
        "layer_url": layer_url.rstrip("/"),
        "layer_id": layer_metadata.get("layer_id"),
        "layer_metadata": layer_metadata,
        "sample": sample,
        "sample_records": sample.get("sample_records") or [],
        "sample_status": sample.get("sample_status"),
        "downloaded_geometry": False,
        "inspected_at": datetime.now(UTC).isoformat(),
    }


def inspect_candidate_service(service_url: str, layer_keywords: list[str] | None = None) -> dict[str, Any]:
    """Inspect a MapServer/FeatureServer and its layer endpoints without feature geometry."""
    clean_url = service_url.rstrip("/")
    try:
        data = fetch_json(clean_url)
    except ArcGISRestError as exc:
        return {
            "inspection_status": "failed",
            "is_verified": False,
            "verification_status": "failed",
            "verification_error": str(exc),
            "service_url": clean_url,
            "downloaded_geometry": False,
        }

    layers: list[dict[str, Any]] = []
    layer_refs = list(data.get("layers") or []) + list(data.get("tables") or [])
    selected_refs = layer_refs
    normalized_keywords = _normalize_keywords(layer_keywords)
    if normalized_keywords:
        matching_refs = [
            layer_ref
            for layer_ref in layer_refs
            if isinstance(layer_ref, dict)
            and any(keyword in _metadata_blob(layer_ref.get("name"), clean_url) for keyword in normalized_keywords)
        ]
        selected_refs = matching_refs or layer_refs[:10]
    for layer_ref in selected_refs[:MAX_LAYERS_PER_SERVICE]:
        if not isinstance(layer_ref, dict) or layer_ref.get("id") is None:
            continue
        layer_id = int(layer_ref["id"])
        layer_url = f"{clean_url}/{layer_id}"
        inspected = inspect_candidate_layer(layer_url)
        layers.append(
            {
                **inspected,
                "layer_id": layer_id,
                "layer_name": (inspected.get("layer_metadata") or {}).get("layer_name") or layer_ref.get("name"),
                "layer_url": layer_url,
            }
        )

    return {
        "inspection_status": "inspected",
        "is_verified": any(layer.get("is_verified") for layer in layers),
        "verification_status": "verified" if any(layer.get("is_verified") for layer in layers) else "no_verified_layers",
        "service_name": _service_name_from_url(clean_url),
        "service_url": clean_url,
        "service_item_id": data.get("serviceItemId"),
        "spatial_reference": data.get("spatialReference") or (data.get("fullExtent") or {}).get("spatialReference"),
        "supported_query_formats": data.get("supportedQueryFormats"),
        "max_record_count": data.get("maxRecordCount"),
        "full_extent": data.get("fullExtent"),
        "layers": layers,
        "layer_count": len(layers),
        "downloaded_geometry": False,
        "inspected_at": datetime.now(UTC).isoformat(),
    }


def score_discovered_layer_for_gap(layer_metadata: dict[str, Any], gap_key: str) -> dict[str, Any]:
    """Score one inspected layer for a known AutoMap data gap."""
    gap = str(gap_key or "").lower()
    keywords = GAP_KEYWORDS.get(gap, {gap.replace("_", " ")})
    layer = layer_metadata.get("layer_metadata") or layer_metadata
    fields = layer.get("fields") or []
    blob = _metadata_blob(
        layer.get("layer_name"),
        layer.get("description"),
        layer_metadata.get("layer_url"),
        layer_metadata.get("service_name"),
        fields,
        layer_metadata.get("sample_records"),
    )
    score = 0
    matched: list[str] = []
    for keyword in keywords:
        if keyword in blob:
            matched.append(keyword)
            score += 25 if " " in keyword else 18
    if layer_metadata.get("is_verified") or layer.get("is_verified"):
        score += 20
    if layer.get("geometry_type"):
        score += 5
    if gap == "current_development_pipeline" and any(term in blob for term in ["plan review", "accela", "subdivision"]):
        score += 20
    if gap == "current_permits" and any(term in blob for term in ["plan review", "proxy"]):
        score -= 20
    if gap == "stip_projects" and "stip" in blob:
        score += 35
    if gap == "traffic_counts" and "aadt" in blob:
        score += 35
    return {
        "gap_key": gap,
        "score": max(0, score),
        "matched_terms": sorted(set(matched)),
        "layer_name": layer.get("layer_name"),
        "layer_url": layer_metadata.get("layer_url"),
    }


def write_discovery_report(results: dict[str, Any] | list[dict[str, Any]], output_dir: str | Path = "outputs/source_discovery") -> Path:
    """Write an ignored local discovery report for reviewer inspection."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    report_path = output_path / f"{timestamp}_source_discovery_report.json"
    payload = results if isinstance(results, dict) else {"results": results}
    report_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return report_path


def discovered_layer_source_key(layer_url: str, layer_name: str | None, gap_key: str) -> str:
    """Create a stable review source key from a discovered layer."""
    parsed = urlparse(layer_url)
    host_slug = slugify(parsed.netloc.replace(".", "_"))
    path_parts = [part for part in parsed.path.split("/") if part]
    service = path_parts[-3] if len(path_parts) >= 3 and path_parts[-2] in SERVICE_TYPES else path_parts[-2] if len(path_parts) >= 2 else "source"
    layer_id = path_parts[-1] if path_parts else "0"
    return f"discovered_{host_slug}_{slugify(service)}_{layer_id}_{slugify(layer_name or gap_key)}"[:120]
