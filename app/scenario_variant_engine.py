"""Create and manage reviewable scenario variants."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.db import _quote_identifier, get_engine
from app.scenario_builder import get_scenario
from app.scenario_workbench_models import (
    MISSING_DATA_NOTICE,
    PROXY_CONTEXT_NOTICE,
    SCENARIO_WORKBENCH_NOTICE,
    VARIANT_OFFICIAL_USE_DISCLAIMER,
    ScenarioVariantRequest,
)


FACTOR_KEY_ALIASES = {
    "aadt_high_traffic": "high_aadt",
    "high_traffic": "high_aadt",
    "traffic": "high_aadt",
    "floodplain_avoidance": "flood_constraint",
    "avoid_floodplain": "flood_constraint",
    "flood_avoidance": "flood_constraint",
    "road_priority": "road_access",
    "road_access_priority": "road_access",
    "permits_gap": "missing_current_permits",
}


def _variant_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.scenario_variants"


def init_scenario_variant_table(schema_name: str = "automap") -> None:
    """Create the additive scenario variant table in AutoMap's own schema."""
    table = _variant_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY,
                    variant_id text UNIQUE,
                    source_scenario_id text,
                    variant_name text,
                    variant_description text,
                    weight_overrides jsonb,
                    enabled_factors jsonb,
                    disabled_factors jsonb,
                    reviewer_assumptions jsonb,
                    variant_json jsonb,
                    created_at timestamptz DEFAULT now(),
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "variant_id": "text UNIQUE",
            "source_scenario_id": "text",
            "variant_name": "text",
            "variant_description": "text",
            "weight_overrides": "jsonb",
            "enabled_factors": "jsonb",
            "disabled_factors": "jsonb",
            "reviewer_assumptions": "jsonb",
            "variant_json": "jsonb",
            "created_at": "timestamptz DEFAULT now()",
            "updated_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _canonical_factor_key(key: str) -> str:
    return FACTOR_KEY_ALIASES.get(key, key)


def _canonical_mapping(mapping: dict[str, Any]) -> dict[str, Any]:
    return {_canonical_factor_key(str(key)): value for key, value in mapping.items()}


def _canonical_list(values: list[str]) -> list[str]:
    return [_canonical_factor_key(str(value)) for value in values]


def _base_factor_weight(factor: dict[str, Any]) -> float:
    try:
        return float(factor.get("suggested_weight") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _is_proxy_or_reference(factor: dict[str, Any]) -> bool:
    return factor.get("factor_type") in {"proxy", "context"} or factor.get("direction") == "reference_only"


def _is_missing_official_factor(factor: dict[str, Any]) -> bool:
    key = str(factor.get("factor_key") or "")
    label = str(factor.get("factor_label") or "").lower()
    return key.startswith("missing_") or "missing official" in label


def _normalize_factor_weights(factors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    total = sum(abs(float(factor.get("reviewer_weight") or 0.0)) for factor in factors if factor.get("enabled", True))
    normalized: list[dict[str, Any]] = []
    for factor in factors:
        item = dict(factor)
        weight = float(item.get("reviewer_weight") or 0.0) if item.get("enabled", True) else 0.0
        item["normalized_weight"] = weight / total if total else 0.0
        item["normalized_percent"] = round((abs(weight) / total) * 100, 2) if total else 0.0
        normalized.append(item)
    return normalized


def normalize_variant_weights(variant: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of a variant with normalized factor weights."""
    result = deepcopy(variant)
    result["factor_weights"] = _normalize_factor_weights(result.get("factor_weights") or [])
    result["normalized_weights"] = [
        {
            "factor_key": factor.get("factor_key"),
            "reviewer_weight": factor.get("reviewer_weight"),
            "normalized_weight": factor.get("normalized_weight"),
            "normalized_percent": factor.get("normalized_percent"),
            "enabled": factor.get("enabled", True),
        }
        for factor in result["factor_weights"]
    ]
    return result


def explain_variant_changes(base_scenario: dict[str, Any], variant: dict[str, Any]) -> dict[str, Any]:
    """Summarize what changed from the source scenario."""
    base_factors = {
        factor.get("factor_key"): factor
        for factor in base_scenario.get("scoring_framework") or []
        if factor.get("factor_key")
    }
    changed_weights: list[dict[str, Any]] = []
    direction_changes: list[dict[str, Any]] = []
    disabled: list[str] = []
    for factor in variant.get("factor_weights") or []:
        key = factor.get("factor_key")
        base = base_factors.get(key) or {}
        if not factor.get("enabled", True):
            disabled.append(str(key))
        if float(factor.get("reviewer_weight") or 0.0) != float(base.get("suggested_weight") or 0.0):
            changed_weights.append(
                {
                    "factor_key": key,
                    "from": base.get("suggested_weight", 0.0),
                    "to": factor.get("reviewer_weight", 0.0),
                }
            )
        if factor.get("direction") != base.get("direction"):
            direction_changes.append({"factor_key": key, "from": base.get("direction"), "to": factor.get("direction")})
    return {
        "changed_weights": changed_weights,
        "direction_changes": direction_changes,
        "disabled_factors": disabled,
        "reviewer_assumptions_added": variant.get("reviewer_assumptions") or [],
    }


def validate_variant_safety(variant: dict[str, Any]) -> dict[str, Any]:
    """Check that variant tuning keeps proxy and missing-data caveats visible."""
    warnings: list[str] = [SCENARIO_WORKBENCH_NOTICE, PROXY_CONTEXT_NOTICE]
    blocked: list[str] = []
    proxy_warnings: list[str] = []
    missing_warnings: list[str] = []
    for factor in variant.get("factor_weights") or []:
        weight = float(factor.get("reviewer_weight") or 0.0)
        key = str(factor.get("factor_key") or "")
        if factor.get("factor_type") in {"proxy", "context"} and weight:
            proxy_warnings.append(
                f"{factor.get('factor_label') or key} is proxy/reference context with a non-zero reviewer weight."
            )
        if _is_missing_official_factor(factor):
            missing_warnings.append(MISSING_DATA_NOTICE)
            if weight > 0:
                blocked.append(f"{factor.get('factor_label') or key} cannot receive a positive opportunity score.")
        if "flood" in key and weight > 0 and factor.get("direction") != "presence_is_bad":
            warnings.append("Flood constraints were changed away from a penalty; review this assumption carefully.")
    for warning in variant.get("source_coverage", {}).get("warnings") or []:
        warnings.append(str(warning))
    for item in variant.get("missing_data") or []:
        missing_warnings.append(f"Missing official source remains unresolved: {item}.")
    unique_missing = list(dict.fromkeys(missing_warnings))
    return {
        "is_safe": not blocked,
        "safety_level": "blocked" if blocked else "review_needed" if proxy_warnings or unique_missing else "safe",
        "safety_warnings": list(dict.fromkeys(warnings + proxy_warnings + unique_missing)),
        "proxy_warnings": list(dict.fromkeys(proxy_warnings + (variant.get("proxy_warnings") or []))),
        "missing_data_warnings": unique_missing,
        "blocked_reasons": blocked,
    }


def _factor_weights_for_variant(
    base_scenario: dict[str, Any],
    request: ScenarioVariantRequest,
) -> list[dict[str, Any]]:
    weight_overrides = _canonical_mapping(request.weight_overrides)
    direction_overrides = _canonical_mapping(request.direction_overrides)
    reviewer_notes = _canonical_mapping(request.reviewer_notes)
    enabled_factors = set(_canonical_list(request.enabled_factors))
    disabled_factors = set(_canonical_list(request.disabled_factors))
    result: list[dict[str, Any]] = []
    for factor in base_scenario.get("scoring_framework") or []:
        item = dict(factor)
        key = str(item.get("factor_key") or "")
        enabled = key not in disabled_factors
        if enabled_factors:
            enabled = key in enabled_factors
        reviewer_weight = float(weight_overrides[key]) if key in weight_overrides else _base_factor_weight(item)
        if _is_proxy_or_reference(item) and key not in weight_overrides:
            reviewer_weight = 0.0
        if _is_missing_official_factor(item) and reviewer_weight > 0:
            reviewer_weight = 0.0
        item.update(
            {
                "reviewer_weight": reviewer_weight if enabled else 0.0,
                "enabled": enabled,
                "direction": str(direction_overrides.get(key) or item.get("direction") or "reference_only"),
                "reviewer_note": str(reviewer_notes.get(key) or ""),
                "needs_review": True if item.get("factor_type") in {"proxy", "context"} else bool(item.get("needs_review", True)),
            }
        )
        result.append(item)
    return _normalize_factor_weights(result)


def build_variant_json(
    base_scenario: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a variant object without writing it."""
    request = ScenarioVariantRequest.from_mapping(overrides)
    variant_id = f"variant_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    variant = {
        "variant_id": variant_id,
        "source_scenario_id": base_scenario["scenario_id"],
        "scenario_type": base_scenario.get("scenario_type"),
        "scenario_title": base_scenario.get("scenario_title"),
        "variant_name": request.variant_name,
        "variant_description": request.variant_description,
        "selected_layer_keys": sorted(
            {
                str(layer.get("layer_key"))
                for layer in base_scenario.get("selected_layers") or []
                if layer.get("layer_key")
            }
        ),
        "required_layers": base_scenario.get("required_layers") or [],
        "optional_layers": base_scenario.get("optional_layers") or [],
        "review_questions": base_scenario.get("review_questions") or [],
        "factor_weights": _factor_weights_for_variant(base_scenario, request),
        "enabled_factors": _canonical_list(request.enabled_factors),
        "disabled_factors": _canonical_list(request.disabled_factors),
        "weight_overrides": _canonical_mapping(request.weight_overrides),
        "direction_overrides": _canonical_mapping(request.direction_overrides),
        "reviewer_assumptions": request.reviewer_assumptions,
        "source_coverage": base_scenario.get("source_coverage") or {},
        "missing_data": base_scenario.get("missing_data") or [],
        "proxy_warnings": base_scenario.get("proxy_warnings") or [],
        "official_use_disclaimer": VARIANT_OFFICIAL_USE_DISCLAIMER,
        "created_at": datetime.now(UTC).isoformat(),
    }
    variant = normalize_variant_weights(variant)
    variant["changes_from_base"] = explain_variant_changes(base_scenario, variant)
    safety = validate_variant_safety(variant)
    variant.update(safety)
    return variant


def create_scenario_variant(
    scenario_id: str,
    overrides: dict[str, Any] | None = None,
    *,
    persist: bool = True,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Create a stored scenario variant."""
    base_scenario = get_scenario(scenario_id, schema_name=schema_name)
    variant = build_variant_json(base_scenario, overrides)
    if persist:
        record_scenario_variant(variant, schema_name=schema_name)
    return variant


def record_scenario_variant(variant: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    init_scenario_variant_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {_variant_table(schema_name)} (
                    variant_id, source_scenario_id, variant_name, variant_description,
                    weight_overrides, enabled_factors, disabled_factors,
                    reviewer_assumptions, variant_json, updated_at
                )
                VALUES (
                    :variant_id, :source_scenario_id, :variant_name, :variant_description,
                    CAST(:weight_overrides AS jsonb), CAST(:enabled_factors AS jsonb),
                    CAST(:disabled_factors AS jsonb), CAST(:reviewer_assumptions AS jsonb),
                    CAST(:variant_json AS jsonb), now()
                )
                ON CONFLICT (variant_id) DO UPDATE SET
                    source_scenario_id = EXCLUDED.source_scenario_id,
                    variant_name = EXCLUDED.variant_name,
                    variant_description = EXCLUDED.variant_description,
                    weight_overrides = EXCLUDED.weight_overrides,
                    enabled_factors = EXCLUDED.enabled_factors,
                    disabled_factors = EXCLUDED.disabled_factors,
                    reviewer_assumptions = EXCLUDED.reviewer_assumptions,
                    variant_json = EXCLUDED.variant_json,
                    updated_at = now();
                """
            ),
            {
                "variant_id": variant["variant_id"],
                "source_scenario_id": variant["source_scenario_id"],
                "variant_name": variant["variant_name"],
                "variant_description": variant.get("variant_description") or "",
                "weight_overrides": json.dumps(variant.get("weight_overrides") or {}, default=str),
                "enabled_factors": json.dumps(variant.get("enabled_factors") or [], default=str),
                "disabled_factors": json.dumps(variant.get("disabled_factors") or [], default=str),
                "reviewer_assumptions": json.dumps(variant.get("reviewer_assumptions") or [], default=str),
                "variant_json": json.dumps(variant, default=str),
            },
        )
    return variant


def get_scenario_variant(variant_id: str, schema_name: str = "automap") -> dict[str, Any]:
    init_scenario_variant_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(f"SELECT variant_json FROM {_variant_table(schema_name)} WHERE variant_id = :variant_id;"),
            {"variant_id": variant_id},
        ).scalar_one_or_none()
    if row is None:
        raise FileNotFoundError(f"Scenario variant not found: {variant_id}")
    return dict(row)


def list_scenario_variants(
    scenario_id: str | None = None,
    *,
    limit: int = 50,
    schema_name: str = "automap",
) -> list[dict[str, Any]]:
    init_scenario_variant_table(schema_name)
    where = "WHERE source_scenario_id = :scenario_id" if scenario_id else ""
    params: dict[str, Any] = {"limit": limit}
    if scenario_id:
        params["scenario_id"] = scenario_id
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT variant_id, source_scenario_id, variant_name, variant_description,
                       weight_overrides, enabled_factors, disabled_factors,
                       reviewer_assumptions, variant_json, created_at, updated_at
                FROM {_variant_table(schema_name)}
                {where}
                ORDER BY updated_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            params,
        ).mappings()
        return [dict(row) for row in rows]
