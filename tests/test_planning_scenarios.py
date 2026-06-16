import json

from app.request_intelligence import build_request_intelligence
from app.scenario_builder import build_scenario, init_planning_scenario_table
from app.scenario_classifier import classify_scenario
from app.scenario_models import SCENARIO_REPORT_REQUIRED_FILES
from app.scenario_reporter import generate_scenario_report
from tests.test_development_transportation_intelligence import external_catalog


def keys_for(scenario, category):
    return {layer["layer_key"] for layer in scenario["selected_layers"] if layer.get("category") == category}


def coverage_keys(scenario, group):
    return {item.get("layer_key") or item.get("gap_key") for item in scenario["source_coverage"].get(group, [])}


def test_scenario_classifier_detects_core_scenario_types():
    assert classify_scenario("Map commercial growth opportunities near high traffic roads.")["scenario_type"] == "commercial_growth_suitability"
    assert classify_scenario("Find areas suitable for residential growth but avoid flood risk.")["scenario_type"] == "residential_growth_suitability"
    assert classify_scenario("Show development pressure near schools.")["scenario_type"] == "development_pressure"


def test_commercial_growth_scenario_selects_transportation_flood_and_proxy_layers():
    scenario = build_scenario(
        "Map commercial growth opportunities near high traffic roads but avoid floodplain.",
        layer_catalog=external_catalog(),
        persist=False,
    )

    assert scenario["scenario_type"] == "commercial_growth_suitability"
    assert "aadt" in keys_for(scenario, "transportation")
    assert "stip" in keys_for(scenario, "transportation_projects")
    assert "flood100" in keys_for(scenario, "flood")
    assert "accela" in keys_for(scenario, "development_activity_proxy")
    assert "permits" in scenario["missing_data"]
    assert "accela" in coverage_keys(scenario, "proxy_sources")
    assert "aadt" in coverage_keys(scenario, "reference_sources")
    assert "current_permits" in coverage_keys(scenario, "missing_official_sources")
    assert scenario["execution_status"] == "scoring_plan_only"
    assert "official planning recommendation" in scenario["official_use_disclaimer"]


def test_scenario_scoring_framework_has_weights_and_review_flags():
    scenario = build_scenario(
        "Map commercial growth opportunities near high traffic roads but avoid floodplain.",
        layer_catalog=external_catalog(),
        persist=False,
    )
    factors = {factor["factor_key"]: factor for factor in scenario["scoring_framework"]}

    assert factors["commercial_zoning"]["suggested_weight"] > 0
    assert factors["high_aadt"]["direction"] == "higher_is_better"
    assert factors["flood_constraint"]["suggested_weight"] < 0
    assert factors["development_proxy"]["factor_type"] == "proxy"
    assert any(factor["needs_review"] for factor in scenario["scoring_framework"])
    assert any("AADT threshold" in question for question in scenario["review_questions"])


def test_development_pressure_scenario_keeps_proxy_and_missing_official_warnings():
    scenario = build_scenario(
        "Show development pressure near schools and flood zones in Concord.",
        layer_catalog=external_catalog(),
        persist=False,
    )

    assert scenario["scenario_type"] == "development_pressure"
    assert "accela" in keys_for(scenario, "development_activity_proxy")
    assert "current_permits" in coverage_keys(scenario, "missing_official_sources")
    assert any("proxy/context source only" in warning for warning in scenario["source_coverage"]["warnings"])


def test_residential_growth_scenario_includes_flood_and_school_context():
    scenario = build_scenario(
        "Find areas suitable for residential growth but avoid flood risk.",
        layer_catalog=external_catalog(),
        persist=False,
    )

    assert scenario["scenario_type"] == "residential_growth_suitability"
    assert keys_for(scenario, "flood")
    assert keys_for(scenario, "schools")
    assert "permits" in scenario["missing_data"]


def test_request_intelligence_recommends_scenario_workflow():
    intelligence = build_request_intelligence("Map commercial growth opportunities near high traffic roads but avoid floodplain.")
    scenario_context = intelligence["request_intelligence"]["scenario_context"]

    assert scenario_context["scenario_detected"] is True
    assert scenario_context["scenario_type"] == "commercial_growth_suitability"
    assert "Scenarios page" in scenario_context["recommended_scenario_workflow"]


def test_planning_scenario_table_creation_uses_automap_schema(monkeypatch):
    statements = []

    class FakeConnection:
        def execute(self, statement, params=None):
            statements.append(str(statement))

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr("app.scenario_builder.get_engine", lambda: FakeEngine())

    init_planning_scenario_table()

    joined = "\n".join(statements).lower()
    assert "planning_scenarios" in joined
    assert "automap" in joined
    assert "cfs_dev" not in joined


def test_scenario_report_writes_required_files_without_protected_database_reference(monkeypatch):
    scenario = build_scenario(
        "Map commercial growth opportunities near high traffic roads but avoid floodplain.",
        layer_catalog=external_catalog(),
        persist=False,
    )
    monkeypatch.setattr("app.scenario_reporter.get_scenario", lambda scenario_id, schema_name="automap": scenario)

    report = generate_scenario_report("scenario_test")
    report_folder = report["report_folder"]
    serialized = json.dumps(report).lower()

    assert {file["name"] for file in report["files"]} == SCENARIO_REPORT_REQUIRED_FILES
    assert report["validation"]["is_valid"] is True
    assert "scenario_reports" in report_folder
    assert "cfs_dev" not in serialized
    assert "database_url" not in serialized
