"""Bounded spatial query optimizer for AutoMap v2.1."""

from __future__ import annotations

from copy import deepcopy
import json
from typing import Any

from app.analysis_chunker import build_chunk_receipts, chunk_constraint_features, enforce_chunk_limits, merge_chunk_results
from app.analysis_models import AnalysisLayerRef
from app.analysis_safety import (
    build_safety_summary,
    enforce_max_count,
    enforce_max_features_per_chunk,
    enforce_max_total_downloads,
    load_analysis_safety_limits,
    narrowing_suggestions,
)
from app.geometry_utils import GeometrySafetyError, filter_features_by_polygon, geojson_envelope
from app.spatial_query_client import SpatialQueryClient, SpatialQueryError


SPATIAL_REL_INTERSECTS = "esriSpatialRelIntersects"
CONSTRAINT_GEOMETRY_OFFSET = 0.00002
CONSTRAINT_GEOMETRY_PRECISION = 6


def _layer_ref(layer: dict[str, Any] | AnalysisLayerRef | None) -> AnalysisLayerRef:
    if isinstance(layer, AnalysisLayerRef):
        return layer
    return AnalysisLayerRef.from_layer(layer or {})


def _requested_geography(recipe: dict[str, Any]) -> str | None:
    geographies = recipe.get("parsed_request", {}).get("geography_terms") or []
    for geography in geographies:
        if isinstance(geography, dict):
            name = geography.get("name")
            geo_type = geography.get("type")
            if name and geo_type not in {"county", "countywide"}:
                return str(name)
        elif geography:
            return str(geography)
    return None


def _geography_where_clause(recipe: dict[str, Any], geography_layer: AnalysisLayerRef) -> str:
    geography_name = (_requested_geography(recipe) or "").strip()
    if not geography_name:
        return "1=1"
    district_values = {
        "concord": "CITY OF CONCORD",
        "kannapolis": "CITY OF KANNAPOLIS",
        "harrisburg": "TOWN OF HARRISBURG",
        "midland": "TOWN OF MIDLAND",
        "mount pleasant": "TOWN OF MOUNT PLEASANT",
        "mt pleasant": "TOWN OF MOUNT PLEASANT",
        "locust": "CITY OF LOCUST",
    }
    normalized = geography_name.lower()
    if geography_layer.layer_name.lower() == "municipaldistrict" and normalized in district_values:
        return f"DISTRICT = '{district_values[normalized]}'"
    return "1=1"


def _feature_matches_geography(feature: dict[str, Any], geography_name: str | None) -> bool:
    if not geography_name:
        return True
    text = json.dumps(feature.get("properties") or {}, default=str).lower()
    normalized = geography_name.lower().replace("mt pleasant", "mount pleasant")
    return normalized in text


def deduplicate_feature_ids(object_ids: list[Any]) -> list[Any]:
    """Deduplicate feature/ObjectIDs while preserving first-seen order."""
    seen: set[str] = set()
    deduped: list[Any] = []
    for object_id in object_ids:
        marker = str(object_id)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(object_id)
    return deduped


def _multipart_polygon_geometry(features: list[dict[str, Any]]) -> dict[str, Any] | None:
    polygons: list[Any] = []
    for feature in features:
        geometry = feature.get("geometry") or {}
        geometry_type = geometry.get("type")
        if geometry_type == "Polygon":
            polygons.append(geometry.get("coordinates") or [])
        elif geometry_type == "MultiPolygon":
            polygons.extend(geometry.get("coordinates") or [])
    if not polygons:
        return None
    return {"type": "MultiPolygon", "coordinates": polygons}


def build_geometry_first_strategy() -> dict[str, Any]:
    """Return the preferred v2.1 strategy metadata."""
    return {
        "strategy": "geometry_first",
        "label": "Geometry-first ObjectID strategy",
        "uses_server_side_spatial_filtering": True,
        "downloads_target_geometry_after_object_id_count": True,
        "steps": [
            "Filter the geography layer to the requested municipality.",
            "Query constraint features that intersect the geography.",
            "Query target layer ObjectIDs against each constraint geometry.",
            "Deduplicate target ObjectIDs before any geometry download.",
            "Download target geometries by ObjectID only if the final count is safe.",
        ],
    }


def build_extent_first_strategy() -> dict[str, Any]:
    """Return a fallback extent strategy metadata block."""
    return {
        "strategy": "extent_first",
        "label": "Extent-first fallback strategy",
        "uses_server_side_spatial_filtering": True,
        "downloads_target_geometry_after_object_id_count": True,
        "steps": [
            "Use a narrowed analysis extent when exact geometry queries are unavailable.",
            "Block if the extent-based candidate count remains above safety limits.",
        ],
    }


def build_chunked_strategy(chunk_count: int) -> dict[str, Any]:
    """Return chunked strategy metadata."""
    strategy = build_geometry_first_strategy()
    strategy.update(
        {
            "strategy": "chunked_geometry_first",
            "label": "Chunked geometry-first ObjectID strategy",
            "chunks_planned": chunk_count,
        }
    )
    return strategy


def choose_query_strategy(
    *,
    constraint_feature_count: int,
    chunk_count: int,
    limits: dict[str, int],
) -> dict[str, Any]:
    """Choose the safest strategy available for an intersection request."""
    if chunk_count > 1:
        return build_chunked_strategy(chunk_count)
    if constraint_feature_count <= limits["max_constraint_features"]:
        return build_geometry_first_strategy()
    return build_extent_first_strategy()


def explain_query_strategy(strategy: dict[str, Any]) -> str:
    """Create a concise user-facing explanation for the selected strategy."""
    name = strategy.get("label") or strategy.get("strategy") or "bounded strategy"
    if strategy.get("strategy") == "chunked_geometry_first":
        return (
            f"{name}: AutoMap narrowed this request using server-side spatial filtering against "
            f"{strategy.get('chunks_planned', 0)} constraint chunks before downloading geometry."
        )
    return f"{name}: AutoMap narrowed this request using server-side spatial filtering before downloading geometry."


def _query_geography_features(
    client: SpatialQueryClient,
    recipe: dict[str, Any],
    geography_layer: AnalysisLayerRef,
    limits: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    where_clause = _geography_where_clause(recipe, geography_layer)
    result = client.query_features(
        geography_layer.layer_url or "",
        where=where_clause,
        return_geometry=True,
        result_record_count=limits["max_download_features_per_layer"],
    )
    features = result.get("features") or []
    if where_clause == "1=1":
        geography_name = _requested_geography(recipe)
        features = [feature for feature in features if _feature_matches_geography(feature, geography_name)]
    if not features and where_clause != "1=1":
        fallback = client.query_features(
            geography_layer.layer_url or "",
            where="1=1",
            return_geometry=True,
            result_record_count=limits["max_download_features_per_layer"],
        )
        geography_name = _requested_geography(recipe)
        features = [feature for feature in fallback.get("features") or [] if _feature_matches_geography(feature, geography_name)]
        result = fallback
        where_clause = "1=1"
    return features, result, where_clause


def _query_constraint_features(
    client: SpatialQueryClient,
    geography_features: list[dict[str, Any]],
    constraint_layer: AnalysisLayerRef,
    limits: dict[str, int],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not geography_features:
        return [], {"status": "blocked", "count": 0, "features": []}
    geography_envelope = geojson_envelope(geography_features)
    constraint_result = client.query_features(
        constraint_layer.layer_url or "",
        geometry=geography_envelope,
        spatial_rel=SPATIAL_REL_INTERSECTS,
        out_fields=constraint_layer.object_id_field or "OBJECTID",
        return_geometry=True,
        result_record_count=min(limits["max_constraint_features"], limits["hard_max_download_features"]),
        # ponytail: simplify public floodplain geometry enough to avoid REST timeouts; use unsimplified geometry if this becomes official analysis.
        max_allowable_offset=CONSTRAINT_GEOMETRY_OFFSET,
        geometry_precision=CONSTRAINT_GEOMETRY_PRECISION,
    )
    features = filter_features_by_polygon(constraint_result.get("features") or [], geography_features)
    return features, constraint_result


def estimate_candidate_counts(
    *,
    client: SpatialQueryClient,
    target_layer: AnalysisLayerRef,
    constraint_chunks: list[list[dict[str, Any]]],
    limits: dict[str, int],
) -> dict[str, Any]:
    """Estimate target candidates using ObjectID-only spatial queries."""
    chunk_results: list[dict[str, Any]] = []
    chunk_receipts = build_chunk_receipts(constraint_chunks)
    safety_checks: list[dict[str, Any]] = []
    for chunk_index, chunk in enumerate(constraint_chunks):
        raw_ids: list[Any] = []
        methods: list[str] = []
        geometry = _multipart_polygon_geometry(chunk)
        query_features = [chunk[0]] if geometry else chunk
        for feature in query_features:
            query_geometry = geometry or feature.get("geometry")
            result = client.query_object_ids(
                target_layer.layer_url or "",
                geometry=query_geometry,
                spatial_rel=SPATIAL_REL_INTERSECTS,
            )
            raw_ids.extend(result.get("object_ids") or [])
            if result.get("request_method"):
                methods.append(str(result["request_method"]))
        deduped_chunk_ids = deduplicate_feature_ids(raw_ids)
        check = enforce_max_features_per_chunk(
            len(deduped_chunk_ids),
            limits["max_features_per_chunk"],
            label=f"candidate ObjectIDs in chunk {chunk_index + 1}",
        )
        safety_checks.append(check)
        chunk_receipts[chunk_index].update(
            {
                "candidate_object_id_count": len(raw_ids),
                "deduplicated_candidate_count": len(deduped_chunk_ids),
                "request_methods": sorted(set(methods)),
                "geometry_mode": "multipart_constraint_chunk" if geometry else "per_feature_constraint_geometry",
                "status": "ok" if check["passed"] else "blocked",
            }
        )
        chunk_results.append({"chunk_index": chunk_index + 1, "object_ids": deduped_chunk_ids})
    merged = merge_chunk_results(chunk_results)
    total_check = enforce_max_total_downloads(
        merged["object_id_count"],
        limits["max_download_features_per_layer"],
    )
    safety_checks.append(total_check)
    return {
        "candidate_object_ids": merged["object_ids"],
        "optimized_candidate_count": merged["object_id_count"],
        "raw_candidate_object_id_count": merged["raw_object_id_count"],
        "chunk_results": chunk_results,
        "chunk_receipts": chunk_receipts,
        "safety_checks": safety_checks,
    }


def optimize_intersection_query_plan(
    recipe: dict[str, Any],
    target_layer: dict[str, Any] | AnalysisLayerRef,
    geography_layer: dict[str, Any] | AnalysisLayerRef,
    constraint_layer: dict[str, Any] | AnalysisLayerRef,
    *,
    query_client: SpatialQueryClient | None = None,
    max_features: int | None = None,
    include_object_ids: bool = False,
) -> dict[str, Any]:
    """Build a v2.1 server-side filtered ObjectID plan for intersection analysis."""
    client = query_client or SpatialQueryClient(max_features=max_features or 2000)
    target_ref = _layer_ref(target_layer)
    geography_ref = _layer_ref(geography_layer)
    constraint_ref = _layer_ref(constraint_layer)
    limits = load_analysis_safety_limits(max_features=max_features)
    blocked_reasons: list[str] = []
    safety_checks: list[dict[str, Any]] = []
    counts: dict[str, Any] = {}

    try:
        try:
            counts["target_broad"] = client.query_count(target_ref.layer_url or "")
        except SpatialQueryError as exc:
            counts["target_broad"] = {
                "count": None,
                "return_geometry": False,
                "diagnostic_only": True,
                "warning": str(exc),
            }
        geography_features, geography_result, geography_where = _query_geography_features(client, recipe, geography_ref, limits)
        counts["geography"] = {
            "queried_count": geography_result.get("count"),
            "matched_count": len(geography_features),
            "where": geography_where,
            "query_metadata": geography_result.get("query_metadata"),
        }
        if not geography_features:
            blocked_reasons.append("No geography boundary matched the requested geography.")

        constraint_features, constraint_result = _query_constraint_features(client, geography_features, constraint_ref, limits)
        counts["constraint"] = {
            "queried_count": constraint_result.get("count"),
            "matched_count": len(constraint_features),
            "bounded_by_geography": True,
            "query_metadata": constraint_result.get("query_metadata"),
        }
        safety_checks.append(enforce_max_count(len(constraint_features), limits["max_constraint_features"], "constraint feature"))
        if not constraint_features:
            blocked_reasons.append("No constraint features intersected the requested geography.")

        constraint_chunks = chunk_constraint_features(constraint_features, max_features_per_chunk=25)
        safety_checks.extend(
            enforce_chunk_limits(
                constraint_chunks,
                max_chunks=limits["max_chunks"],
                max_features_per_chunk=25,
            )
        )
        strategy = choose_query_strategy(
            constraint_feature_count=len(constraint_features),
            chunk_count=len(constraint_chunks),
            limits=limits,
        )

        candidate_summary = {
            "candidate_object_ids": [],
            "optimized_candidate_count": 0,
            "raw_candidate_object_id_count": 0,
            "chunk_results": [],
            "chunk_receipts": build_chunk_receipts(constraint_chunks),
            "safety_checks": [],
        }
        if constraint_chunks and not blocked_reasons and len(constraint_chunks) <= limits["max_chunks"]:
            candidate_summary = estimate_candidate_counts(
                client=client,
                target_layer=target_ref,
                constraint_chunks=constraint_chunks,
                limits=limits,
            )
            safety_checks.extend(candidate_summary["safety_checks"])
            if candidate_summary["optimized_candidate_count"] > limits["max_download_features_per_layer"]:
                blocked_reasons.append(
                    "Optimized candidate parcel count "
                    f"{candidate_summary['optimized_candidate_count']} exceeds max feature limit "
                    f"{limits['max_download_features_per_layer']}."
                )
    except (SpatialQueryError, GeometrySafetyError, ValueError) as exc:
        strategy = build_extent_first_strategy()
        constraint_features = []
        geography_features = []
        constraint_chunks = []
        candidate_summary = {
            "candidate_object_ids": [],
            "optimized_candidate_count": 0,
            "raw_candidate_object_id_count": 0,
            "chunk_results": [],
            "chunk_receipts": [],
            "safety_checks": [],
        }
        blocked_reasons.append(str(exc))

    safety_summary = build_safety_summary(
        limits=limits,
        safety_checks=safety_checks,
        blocked_reasons=blocked_reasons,
        narrowing=narrowing_suggestions() if blocked_reasons else [],
    )
    executable = not safety_summary["blocked"]
    response = {
        "optimizer_version": "2.1",
        "strategy": strategy["strategy"],
        "strategy_label": strategy.get("label"),
        "strategy_explanation": explain_query_strategy(strategy),
        "strategy_steps": strategy.get("steps") or [],
        "uses_server_side_spatial_filtering": strategy.get("uses_server_side_spatial_filtering", True),
        "broad_count": (counts.get("target_broad") or {}).get("count"),
        "optimized_candidate_count": candidate_summary["optimized_candidate_count"],
        "raw_candidate_object_id_count": candidate_summary["raw_candidate_object_id_count"],
        "constraint_feature_count": len(constraint_features),
        "chunks_planned": len(constraint_chunks),
        "chunk_receipts": candidate_summary["chunk_receipts"],
        "safety": safety_summary,
        "safety_limits": limits,
        "blocked_reasons": blocked_reasons,
        "narrowing_suggestions": safety_summary["narrowing_suggestions"],
        "executable": executable,
        "counts": counts,
        "target_layer": target_ref.to_dict(),
        "geography_layer": geography_ref.to_dict(),
        "constraint_layer": constraint_ref.to_dict(),
        "geography_features": deepcopy(geography_features),
        "constraint_features": deepcopy(constraint_features),
    }
    if include_object_ids:
        response["candidate_object_ids"] = candidate_summary["candidate_object_ids"]
    return response
