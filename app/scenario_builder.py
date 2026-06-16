"""Build and store reviewable AutoMap planning scenarios."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.data_gap_resolver import safe_gap_context_for_recipe
from app.db import _quote_identifier, get_engine
from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import slugify
from app.prompt_parser import parse_prompt
from app.recipe_engine import build_recipe
from app.scenario_classifier import classify_scenario
from app.scenario_models import EXECUTION_PLAN_ONLY, OFFICIAL_USE_DISCLAIMER
from app.source_usage_intelligence import build_source_coverage, enrich_selected_layers_with_source_usage
from app.suitability_scoring import build_scoring_framework


def _scenario_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.planning_scenarios"


def init_planning_scenario_table(schema_name: str = "automap") -> None:
    """Create the additive planning scenario table in the AutoMap schema."""
    table = _scenario_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY,
                    scenario_id text UNIQUE,
                    raw_prompt text,
                    scenario_type text,
                    scenario_title text,
                    scenario_json jsonb,
                    scoring_framework jsonb,
                    source_coverage jsonb,
                    status text,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "scenario_id": "text UNIQUE",
            "raw_prompt": "text",
            "scenario_type": "text",
            "scenario_title": "text",
            "scenario_json": "jsonb",
            "scoring_framework": "jsonb",
            "source_coverage": "jsonb",
            "status": "text",
            "created_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _as_text(value: Any) -> str:
    return str(value or "").lower()


def _matches_terms(record: dict[str, Any], terms: list[str]) -> bool:
    blob = " ".join(
        [
            _as_text(record.get("layer_key")),
            _as_text(record.get("layer_name")),
            _as_text(record.get("service_name")),
            _as_text(record.get("source_key")),
            " ".join(_as_text(item) for item in (record.get("aliases") or [])),
            " ".join(_as_text(item) for item in (record.get("planning_use_cases") or [])),
        ]
    )
    return any(term in blob for term in terms)


def _best_catalog_record(
    catalog_records: list[dict[str, Any]],
    category: str,
    *,
    terms: list[str] | None = None,
) -> dict[str, Any] | None:
    terms = terms or []
    candidates = [
        record
        for record in catalog_records
        if record.get("category") == category
        and record.get("is_verified")
        and (record.get("approval_status") or "approved") != "needs_review"
        and not record.get("is_group_layer")
        and not record.get("is_historical")
        and (not terms or _matches_terms(record, terms))
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            0 if item.get("source_status") == "active" else 1 if item.get("source_status") == "reference" else 2,
            int(item.get("source_priority") or 999),
            str(item.get("layer_name") or ""),
        ),
    )[0]


def _scenario_title(scenario_type: str, parsed_request: dict[str, Any]) -> str:
    geographies = [
        geo.get("name")
        for geo in parsed_request.get("geography_terms") or []
        if isinstance(geo, dict) and geo.get("name")
    ]
    title = scenario_type.replace("_", " ").title()
    if geographies:
        return f"{title} - {geographies[0]}"
    return title


def _planning_goal(scenario_type: str) -> str:
    goals = {
        "commercial_growth_suitability": "Build a transparent commercial growth suitability framework for reviewer discussion.",
        "residential_growth_suitability": "Build a transparent residential growth suitability framework for reviewer discussion.",
        "development_pressure": "Map development-pressure context while keeping proxy and missing-data limits visible.",
        "constraint_exposure": "Summarize constraint exposure context without making entitlement decisions.",
        "transportation_access": "Show transportation access and traffic context for planning review.",
        "planning_case_context": "Show planning case context with coverage and authority warnings.",
        "flood_avoidance": "Frame flood avoidance as a constraint review workflow.",
        "school_impact_context": "Frame school district context for review without capacity scoring.",
        "historical_change_context": "Compare historical and current context without treating old layers as current.",
    }
    return goals.get(scenario_type, "Create a reviewable planning scenario if sufficient trusted data exists.")


def _scenario_layer_needs(scenario_type: str, prompt: str) -> list[tuple[str, list[str]]]:
    text = prompt.lower()
    needs: list[tuple[str, list[str]]] = []
    if scenario_type in {"commercial_growth_suitability", "residential_growth_suitability", "development_pressure"}:
        needs.extend(
            [
                ("parcel", ["parcel"]),
                ("zoning", ["zoning"]),
                ("transportation", ["centerline", "road"]),
            ]
        )
    if scenario_type in {"commercial_growth_suitability", "transportation_access"} or "high traffic" in text or "aadt" in text:
        needs.append(("transportation", ["aadt", "traffic"]))
    if scenario_type in {"commercial_growth_suitability", "development_pressure", "transportation_access"}:
        needs.append(("transportation_projects", ["stip", "transportation project", "road improvement"]))
    if scenario_type in {"commercial_growth_suitability", "residential_growth_suitability", "development_pressure"}:
        needs.append(("development_activity_proxy", ["accela", "plan review"]))
    if scenario_type in {"commercial_growth_suitability", "residential_growth_suitability", "constraint_exposure", "flood_avoidance"} or "flood" in text:
        needs.append(("flood", ["flood"]))
    if scenario_type in {"residential_growth_suitability", "school_impact_context"} or "school" in text:
        needs.append(("schools", ["school"]))
    if scenario_type == "planning_case_context" or "planning cases" in text:
        needs.append(("planning_cases", ["planning cases", "rezoning"]))
    return needs


def _merge_scenario_layers(
    selected_layers: list[dict[str, Any]],
    catalog_records: list[dict[str, Any]],
    scenario_type: str,
    prompt: str,
    parsed_request: dict[str, Any],
) -> list[dict[str, Any]]:
    merged = [dict(layer) for layer in selected_layers]
    selected_keys = {layer.get("layer_key") for layer in merged}
    for category, terms in _scenario_layer_needs(scenario_type, prompt):
        record = _best_catalog_record(catalog_records, category, terms=terms)
        if not record or record.get("layer_key") in selected_keys:
            continue
        merged.append(
            {
                **record,
                "role": "reference_layer" if category in {"transportation_projects", "development_activity_proxy"} else "scenario_layer",
                "confidence_score": 0.72,
                "match_score": 120.0,
                "match_reasons": [f"scenario template includes {category}"],
                "matched_topic": category,
                "why_selected": "Selected by the deterministic planning scenario template.",
                "review_notes": ["Scenario-selected context layer; review before official use."],
            }
        )
        selected_keys.add(record.get("layer_key"))
    return enrich_selected_layers_with_source_usage(merged, parsed_request)


def _review_questions(scenario_type: str, scoring_framework: list[dict[str, Any]]) -> list[str]:
    questions = [
        "Confirm the scenario weights before using this framework in a staff review.",
        "Confirm whether this scenario should be planning context only or should proceed to a bounded analysis plan.",
    ]
    factor_keys = {factor.get("factor_key") for factor in scoring_framework}
    if "commercial_zoning" in factor_keys:
        questions.append("Which zoning codes should count as commercial or general business?")
    if "high_aadt" in factor_keys:
        questions.append("What AADT threshold should count as high traffic?")
    if "road_access" in factor_keys:
        questions.append("What distance to roads should count as good access?")
    if "flood_constraint" in factor_keys:
        questions.append("Should flood avoidance include floodway, 100-year floodplain, 500-year floodplain, or all flood hazard layers?")
    if scenario_type == "residential_growth_suitability":
        questions.append("Should school district context be included even though official capacity scoring is not available?")
    return questions


def _scenario_status(scenario_type: str) -> str:
    return "needs_review" if scenario_type == "unsupported_scenario" else "draft"


def build_scenario(
    prompt: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    persist: bool = True,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Build a deterministic planning scenario without executing large spatial jobs."""
    parsed_request = parse_prompt(prompt)
    classification = classify_scenario(prompt, parsed_request)
    scenario_type = classification["scenario_type"]
    catalog_records = layer_catalog if layer_catalog is not None else load_catalog_records()
    recipe = build_recipe(prompt, catalog_records, persist_data_gaps=False)
    selected_layers = _merge_scenario_layers(
        recipe.get("selected_layers") or [],
        catalog_records,
        scenario_type,
        prompt,
        parsed_request,
    )
    scoring_framework = build_scoring_framework(scenario_type, selected_layers, parsed_request)
    base_missing = set(recipe.get("missing_data_needed") or [])
    if "environmental" in base_missing and any(layer.get("category") == "flood" for layer in selected_layers):
        base_missing.remove("environmental")
    missing_data = sorted(
        set(
            [
                *base_missing,
                *(["permits"] if scenario_type in {"commercial_growth_suitability", "residential_growth_suitability", "development_pressure"} else []),
            ]
        )
    )
    source_coverage = build_source_coverage(
        selected_layers,
        missing_data,
        safe_gap_context_for_recipe(missing_data),
        parsed_request,
    )
    scenario_id = f"scenario_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"
    title = _scenario_title(scenario_type, parsed_request)
    positive_factors = [factor for factor in scoring_framework if factor.get("factor_type") == "opportunity"]
    negative_factors = [factor for factor in scoring_framework if factor.get("factor_type") == "constraint"]
    proxy_warnings = [
        warning
        for warning in source_coverage.get("warnings") or []
        if "proxy" in warning.lower() or "missing official" in warning.lower()
    ]
    scenario = {
        "scenario_id": scenario_id,
        "raw_prompt": prompt,
        "scenario_type": scenario_type,
        "scenario_title": title,
        "planning_goal": _planning_goal(scenario_type),
        "positive_factors": positive_factors,
        "negative_factors": negative_factors,
        "required_layers": sorted({key for factor in scoring_framework for key in factor.get("layer_keys", []) if key}),
        "optional_layers": [
            layer.get("layer_key")
            for layer in selected_layers
            if layer.get("source_role") in {"proxy", "reference", "limited_coverage"}
        ],
        "excluded_layers": [],
        "selected_layers": selected_layers,
        "scoring_framework": scoring_framework,
        "assumptions": [
            "Scenario scores are draft review weights, not official decisions.",
            "No parcel scoring is executed unless a separate bounded analysis passes safety checks.",
            "Proxy and reference layers are context only.",
        ],
        "review_questions": _review_questions(scenario_type, scoring_framework),
        "source_coverage": source_coverage,
        "missing_data": missing_data,
        "proxy_warnings": proxy_warnings,
        "confidence_score": classification["confidence_score"],
        "classification_reasons": classification["classification_reasons"],
        "execution_status": EXECUTION_PLAN_ONLY,
        "official_use_disclaimer": OFFICIAL_USE_DISCLAIMER,
        "map_recipe": recipe | {"selected_layers": selected_layers, "source_coverage": source_coverage},
        "created_at": datetime.now(UTC).isoformat(),
        "status": _scenario_status(scenario_type),
    }
    if persist:
        record_scenario(scenario, schema_name=schema_name)
    return scenario


def record_scenario(scenario: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    """Upsert one planning scenario into AutoMap's own database."""
    init_planning_scenario_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {_scenario_table(schema_name)} (
                    scenario_id, raw_prompt, scenario_type, scenario_title,
                    scenario_json, scoring_framework, source_coverage, status
                )
                VALUES (
                    :scenario_id, :raw_prompt, :scenario_type, :scenario_title,
                    CAST(:scenario_json AS jsonb), CAST(:scoring_framework AS jsonb),
                    CAST(:source_coverage AS jsonb), :status
                )
                ON CONFLICT (scenario_id) DO UPDATE SET
                    raw_prompt = EXCLUDED.raw_prompt,
                    scenario_type = EXCLUDED.scenario_type,
                    scenario_title = EXCLUDED.scenario_title,
                    scenario_json = EXCLUDED.scenario_json,
                    scoring_framework = EXCLUDED.scoring_framework,
                    source_coverage = EXCLUDED.source_coverage,
                    status = EXCLUDED.status;
                """
            ),
            {
                "scenario_id": scenario["scenario_id"],
                "raw_prompt": scenario["raw_prompt"],
                "scenario_type": scenario["scenario_type"],
                "scenario_title": scenario["scenario_title"],
                "scenario_json": json.dumps(scenario, default=str),
                "scoring_framework": json.dumps(scenario.get("scoring_framework") or [], default=str),
                "source_coverage": json.dumps(scenario.get("source_coverage") or {}, default=str),
                "status": scenario.get("status") or "draft",
            },
        )
    return scenario


def get_scenario(scenario_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one stored planning scenario."""
    init_planning_scenario_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT scenario_json
                FROM {_scenario_table(schema_name)}
                WHERE scenario_id = :scenario_id;
                """
            ),
            {"scenario_id": scenario_id},
        ).scalar_one_or_none()
    if row is None:
        raise FileNotFoundError(f"Scenario not found: {scenario_id}")
    return dict(row)


def list_scenarios(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List recent planning scenarios."""
    init_planning_scenario_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT scenario_id, raw_prompt, scenario_type, scenario_title,
                       scenario_json, scoring_framework, source_coverage, status, created_at
                FROM {_scenario_table(schema_name)}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            scenario_json = item.get("scenario_json")
            if isinstance(scenario_json, dict):
                item.update(
                    {
                        "confidence_score": scenario_json.get("confidence_score"),
                        "execution_status": scenario_json.get("execution_status"),
                        "missing_data": scenario_json.get("missing_data") or [],
                    }
                )
            results.append(item)
        return results
