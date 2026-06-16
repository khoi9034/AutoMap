import json

import pytest

from app import data_gap_resolver as resolver
from app import external_source_registry as registry
from app.source_candidate_evaluator import (
    classify_source_limitations,
    recommend_catalog_category,
    score_source_for_gap,
)
from app.layer_matcher import match_layers
from app.prompt_parser import parse_prompt


def source_record(**overrides):
    record = {
        "source_key": "cabarrus_accela_plan_review_proxy",
        "source_name": "Cabarrus Plan Review Proxy",
        "source_type": "external_reference",
        "base_url": None,
        "layer_url": None,
        "priority": 20,
        "approval_status": "candidate",
        "source_status": "proxy",
        "categories": ["plan_review", "development_pipeline_proxy"],
        "intended_gaps": ["current_development_pipeline", "current_permits"],
        "notes": "Candidate proxy for development pipeline signal.",
        "limitations": "Proxy/context only; not official development approval.",
        "inspected_metadata": {},
        "is_active": True,
    }
    record.update(overrides)
    return record


def catalog_record(**overrides):
    record = {
        "layer_key": "approved_current_development",
        "layer_name": "Current Permits and Planning Cases",
        "category": "development",
        "aliases": ["permits", "planning cases", "development", "current permits"],
        "description": "Current permit and planning case activity.",
        "planning_use_cases": ["permits", "planning cases", "development pipeline"],
        "canonical_topic": "development",
        "source_priority": 1,
        "source_status": "active",
        "approval_status": "approved",
        "source_key": "external_current_development",
        "service_name": "Current Permits",
        "service_url": "https://example.com/CurrentPermits/MapServer",
        "layer_url": "https://example.com/CurrentPermits/MapServer/0",
        "geometry_type": "esriGeometryPoint",
        "layer_id": 0,
        "is_verified": True,
        "is_group_layer": False,
        "is_feature_layer": True,
        "is_historical": False,
        "record_count": 10,
    }
    record.update(overrides)
    return record


def test_external_source_record_validation_allows_review_reference_placeholders():
    normalized = registry.validate_external_source_record(
        source_record(source_key="cabarrus_current_permits_candidate", approval_status="needs_review")
    )

    assert normalized["source_type"] == "external_reference"
    assert normalized["approval_status"] == "needs_review"
    assert normalized["base_url"] is None


def test_external_source_record_validation_rejects_bad_statuses():
    with pytest.raises(ValueError):
        registry.validate_external_source_record(source_record(source_type="spreadsheet_upload"))


def test_reference_source_inspection_is_metadata_only():
    inspected = registry.inspect_external_source(source_record())

    assert inspected["inspected_metadata"]["inspection_status"] == "reference_only"
    assert inspected["inspected_metadata"]["downloaded_geometry"] is False
    assert inspected["inspected_metadata"]["is_verified"] is False


def test_gap_maps_to_ranked_candidate_sources(monkeypatch):
    monkeypatch.setattr(
        resolver,
        "list_external_sources",
        lambda schema_name="automap": [
            source_record(),
            source_record(
                source_key="ncdot_aadt_reference",
                source_name="NCDOT AADT Reference",
                categories=["aadt", "traffic", "transportation"],
                intended_gaps=["traffic_counts"],
                source_status="reference",
            ),
        ],
    )

    candidates = resolver.map_gap_to_candidate_sources("current_development_pipeline")

    assert candidates[0]["source_key"] == "cabarrus_accela_plan_review_proxy"
    assert candidates[0]["source_score"] > 0
    assert "Proxy/context only" in " ".join(candidates[0]["classified_limitations"])


def test_proxy_source_does_not_resolve_official_permit_gap(monkeypatch):
    monkeypatch.setattr(resolver, "list_external_sources", lambda schema_name="automap": [source_record()])

    evaluation = resolver.evaluate_gap_resolution("current_permits")

    assert evaluation["status"] == "needs_review"
    assert evaluation["authoritative_sources"] == []
    assert evaluation["proxy_sources"][0]["source_key"] == "cabarrus_accela_plan_review_proxy"


def test_concord_only_planning_case_source_records_coverage_limitation():
    limitations = classify_source_limitations(
        source_record(
            source_key="concord_planning_cases_limited_candidate",
            source_name="Concord Planning Cases Limited Candidate",
            categories=["planning", "rezoning"],
            intended_gaps=["current_planning_cases"],
            source_status="active",
            limitations="Coverage limited to Concord only.",
        )
    )

    assert "Coverage may be limited to Concord." in limitations


def test_aadt_and_stip_sources_categorize_as_transportation():
    assert recommend_catalog_category(source_record(categories=["aadt", "traffic"])) == "transportation"
    assert recommend_catalog_category(source_record(categories=["stip", "planned_projects"])) == "transportation_projects"


def test_gap_resolution_log_inserts_without_protected_database_references(monkeypatch):
    statements = []
    params_seen = []

    class FakeConnection:
        def execute(self, statement, params=None):
            statements.append(str(statement))
            params_seen.append(params or {})

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(resolver, "init_external_source_tables", lambda schema_name="automap": None)
    monkeypatch.setattr(resolver, "get_engine", lambda: FakeEngine())

    result = resolver.log_gap_resolution(
        "current_permits",
        "cabarrus_current_permits_candidate",
        "needs_review",
        "Candidate requires review.",
        42.0,
        {"inspection_status": "reference_only"},
    )

    serialized = json.dumps({"statements": statements, "params": params_seen, "result": result}).lower()
    assert "data_gap_resolution_log" in "\n".join(statements)
    assert result["resolution_status"] == "needs_review"
    assert "cfs_dev" not in serialized
    assert "database_url" not in serialized


def test_recipe_uses_verified_approved_gap_source_when_available():
    result = match_layers(
        parse_prompt("Map recent permits and planning cases near Kannapolis."),
        [catalog_record()],
    )

    selected_keys = {layer["layer_key"] for layer in result["selected_layers"]}
    assert "approved_current_development" in selected_keys
    assert "permits" not in result["missing_data_needed"]
    assert "planning cases" not in result["missing_data_needed"]


def test_recipe_keeps_missing_data_when_source_is_candidate_or_proxy():
    result = match_layers(
        parse_prompt("Map recent permits and planning cases near Kannapolis."),
        [
            catalog_record(
                layer_key="candidate_plan_review_proxy",
                source_status="proxy",
                approval_status="candidate",
                source_key="cabarrus_accela_plan_review_proxy",
            )
        ],
    )

    assert "permits" in result["missing_data_needed"]
    assert "planning cases" in result["missing_data_needed"]


def test_source_scoring_does_not_treat_candidate_proxy_as_authoritative():
    candidate_score = score_source_for_gap(source_record(), "current_permits")
    approved_score = score_source_for_gap(
        source_record(approval_status="approved", source_status="active", inspected_metadata={"is_verified": True}),
        "current_permits",
    )

    assert approved_score > candidate_score
