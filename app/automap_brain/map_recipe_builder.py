"""Recipe metadata attachment for AutoMap Brain v2."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.automap_brain.explain_plan import build_brain_explanation
from app.automap_brain.field_value_resolver import resolve_field_values
from app.automap_brain.layer_ranker import attach_layer_rank_explanations, rank_candidate_layers


def _elapsed_ms(start: float) -> int:
    return int(round((perf_counter() - start) * 1000))


def attach_brain_recipe_metadata(recipe: dict[str, Any], catalog_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    started = perf_counter()
    plan = recipe.get("request_plan") or {}
    layer_rank_start = perf_counter()
    ranked = rank_candidate_layers(plan, catalog_records or recipe.get("selected_layers") or [])
    layer_rank_ms = _elapsed_ms(layer_rank_start)
    recipe = attach_layer_rank_explanations(recipe, ranked)
    field_start = perf_counter()
    field_resolution = resolve_field_values(recipe, catalog_records)
    field_ms = _elapsed_ms(field_start)
    recipe["automap_brain"] = {
        "version": "automap_brain_v2",
        "request_plan": plan,
        "layer_rankings": recipe.get("brain_layer_rankings") or [],
        "field_value_resolution": field_resolution,
        "explanation": build_brain_explanation(recipe),
        "timing": {"layer_rank_ms": layer_rank_ms, "field_resolve_ms": field_ms, "total_ms": _elapsed_ms(started)},
    }
    return recipe
