"""Compare planning scenarios and reviewer variants."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import _quote_identifier, get_engine
from app.scenario_builder import get_scenario
from app.scenario_variant_engine import get_scenario_variant


def _comparison_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.scenario_comparisons"


def init_scenario_comparison_table(schema_name: str = "automap") -> None:
    table = _comparison_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY,
                    comparison_id text UNIQUE,
                    scenario_ids jsonb,
                    variant_ids jsonb,
                    comparison_json jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "comparison_id": "text UNIQUE",
            "scenario_ids": "jsonb",
            "variant_ids": "jsonb",
            "comparison_json": "jsonb",
            "created_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _scenario_factor_weights(scenario: dict[str, Any]) -> dict[str, float]:
    return {
        str(factor.get("factor_key")): float(factor.get("suggested_weight") or 0.0)
        for factor in scenario.get("scoring_framework") or []
        if factor.get("factor_key")
    }


def _variant_factor_weights(variant: dict[str, Any]) -> dict[str, float]:
    return {
        str(factor.get("factor_key")): float(factor.get("reviewer_weight") or 0.0)
        for factor in variant.get("factor_weights") or []
        if factor.get("factor_key")
    }


def _layer_keys(item: dict[str, Any]) -> set[str]:
    if item.get("variant_id"):
        return set(item.get("selected_layer_keys") or item.get("required_layers") or [])
    return set(item.get("required_layers") or []) | set(item.get("optional_layers") or [])


def compare_factor_weights(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    weight_maps = [
        _variant_factor_weights(item) if item.get("variant_id") else _scenario_factor_weights(item)
        for item in items
    ]
    all_keys = sorted({key for weights in weight_maps for key in weights})
    return [
        {
            "factor_key": key,
            "weights": {
                str(items[index].get("variant_id") or items[index].get("scenario_id")): weight_maps[index].get(key, 0.0)
                for index in range(len(items))
            },
        }
        for key in all_keys
    ]


def compare_required_layers(items: list[dict[str, Any]]) -> dict[str, Any]:
    maps = {str(item.get("variant_id") or item.get("scenario_id")): sorted(_layer_keys(item)) for item in items}
    all_layers = sorted({layer for layers in maps.values() for layer in layers})
    common = sorted(set(all_layers).intersection(*(set(layers) for layers in maps.values()))) if maps else []
    return {
        "by_item": maps,
        "common_layers": common,
        "unique_layers": {
            item_id: sorted(set(layers) - set(common))
            for item_id, layers in maps.items()
        },
    }


def compare_source_coverage(items: list[dict[str, Any]]) -> dict[str, Any]:
    keys = ["official_sources", "proxy_sources", "limited_coverage_sources", "reference_sources", "missing_official_sources"]
    return {
        str(item.get("variant_id") or item.get("scenario_id")): {
            key: len((item.get("source_coverage") or {}).get(key) or [])
            for key in keys
        }
        for item in items
    }


def compare_missing_data(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        str(item.get("variant_id") or item.get("scenario_id")): [str(value) for value in (item.get("missing_data") or [])]
        for item in items
    }


def compare_review_questions(items: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        str(item.get("variant_id") or item.get("scenario_id")): [str(value) for value in (item.get("review_questions") or [])]
        for item in items
    }


def build_comparison_summary(comparison: dict[str, Any]) -> list[str]:
    focus = ["Review factor weight differences before using any scenario for staff discussion."]
    if any(comparison.get("missing_data_differences", {}).values()):
        focus.append("Missing official data remains visible and should be discussed before further analysis.")
    if any(values.get("proxy_sources") for values in comparison.get("source_coverage_differences", {}).values()):
        focus.append("Proxy sources are present; do not treat them as official approvals.")
    if any(item.get("factor_key") for item in comparison.get("factor_differences") or []):
        focus.append("Compare opportunity and constraint weights side by side.")
    return focus


def _record_comparison(comparison: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    init_scenario_comparison_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {_comparison_table(schema_name)} (
                    comparison_id, scenario_ids, variant_ids, comparison_json
                )
                VALUES (
                    :comparison_id, CAST(:scenario_ids AS jsonb),
                    CAST(:variant_ids AS jsonb), CAST(:comparison_json AS jsonb)
                )
                ON CONFLICT (comparison_id) DO UPDATE SET
                    scenario_ids = EXCLUDED.scenario_ids,
                    variant_ids = EXCLUDED.variant_ids,
                    comparison_json = EXCLUDED.comparison_json;
                """
            ),
            {
                "comparison_id": comparison["comparison_id"],
                "scenario_ids": json.dumps(comparison.get("scenario_ids") or [], default=str),
                "variant_ids": json.dumps(comparison.get("variant_ids") or [], default=str),
                "comparison_json": json.dumps(comparison, default=str),
            },
        )
    return comparison


def compare_scenarios(
    scenario_ids: list[str] | None = None,
    variant_ids: list[str] | None = None,
    *,
    persist: bool = True,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Compare stored scenarios and variants."""
    scenario_ids = [value for value in (scenario_ids or []) if value]
    variant_ids = [value for value in (variant_ids or []) if value]
    scenarios = [get_scenario(scenario_id, schema_name=schema_name) for scenario_id in scenario_ids]
    variants = [get_scenario_variant(variant_id, schema_name=schema_name) for variant_id in variant_ids]
    items = [*scenarios, *variants]
    if len(items) < 2:
        raise ValueError("At least two scenarios or variants are required for comparison.")
    comparison = {
        "comparison_id": f"comparison_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
        "scenario_ids": scenario_ids,
        "variant_ids": variant_ids,
        "items": [
            {
                "id": item.get("variant_id") or item.get("scenario_id"),
                "name": item.get("variant_name") or item.get("scenario_title"),
                "type": "variant" if item.get("variant_id") else "scenario",
                "scenario_type": item.get("scenario_type"),
            }
            for item in items
        ],
        "factor_differences": compare_factor_weights(items),
        "layer_differences": compare_required_layers(items),
        "source_coverage_differences": compare_source_coverage(items),
        "missing_data_differences": compare_missing_data(items),
        "review_question_differences": compare_review_questions(items),
        "created_at": datetime.now(UTC).isoformat(),
    }
    comparison["recommended_review_focus"] = build_comparison_summary(comparison)
    if persist:
        _record_comparison(comparison, schema_name=schema_name)
    return comparison


def list_scenario_comparisons(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    init_scenario_comparison_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT comparison_id, scenario_ids, variant_ids, comparison_json, created_at
                FROM {_comparison_table(schema_name)}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return [dict(row) for row in rows]
