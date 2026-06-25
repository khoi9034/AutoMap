"""Recipe metadata attachment for AutoMap Brain v2."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.automap_brain.aoi_planner import build_aoi_plan
from app.automap_brain.explain_plan import build_brain_explanation
from app.automap_brain.fallback_planner import plan_fallbacks
from app.automap_brain.field_value_resolver import resolve_field_values
from app.automap_brain.intent_classifier import classify_intent
from app.automap_brain.layer_ranker import attach_layer_rank_explanations, rank_candidate_layers
from app.automap_brain.parameter_extractor import extract_parameters
from app.automap_brain.spatial_operation_planner import plan_spatial_operation


def _elapsed_ms(start: float) -> int:
    return int(round((perf_counter() - start) * 1000))


def attach_brain_recipe_metadata(recipe: dict[str, Any], catalog_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    started = perf_counter()
    plan = recipe.get("request_plan") or {}
    prompt = str(recipe.get("user_intent") or recipe.get("parsed_request", {}).get("raw_prompt") or "")
    intent_start = perf_counter()
    intent = classify_intent(prompt, recipe.get("parsed_request") or None)
    parameters = extract_parameters(prompt, recipe.get("parsed_request") or None, plan)
    aoi = build_aoi_plan(recipe)
    spatial_operation = plan_spatial_operation(plan, parameters)
    fallback = plan_fallbacks(plan, spatial_operation)
    intent_ms = _elapsed_ms(intent_start)
    plan.update(
        {
            "original_prompt": prompt,
            "aoi": aoi,
            "target_features": parameters.get("target_features") or [],
            "context_features": parameters.get("context_features") or [],
            "spatial_relationship": spatial_operation.get("spatial_relationship"),
            "spatial_operation": spatial_operation.get("operation"),
            "layer_roles": spatial_operation.get("layer_roles") or [],
            "required_fields": parameters.get("requested_fields") or [],
            "fallback_strategy": fallback,
            "expected_result": spatial_operation.get("result_layer_role"),
            "explanation": spatial_operation.get("reasoning"),
        }
    )
    recipe["request_plan"] = plan
    layer_rank_start = perf_counter()
    ranked = rank_candidate_layers(plan, catalog_records or recipe.get("selected_layers") or [])
    layer_rank_ms = _elapsed_ms(layer_rank_start)
    recipe = attach_layer_rank_explanations(recipe, ranked)
    field_start = perf_counter()
    field_resolution = resolve_field_values(recipe, catalog_records)
    field_ms = _elapsed_ms(field_start)
    recipe["automap_brain"] = {
        "version": "automap_brain_v2",
        "kernel_version": "automap_brain_kernel_v1",
        "request_plan": plan,
        "intent": intent,
        "parameters": parameters,
        "aoi": aoi,
        "spatial_operation": spatial_operation,
        "fallback_plan": fallback,
        "layer_rankings": recipe.get("brain_layer_rankings") or [],
        "field_value_resolution": field_resolution,
        "explanation": build_brain_explanation(recipe),
        "timing": {
            "intent_parameter_ms": intent_ms,
            "layer_rank_ms": layer_rank_ms,
            "field_resolve_ms": field_ms,
            "total_ms": _elapsed_ms(started),
        },
    }
    return recipe
