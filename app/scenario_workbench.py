"""Scenario workbench orchestration helpers."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from app.recipe_engine import build_recipe
from app.scenario_builder import get_scenario
from app.scenario_comparison import init_scenario_comparison_table
from app.scenario_variant_engine import get_scenario_variant, init_scenario_variant_table
from app.scenario_workbench_models import (
    MISSING_DATA_NOTICE,
    PROXY_CONTEXT_NOTICE,
    SCENARIO_WORKBENCH_NOTICE,
    VARIANT_OFFICIAL_USE_DISCLAIMER,
)


def init_scenario_workbench_tables(schema_name: str = "automap") -> None:
    """Create all additive scenario workbench tables."""
    init_scenario_variant_table(schema_name)
    init_scenario_comparison_table(schema_name)


def _variant_context(variant: dict[str, Any] | None) -> dict[str, Any] | None:
    if not variant:
        return None
    return {
        "variant_id": variant.get("variant_id"),
        "variant_name": variant.get("variant_name"),
        "factor_weights": variant.get("factor_weights") or [],
        "normalized_weights": variant.get("normalized_weights") or [],
        "changes_from_base": variant.get("changes_from_base") or {},
        "safety_warnings": variant.get("safety_warnings") or [],
        "reviewer_assumptions": variant.get("reviewer_assumptions") or [],
    }


def build_recipe_from_scenario(
    scenario_id: str,
    variant_id: str | None = None,
    *,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Convert a reviewed scenario or variant into a draft map recipe.

    This does not publish, execute geometry scoring, or create any ArcGIS item.
    """
    scenario = get_scenario(scenario_id, schema_name=schema_name)
    variant = get_scenario_variant(variant_id, schema_name=schema_name) if variant_id else None
    recipe = deepcopy(scenario.get("map_recipe") or build_recipe(scenario.get("raw_prompt") or ""))
    recipe["map_title"] = f"{scenario.get('scenario_title') or 'Planning Scenario'} - Draft Recipe"
    recipe["selected_layers"] = scenario.get("selected_layers") or recipe.get("selected_layers") or []
    recipe["source_coverage"] = scenario.get("source_coverage") or recipe.get("source_coverage") or {}
    recipe["missing_data_needed"] = scenario.get("missing_data") or recipe.get("missing_data_needed") or []
    recipe["needs_review"] = True
    recipe["scenario_context"] = {
        "scenario_id": scenario.get("scenario_id"),
        "variant_id": variant_id,
        "scenario_type": scenario.get("scenario_type"),
        "scenario_title": scenario.get("scenario_title"),
        "planning_goal": scenario.get("planning_goal"),
        "scoring_framework": variant.get("factor_weights") if variant else scenario.get("scoring_framework"),
        "variant": _variant_context(variant),
        "official_use_disclaimer": VARIANT_OFFICIAL_USE_DISCLAIMER,
        "execution_status": "scoring_plan_only",
    }
    analysis_plan = dict(recipe.get("analysis_plan") or {})
    analysis_plan["scenario_workbench"] = {
        "goal": scenario.get("planning_goal"),
        "scoring_framework": recipe["scenario_context"]["scoring_framework"] or [],
        "assumptions": [
            *(scenario.get("assumptions") or []),
            *(((variant or {}).get("reviewer_assumptions")) or []),
        ],
        "review_questions": scenario.get("review_questions") or [],
        "blockers": [
            "No geometry scoring is executed by scenario-to-recipe conversion.",
            "Review proxy and missing-data warnings before creating review packets.",
        ],
    }
    recipe["analysis_plan"] = analysis_plan
    review_reasons = list(dict.fromkeys(
        [
            *(recipe.get("review_reasons") or []),
            SCENARIO_WORKBENCH_NOTICE,
            PROXY_CONTEXT_NOTICE,
            MISSING_DATA_NOTICE,
            *((variant or {}).get("safety_warnings") or []),
            *((scenario.get("source_coverage") or {}).get("warnings") or []),
        ]
    ))
    recipe["review_reasons"] = review_reasons
    recipe["notes"] = list(dict.fromkeys(
        [
            *(recipe.get("notes") or []),
            "Scenario-to-recipe conversion created a draft review artifact only.",
            "No ArcGIS item was published and no geometry scoring was executed.",
        ]
    ))
    recipe["scenario_to_recipe"] = {
        "scenario_id": scenario_id,
        "variant_id": variant_id,
        "converted_at": datetime.now(UTC).isoformat(),
        "published": False,
        "requires_human_review": True,
    }
    return {
        "scenario_id": scenario_id,
        "variant_id": variant_id,
        "recipe": recipe,
        "scenario_context": recipe["scenario_context"],
        "warnings": review_reasons,
        "published": False,
    }
