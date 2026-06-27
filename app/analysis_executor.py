"""Safe bounded spatial analysis execution for AutoMap v2.2."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.analysis_models import (
    DEFAULT_MAX_FEATURES,
    HARD_MAX_FEATURES,
    AnalysisExecutionResult,
    AnalysisLayerRef,
    AnalysisOperationType,
    AnalysisPlanResult,
)
from app.analysis_result_store import (
    init_analysis_tables,
    list_analysis_runs,
    record_analysis_run,
    validate_analysis_run,
    write_analysis_outputs,
)
from app.geometry_utils import (
    GeometrySafetyError,
    compute_basic_stats,
    feature_collection_to_geojson,
    filter_features_by_polygon,
    geojson_envelope,
    intersect_features,
    make_safe_geojson_output,
)
from app.layer_catalog_store import load_catalog_records
from app.recipe_engine import build_recipe
from app.spatial_query_client import SpatialQueryClient, SpatialQueryError
from app.spatial_query_optimizer import optimize_intersection_query_plan
from app.ui_models import repo_root


SPATIAL_REL_INTERSECTS = "esriSpatialRelIntersects"
ENVELOPE_GEOMETRY_TYPE = "esriGeometryEnvelope"


def _layer_text(layer: dict[str, Any]) -> str:
    parts = [
        layer.get("layer_key"),
        layer.get("layer_name"),
        layer.get("category"),
        layer.get("role"),
        layer.get("service_name"),
        layer.get("source_status"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _catalog_lookup(catalog_records: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    records = catalog_records if catalog_records is not None else load_catalog_records()
    return {str(record.get("layer_key")): record for record in records if record.get("layer_key")}


def _enriched_selected_layers(
    recipe: dict[str, Any],
    catalog_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    lookup = _catalog_lookup(catalog_records)
    enriched: list[dict[str, Any]] = []
    for layer in recipe.get("selected_layers") or []:
        merged = deepcopy(lookup.get(str(layer.get("layer_key")), {}))
        merged.update({key: value for key, value in layer.items() if value is not None})
        enriched.append(merged)
    return enriched


def _find_layer(layers: list[dict[str, Any]], *, category: str | None = None, contains: str | None = None) -> dict[str, Any] | None:
    for layer in layers:
        if category and layer.get("category") != category:
            continue
        if contains and contains.lower() not in _layer_text(layer):
            continue
        if layer.get("is_group_layer") and not layer.get("is_feature_layer"):
            continue
        if layer.get("layer_url") or layer.get("rest_url"):
            return layer
    return None


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


def _is_historical_request(recipe: dict[str, Any]) -> bool:
    parsed = recipe.get("parsed_request") or {}
    return bool(parsed.get("historical_year") or "historical" in (parsed.get("time_references") or []))


def _operation_from_recipe(recipe: dict[str, Any], layers: list[dict[str, Any]]) -> AnalysisOperationType:
    if _is_historical_request(recipe):
        return AnalysisOperationType.UNSUPPORTED_OPERATION
    categories = {layer.get("category") for layer in layers}
    if {"parcel", "flood"}.issubset(categories) and _requested_geography(recipe):
        return AnalysisOperationType.SELECT_BY_INTERSECTION
    if "zoning" in categories and "commercial" in (recipe.get("parsed_request", {}).get("topic_details", {}).get("zoning_modifiers") or []):
        return AnalysisOperationType.ATTRIBUTE_FILTER_ONLY
    for operation in recipe.get("spatial_operations") or []:
        name = operation.get("operation") if isinstance(operation, dict) else None
        if name in {"proximity_search", "buffer_or_proximity"}:
            return AnalysisOperationType.SELECT_BY_DISTANCE
        if name == "summarize_by_boundary":
            return AnalysisOperationType.SUMMARIZE_BY_BOUNDARY
    return AnalysisOperationType.UNSUPPORTED_OPERATION


def _supported_ops() -> list[str]:
    return [
        AnalysisOperationType.FILTER_BY_GEOGRAPHY.value,
        AnalysisOperationType.SELECT_BY_INTERSECTION.value,
        AnalysisOperationType.ATTRIBUTE_FILTER_ONLY.value,
    ]


def _plan_steps(operation_type: AnalysisOperationType, geography_name: str | None, constraint: AnalysisLayerRef | None) -> list[str]:
    if operation_type == AnalysisOperationType.SELECT_BY_INTERSECTION:
        constraint_name = constraint.layer_name if constraint else "constraint layer"
        return [
            f"Filter MunicipalDistrict to {geography_name}.",
            f"Query {constraint_name} geometry using bounded REST requests.",
            f"Query parcel ObjectIDs using {constraint_name} geometry before downloading parcel geometry.",
            "Deduplicate parcel ObjectIDs and enforce download limits.",
            f"Download only selected parcels and intersect them with {constraint_name} locally.",
            "Write selected parcel GeoJSON under outputs/analysis.",
        ]
    if operation_type == AnalysisOperationType.ATTRIBUTE_FILTER_ONLY:
        return [
            "Use trusted field/filter intelligence to build an attribute where clause.",
            "Run a count-only query first.",
            "Only fetch bounded matching features if the count is below the configured max.",
            "Write local GeoJSON only when feature download is safe.",
        ]
    return ["Operation is not executable in v2.2; return review guidance only."]


def _count_or_unavailable(client: SpatialQueryClient, layer: AnalysisLayerRef | None, where: str | None = None) -> dict[str, Any] | None:
    if not layer or not layer.layer_url:
        return None
    try:
        return client.query_count(layer.layer_url, where=where)
    except Exception as exc:
        return {"count": None, "error": str(exc), "where": where or "1=1", "return_geometry": False}


def _filter_plan_where(recipe: dict[str, Any], layer_key: str | None) -> str | None:
    if not layer_key:
        return None
    entry = (recipe.get("filter_plan") or {}).get(layer_key)
    if isinstance(entry, dict) and isinstance(entry.get("draft_where_clause"), str):
        where = entry["draft_where_clause"].strip()
        return where or None
    return None


def _commercial_where(recipe: dict[str, Any], layer: dict[str, Any] | None) -> str | None:
    if not layer:
        return None
    where = _filter_plan_where(recipe, layer.get("layer_key"))
    if where:
        return where
    entry = (recipe.get("filter_plan") or {}).get(layer.get("layer_key"))
    if isinstance(entry, dict) and entry.get("selected_field"):
        return f"{entry['selected_field']} IN ('COMMERCIAL', 'OFFICE')"
    fields = layer.get("fields") or []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "")
        alias = str(field.get("alias") or "")
        if any(term in f"{name} {alias}".lower() for term in ["zone", "zoning", "class", "use"]):
            return f"{name} IN ('COMMERCIAL', 'OFFICE')"
    return None


def build_analysis_plan(
    prompt_or_recipe: str | dict[str, Any],
    *,
    catalog_records: list[dict[str, Any]] | None = None,
    query_client: SpatialQueryClient | None = None,
    estimate_counts: bool = True,
    max_features: int = DEFAULT_MAX_FEATURES,
) -> dict[str, Any]:
    """Plan a safe bounded analysis. Count checks do not fetch feature geometry."""
    recipe = build_recipe(prompt_or_recipe, catalog_records, persist_data_gaps=False) if isinstance(prompt_or_recipe, str) else deepcopy(prompt_or_recipe)
    prompt = recipe.get("user_intent") or recipe.get("parsed_request", {}).get("raw_prompt") or ""
    layers = _enriched_selected_layers(recipe, catalog_records)
    operation_type = _operation_from_recipe(recipe, layers)
    geography_name = _requested_geography(recipe)
    target_layer = _find_layer(layers, category="parcel")
    geography_layer = _find_layer(layers, category="jurisdiction") or _find_layer(layers, category="boundary")
    constraint_layer = _find_layer(layers, category="flood")
    attribute_layer = _find_layer(layers, category="zoning")

    blocked_reasons: list[str] = []
    warnings: list[str] = []
    if operation_type == AnalysisOperationType.UNSUPPORTED_OPERATION:
        blocked_reasons.append("This request is not supported for v2.2 spatial execution.")
    if _is_historical_request(recipe):
        blocked_reasons.append("Historical comparison requests are planning-only in v2.2 unless reviewed and narrowed.")
    if operation_type == AnalysisOperationType.SELECT_BY_INTERSECTION:
        missing = []
        if not target_layer:
            missing.append("target parcel layer")
        if not geography_layer:
            missing.append("geography boundary layer")
        if not constraint_layer:
            missing.append("constraint layer")
        if missing:
            blocked_reasons.append(f"Missing required analysis layer(s): {', '.join(missing)}.")
    if operation_type == AnalysisOperationType.ATTRIBUTE_FILTER_ONLY:
        if not attribute_layer:
            blocked_reasons.append("Missing attribute target layer.")
        elif not _commercial_where(recipe, attribute_layer):
            warnings.append("Attribute filter field/value needs review before execution.")

    client = query_client or SpatialQueryClient(max_features=max_features)
    counts: dict[str, Any] = {"max_features": max_features, "hard_max_features": HARD_MAX_FEATURES}
    optimized_plan: dict[str, Any] | None = None
    if estimate_counts:
        for name, layer in {
            "target_unbounded": AnalysisLayerRef.from_layer(target_layer) if target_layer else None,
            "geography": AnalysisLayerRef.from_layer(geography_layer) if geography_layer else None,
            "constraint": AnalysisLayerRef.from_layer(constraint_layer) if constraint_layer else None,
            "attribute": AnalysisLayerRef.from_layer(attribute_layer) if attribute_layer else None,
        }.items():
            count_result = _count_or_unavailable(client, layer)
            if count_result:
                counts[name] = count_result
        if operation_type == AnalysisOperationType.ATTRIBUTE_FILTER_ONLY and attribute_layer:
            where = _commercial_where(recipe, attribute_layer)
            counts["attribute_filtered"] = _count_or_unavailable(client, AnalysisLayerRef.from_layer(attribute_layer), where=where)
        if operation_type == AnalysisOperationType.SELECT_BY_INTERSECTION and target_layer and geography_layer and constraint_layer:
            optimized_plan = optimize_intersection_query_plan(
                recipe,
                target_layer,
                geography_layer,
                constraint_layer,
                query_client=client,
                max_features=max_features,
                include_object_ids=False,
            )
            counts["optimized"] = {
                "strategy": optimized_plan.get("strategy"),
                "broad_count": optimized_plan.get("broad_count"),
                "optimized_candidate_count": optimized_plan.get("optimized_candidate_count"),
                "constraint_feature_count": optimized_plan.get("constraint_feature_count"),
                "chunks_planned": optimized_plan.get("chunks_planned"),
            }
            for reason in optimized_plan.get("blocked_reasons") or []:
                if reason not in blocked_reasons:
                    blocked_reasons.append(reason)

    executable = operation_type in {
        AnalysisOperationType.SELECT_BY_INTERSECTION,
        AnalysisOperationType.ATTRIBUTE_FILTER_ONLY,
    } and not blocked_reasons
    plan = AnalysisPlanResult(
        raw_prompt=prompt,
        operation_type=operation_type,
        executable=executable,
        supported_operations=_supported_ops(),
        blocked_reasons=blocked_reasons,
        warnings=warnings,
        estimated_query_counts=counts,
        recommended_execution_plan=_plan_steps(
            operation_type,
            geography_name,
            AnalysisLayerRef.from_layer(constraint_layer) if constraint_layer else None,
        ),
        target_layer=AnalysisLayerRef.from_layer(target_layer) if target_layer else None,
        geography_layer=AnalysisLayerRef.from_layer(geography_layer) if geography_layer else None,
        constraint_layer=AnalysisLayerRef.from_layer(constraint_layer) if constraint_layer else None,
        attribute_layer=AnalysisLayerRef.from_layer(attribute_layer) if attribute_layer else None,
        max_features=max_features,
        hard_max_features=HARD_MAX_FEATURES,
    )
    result = plan.to_dict()
    result["recipe"] = recipe
    if optimized_plan:
        slim_optimized_plan = {
            key: value
            for key, value in optimized_plan.items()
            if key not in {"candidate_object_ids", "geography_features", "constraint_features"}
        }
        result["optimized_query_plan"] = slim_optimized_plan
        result["query_strategy"] = optimized_plan.get("strategy")
        result["strategy_explanation"] = optimized_plan.get("strategy_explanation")
        result["narrowing_suggestions"] = optimized_plan.get("narrowing_suggestions") or []
    return result


def analysis_execution_for_recipe(recipe: dict[str, Any], catalog_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return the recipe-level v2.2 analysis execution block without live queries."""
    plan = build_analysis_plan(recipe, catalog_records=catalog_records, estimate_counts=False)
    return {
        "executable": plan["executable"],
        "supported_operations": plan["supported_operations"],
        "blocked_reasons": plan["blocked_reasons"],
        "estimated_query_counts": plan["estimated_query_counts"],
        "recommended_execution_plan": plan["recommended_execution_plan"],
        "operation_type": plan["operation_type"],
        "optimized_query_plan": plan.get("optimized_query_plan"),
        "query_strategy": plan.get("query_strategy"),
        "strategy_explanation": plan.get("strategy_explanation"),
        "narrowing_suggestions": plan.get("narrowing_suggestions") or [],
        "analysis_run_id": None,
        "derived_outputs": [],
    }


def _properties_contain_value(feature: dict[str, Any], value: str) -> bool:
    text = json.dumps(feature.get("properties") or {}, default=str).lower()
    return value.lower() in text


def _query_bounded_features(
    client: SpatialQueryClient,
    layer: AnalysisLayerRef,
    *,
    where: str | None = None,
    geometry: dict[str, Any] | None = None,
    spatial_rel: str | None = SPATIAL_REL_INTERSECTS,
    max_features: int,
) -> dict[str, Any]:
    if not layer.layer_url:
        raise SpatialQueryError(f"Layer URL is missing for {layer.layer_name}.")
    return client.query_features(
        layer.layer_url,
        where=where,
        geometry=geometry,
        geometry_type=ENVELOPE_GEOMETRY_TYPE if geometry else None,
        spatial_rel=spatial_rel if geometry else None,
        result_record_count=max_features,
        return_geometry=True,
    )


def _blocked_execution(
    recipe: dict[str, Any],
    plan: dict[str, Any],
    reason: str,
    *,
    input_counts: dict[str, Any] | None = None,
) -> AnalysisExecutionResult:
    run_id = f"analysis_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    warnings = list(plan.get("warnings") or [])
    blocked = []
    for item in [*list(plan.get("blocked_reasons") or []), reason]:
        if item and item not in blocked:
            blocked.append(item)
    receipt = {
        "analysis_run_id": run_id,
        "status": "blocked",
        "operation_type": plan.get("operation_type"),
        "blocked_status": True,
        "blocked_reasons": blocked,
        "input_counts": input_counts or plan.get("estimated_query_counts") or {},
        "query_strategy": plan.get("query_strategy"),
        "optimized_query_plan": plan.get("optimized_query_plan"),
        "strategy_explanation": plan.get("strategy_explanation"),
        "narrowing_suggestions": plan.get("narrowing_suggestions") or [],
        "max_feature_limits": {
            "default_max_features": DEFAULT_MAX_FEATURES,
            "hard_max_features": HARD_MAX_FEATURES,
        },
    }
    return AnalysisExecutionResult(
        analysis_run_id=run_id,
        raw_prompt=plan.get("raw_prompt") or recipe.get("user_intent") or "",
        operation_type=AnalysisOperationType(plan.get("operation_type") or AnalysisOperationType.UNSUPPORTED_OPERATION),
        status="blocked",
        recipe_json=recipe,
        selected_layer_keys=[layer.get("layer_key") for layer in recipe.get("selected_layers") or [] if layer.get("layer_key")],
        input_counts=input_counts or {},
        analysis_receipt=receipt,
        warnings=warnings,
        blocked_reasons=blocked,
    )


def _execute_intersection(
    recipe: dict[str, Any],
    plan: dict[str, Any],
    *,
    query_client: SpatialQueryClient,
    max_features: int,
) -> AnalysisExecutionResult:
    run_id = f"analysis_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    target = AnalysisLayerRef.from_layer(plan["target_layer"])
    geography = AnalysisLayerRef.from_layer(plan["geography_layer"])
    constraint = AnalysisLayerRef.from_layer(plan["constraint_layer"])
    geography_name = _requested_geography(recipe) or "requested geography"
    input_counts: dict[str, Any] = {}
    where_clauses: dict[str, str] = {
        "geography": "optimized geography filter",
        "constraint": "server-side spatial filter against geography",
        "target": "ObjectID query against constraint geometries",
    }
    optimized_plan = optimize_intersection_query_plan(
        recipe,
        target,
        geography,
        constraint,
        query_client=query_client,
        max_features=max_features,
        include_object_ids=True,
    )
    input_counts["optimizer"] = {
        "broad_count": optimized_plan.get("broad_count"),
        "optimized_candidate_count": optimized_plan.get("optimized_candidate_count"),
        "constraint_feature_count": optimized_plan.get("constraint_feature_count"),
        "chunks_planned": optimized_plan.get("chunks_planned"),
    }
    if optimized_plan.get("blocked_reasons"):
        blocked = _blocked_execution(
            recipe,
            plan,
            "; ".join(optimized_plan["blocked_reasons"]),
            input_counts=input_counts,
        )
        blocked.analysis_receipt.update(
            {
                "query_strategy": optimized_plan.get("strategy"),
                "strategy_explanation": optimized_plan.get("strategy_explanation"),
                "optimized_query_plan": {
                    key: value
                    for key, value in optimized_plan.items()
                    if key not in {"candidate_object_ids", "geography_features", "constraint_features"}
                },
                "narrowing_suggestions": optimized_plan.get("narrowing_suggestions") or [],
            }
        )
        return write_analysis_outputs(blocked)

    target_out_fields = target.object_id_field or "OBJECTID"
    candidate_object_ids = optimized_plan.get("candidate_object_ids") or []
    target_result = query_client.query_features_by_object_ids(
        target.layer_url or "",
        object_ids=candidate_object_ids,
        out_fields=target_out_fields,
        return_geometry=True,
        result_record_count=max_features,
    )
    if target_result.get("status") == "blocked":
        blocked = _blocked_execution(recipe, plan, str(target_result.get("blocked_reason")), input_counts=input_counts)
        return write_analysis_outputs(blocked)
    geography_features = optimized_plan.get("geography_features") or []
    constraint_features = optimized_plan.get("constraint_features") or []
    target_features = filter_features_by_polygon(target_result.get("features") or [], geography_features)
    selected_features = intersect_features(target_features, constraint_features)
    input_counts["target"] = {
        "queried_count": target_result.get("count"),
        "candidate_object_id_count": len(candidate_object_ids),
        "downloaded_feature_count": len(target_result.get("features") or []),
        "geography_filtered_count": len(target_features),
        "selected_count": len(selected_features),
        "bounded_by_constraint_geometry": True,
    }

    title = "Selected Parcels - 100-Year Floodplain"
    if "floodway" in constraint.layer_name.lower():
        title = "Selected Parcels - Floodway"
    geojson = make_safe_geojson_output(selected_features, max_features=max_features, name=title)
    receipt = {
        "analysis_run_id": run_id,
        "status": "completed",
        "operation_type": AnalysisOperationType.SELECT_BY_INTERSECTION.value,
        "raw_prompt": recipe.get("user_intent"),
        "target_layer": target.to_dict(),
        "geography_layer": geography.to_dict(),
        "constraint_layer": constraint.to_dict(),
        "where_clauses": where_clauses,
        "target_out_fields": target_out_fields,
        "counts_before_after": input_counts,
        "query_strategy": optimized_plan.get("strategy"),
        "strategy_explanation": optimized_plan.get("strategy_explanation"),
        "optimized_candidate_count": optimized_plan.get("optimized_candidate_count"),
        "broad_count": optimized_plan.get("broad_count"),
        "constraint_feature_count": optimized_plan.get("constraint_feature_count"),
        "chunks_used": optimized_plan.get("chunks_planned"),
        "object_ids_selected": candidate_object_ids,
        "object_ids_selected_count": len(candidate_object_ids),
        "features_downloaded": len(target_result.get("features") or []),
        "chunk_receipts": optimized_plan.get("chunk_receipts") or [],
        "safety_checks": (optimized_plan.get("safety") or {}).get("checks") or [],
        "narrowing_suggestions": optimized_plan.get("narrowing_suggestions") or [],
        "max_feature_limits": {
            "default_max_features": DEFAULT_MAX_FEATURES,
            "run_max_features": max_features,
            "hard_max_features": HARD_MAX_FEATURES,
        },
        "output_count": len(selected_features),
        "output_stats": compute_basic_stats(selected_features),
        "warnings": ["Derived result is local and requires GIS review before official use."],
        "blocked_status": False,
        "derived_layer_title": title,
    }
    result = AnalysisExecutionResult(
        analysis_run_id=run_id,
        raw_prompt=recipe.get("user_intent") or "",
        operation_type=AnalysisOperationType.SELECT_BY_INTERSECTION,
        status="completed",
        recipe_json=recipe,
        selected_layer_keys=[target.layer_key, geography.layer_key, constraint.layer_key],
        input_counts=input_counts,
        output_count=len(selected_features),
        analysis_receipt=receipt,
        warnings=receipt["warnings"],
    )
    return write_analysis_outputs(result, geojson=geojson)


def _execute_attribute_filter(
    recipe: dict[str, Any],
    plan: dict[str, Any],
    *,
    query_client: SpatialQueryClient,
    max_features: int,
) -> AnalysisExecutionResult:
    run_id = f"analysis_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    attribute_layer = AnalysisLayerRef.from_layer(plan["attribute_layer"])
    layer_dict = dict(plan["attribute_layer"] or {})
    where = _commercial_where(recipe, layer_dict)
    if not where:
        blocked = _blocked_execution(recipe, plan, "No safe attribute where clause was available for execution.")
        return write_analysis_outputs(blocked)
    result = _query_bounded_features(query_client, attribute_layer, where=where, max_features=max_features)
    input_counts = {"attribute_filtered": {"count": result.get("count"), "where": where}}
    if result.get("status") == "blocked":
        blocked = _blocked_execution(recipe, plan, str(result.get("blocked_reason")), input_counts=input_counts)
        return write_analysis_outputs(blocked)
    features = result.get("features") or []
    title = f"Selected {attribute_layer.layer_name}"
    geojson = make_safe_geojson_output(features, max_features=max_features, name=title)
    receipt = {
        "analysis_run_id": run_id,
        "status": "completed",
        "operation_type": AnalysisOperationType.ATTRIBUTE_FILTER_ONLY.value,
        "raw_prompt": recipe.get("user_intent"),
        "target_layer": attribute_layer.to_dict(),
        "where_clauses": {"attribute": where},
        "counts_before_after": input_counts,
        "max_feature_limits": {
            "default_max_features": DEFAULT_MAX_FEATURES,
            "run_max_features": max_features,
            "hard_max_features": HARD_MAX_FEATURES,
        },
        "output_count": len(features),
        "output_stats": compute_basic_stats(features),
        "warnings": ["Attribute-only derived result requires field/value review before official use."],
        "blocked_status": False,
        "derived_layer_title": title,
    }
    execution = AnalysisExecutionResult(
        analysis_run_id=run_id,
        raw_prompt=recipe.get("user_intent") or "",
        operation_type=AnalysisOperationType.ATTRIBUTE_FILTER_ONLY,
        status="completed",
        recipe_json=recipe,
        selected_layer_keys=[attribute_layer.layer_key],
        input_counts=input_counts,
        output_count=len(features),
        analysis_receipt=receipt,
        warnings=receipt["warnings"],
    )
    return write_analysis_outputs(execution, geojson=geojson)


def execute_analysis(
    prompt_or_recipe: str | dict[str, Any],
    *,
    catalog_records: list[dict[str, Any]] | None = None,
    query_client: SpatialQueryClient | None = None,
    max_features: int = DEFAULT_MAX_FEATURES,
    estimate_counts: bool = True,
) -> dict[str, Any]:
    """Execute a supported bounded analysis and write local outputs."""
    init_analysis_tables()
    recipe = build_recipe(prompt_or_recipe, catalog_records, persist_data_gaps=False) if isinstance(prompt_or_recipe, str) else deepcopy(prompt_or_recipe)
    plan = build_analysis_plan(recipe, catalog_records=catalog_records, query_client=query_client, estimate_counts=estimate_counts, max_features=max_features)
    client = query_client or SpatialQueryClient(max_features=max_features)
    if not plan.get("executable"):
        plan_reasons = list(plan.get("blocked_reasons") or [])
        result = _blocked_execution(recipe, plan, plan_reasons[0] if plan_reasons else "Analysis plan is not executable.")
        result = write_analysis_outputs(result)
        record_analysis_run(result)
        return result.to_dict()
    try:
        if plan["operation_type"] == AnalysisOperationType.SELECT_BY_INTERSECTION.value:
            result = _execute_intersection(recipe, plan, query_client=client, max_features=max_features)
        elif plan["operation_type"] == AnalysisOperationType.ATTRIBUTE_FILTER_ONLY.value:
            result = _execute_attribute_filter(recipe, plan, query_client=client, max_features=max_features)
        else:
            result = _blocked_execution(recipe, plan, f"{plan['operation_type']} is stubbed in v2.2.")
            result = write_analysis_outputs(result)
    except (SpatialQueryError, GeometrySafetyError, ValueError) as exc:
        result = _blocked_execution(recipe, plan, str(exc))
        result = write_analysis_outputs(result)
    result.recipe_json.setdefault("analysis_execution", {})
    result.recipe_json["analysis_execution"].update(
        {
            "analysis_run_id": result.analysis_run_id,
            "derived_outputs": [result.derived_layer] if result.derived_layer else [],
        }
    )
    result.analysis_receipt["analysis_run_id"] = result.analysis_run_id
    result.analysis_receipt["derived_layer"] = result.derived_layer
    if result.output_folder:
        output_folder = repo_root() / result.output_folder
        if output_folder.exists():
            (output_folder / "input_recipe.json").write_text(json.dumps(result.recipe_json, indent=2, default=str), encoding="utf-8")
            (output_folder / "analysis_receipt.json").write_text(json.dumps(result.analysis_receipt, indent=2, default=str), encoding="utf-8")
    record_analysis_run(result)
    return result.to_dict()


def list_runs(limit: int = 50) -> list[dict[str, Any]]:
    """List analysis runs via the result store."""
    return list_analysis_runs(limit=limit)


def validate_run(analysis_run_id_or_path: str | Path) -> dict[str, Any]:
    """Validate an analysis run via the result store."""
    return validate_analysis_run(analysis_run_id_or_path)
