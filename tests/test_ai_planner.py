import pytest
from types import SimpleNamespace
import sys

from app.ai.openai_client import AISettings, request_structured_map_plan
from app.ai.map_plan_validator import MapPlanValidationError, map_plan_to_request_plan, validate_map_plan
from app.ai.map_planner import plan_with_ai
from app.recipe_engine import build_recipe


def catalog_record(layer_key, layer_name, category):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "aliases": [category, layer_name],
        "description": "",
        "planning_use_cases": [category],
        "canonical_topic": category,
        "source_priority": 1,
        "source_status": "active",
        "source_key": "cabarrus_new_opendata",
        "service_name": layer_name,
        "service_url": f"https://example.test/{layer_name}/MapServer",
        "layer_url": f"https://example.test/{layer_name}/MapServer/0",
        "geometry_type": "esriGeometryPolygon",
        "layer_id": 0,
        "is_verified": True,
        "is_group_layer": False,
        "is_feature_layer": True,
        "is_historical": False,
        "record_count": 1,
        "fields": [{"name": "PIN14", "alias": "PIN14"}],
    }


def sample_catalog():
    return [
        catalog_record("tax_parcels", "Tax Parcels", "parcel"),
        catalog_record("flood_100", "FloodPlain100year", "flood"),
        catalog_record("municipal", "Municipal District", "jurisdiction"),
        catalog_record("zoning", "Concord Zoning", "zoning"),
        catalog_record("roads", "Road Centerlines", "transportation"),
    ]


def valid_floodplain_plan():
    return {
        "version": "1",
        "request_type": "floodplain_screening",
        "confidence": 0.91,
        "normalized_prompt": "show parcels in concord that are in the 100-year floodplain",
        "cabarrus_scope_check": "in_scope",
        "user_intent_summary": "Floodplain parcel screening in Concord",
        "geography": {"name": "Concord", "type": "municipality"},
        "aoi": {"type": "municipality", "name": "Concord", "buffer_distance": "none"},
        "output_mode": "map",
        "target_layers": [
            {
                "domain": "parcels",
                "role": "primary_result",
                "required": True,
                "preferred_source_hint": "tax parcels",
                "filter_intent": "",
                "geometry_type_expected": "polygon",
                "fallback_if_missing": "partial context map",
            }
        ],
        "context_layers": [
            {
                "domain": "floodplain",
                "role": "supporting_context",
                "required": True,
                "preferred_source_hint": "100-year floodplain",
                "filter_intent": "100-year",
                "geometry_type_expected": "polygon",
                "fallback_if_missing": "partial context map",
            },
            {
                "domain": "boundaries",
                "role": "boundary_context",
                "required": True,
                "preferred_source_hint": "municipal boundary",
                "filter_intent": "Concord",
                "geometry_type_expected": "polygon",
                "fallback_if_missing": "use AOI extent",
            },
        ],
        "spatial_operations": ["intersect", "clip_to_aoi"],
        "filters": [{"domain": "floodplain", "field_role": "flood_type", "operator": "equals", "value": "100_year", "confidence": 0.9}],
        "result_expectation": "Parcels intersecting the 100-year floodplain",
        "cartography_roles": ["primary_result", "supporting_context", "boundary_context"],
        "legend_expectation": ["Parcels in 100-year floodplain", "100-year floodplain", "Concord boundary"],
        "fallback_strategy": "Show partial context only if parcel intersection fails.",
        "clarifying_question": None,
        "safety_notes": ["No owner/name fields.", "No real publish."],
    }


def test_ai_disabled_uses_deterministic(monkeypatch):
    monkeypatch.setenv("AUTOMAP_AI_ENABLED", "false")

    result = plan_with_ai("commercial zoning around Concord")

    assert result["planner_used"] == "deterministic"
    assert result["ai_status"] == "disabled"
    assert result["request_plan"] is None


def test_missing_openai_key_does_not_crash(monkeypatch):
    monkeypatch.setenv("AUTOMAP_AI_ENABLED", "true")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = plan_with_ai("commercial zoning around Concord")

    assert result["planner_used"] == "fallback"
    assert result["ai_status"] == "unavailable"
    assert result["ai_error_category"] == "missing_api_key"


def test_map_plan_validation_accepts_valid_floodplain_plan():
    plan = validate_map_plan(valid_floodplain_plan())
    request_plan = map_plan_to_request_plan(plan)

    assert request_plan["request_type"] == "floodplain_screening"
    assert request_plan["primary_domain"] == "parcels"
    assert "floodplain" in request_plan["secondary_domains"]
    assert request_plan["result_layer"] == "affected_parcels"


def test_map_plan_validator_rejects_raw_urls_owner_fields_sql_and_scope():
    for key, value in [
        ("preferred_source_hint", "https://evil.example/layer"),
        ("filter_intent", "owner name contains Smith"),
        ("filter_intent", "select * from parcels"),
    ]:
        plan = valid_floodplain_plan()
        plan["target_layers"][0][key] = value
        with pytest.raises(MapPlanValidationError):
            validate_map_plan(plan)

    plan = valid_floodplain_plan()
    plan["geography"] = {"name": "Charlotte", "type": "city"}
    with pytest.raises(MapPlanValidationError):
        validate_map_plan(plan)


def test_invalid_ai_plan_falls_back(monkeypatch):
    monkeypatch.setenv("AUTOMAP_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.ai.map_planner.request_structured_map_plan",
        lambda messages, settings: {"ai_status": "ok", "plan": {"request_type": "bogus"}},
    )

    result = plan_with_ai("commercial zoning around Concord")

    assert result["planner_used"] == "fallback"
    assert result["ai_status"] == "invalid"


def test_mock_ai_floodplain_plan_executes_through_deterministic_recipe(monkeypatch):
    monkeypatch.setenv("AUTOMAP_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.ai.map_planner.request_structured_map_plan",
        lambda messages, settings: {"ai_status": "ok", "plan": valid_floodplain_plan()},
    )

    planner = plan_with_ai("show parcels in Concord that are in the 100-year floodplain", sample_catalog())
    recipe = build_recipe(
        "show parcels in Concord that are in the 100-year floodplain",
        sample_catalog(),
        persist_data_gaps=False,
        request_plan_override=planner["request_plan"],
    )

    assert planner["planner_used"] == "ai"
    assert recipe["request_plan"]["ai_validated"] is True
    assert recipe["request_type"] == "floodplain_screening"
    assert any(layer["category"] == "flood" for layer in recipe["selected_layers"])


def test_mock_ai_timeout_falls_back(monkeypatch):
    monkeypatch.setenv("AUTOMAP_AI_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        "app.ai.map_planner.request_structured_map_plan",
        lambda messages, settings: {"ai_status": "unavailable", "error_category": "timeout"},
    )

    result = plan_with_ai("commercial zoning around Concord")

    assert result["planner_used"] == "fallback"
    assert result["ai_error_category"] == "timeout"


def test_openai_bad_request_returns_safe_details(monkeypatch):
    class FakeBadRequest(Exception):
        status_code = 400
        body = {"error": {"type": "invalid_request_error", "code": "invalid_json_schema", "message": "Invalid schema for response format."}}

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: object()))
    monkeypatch.setattr("app.ai.openai_client._create_response", lambda client, model, messages: (_ for _ in ()).throw(FakeBadRequest()))

    result = request_structured_map_plan(
        [{"role": "user", "content": "commercial zoning around Concord"}],
        AISettings(True, "openai", "gpt-5.5", None, 20, 0, "structured_map_plan", True, True),
    )

    assert result["ai_status"] == "unavailable"
    assert result["error_status_code"] == 400
    assert result["error_type"] == "invalid_request_error"
    assert result["error_code"] == "invalid_json_schema"
    assert "Invalid schema" in result["error_message_safe"]
    assert "sk-" not in result["error_message_safe"]


def test_openai_model_error_uses_configured_fallback(monkeypatch):
    calls = []

    class FakeModelError(Exception):
        status_code = 400
        body = {"error": {"type": "invalid_request_error", "code": "model_not_found", "message": "The model does not exist or you do not have access."}}

    class FakeResponse:
        output_text = None

        def model_dump_json(self):
            return "{}"

    def fake_create(client, model, messages):
        calls.append(model)
        if model == "gpt-5.5":
            raise FakeModelError()
        return FakeResponse()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda **kwargs: object()))
    monkeypatch.setattr("app.ai.openai_client._create_response", fake_create)

    result = request_structured_map_plan(
        [{"role": "user", "content": "commercial zoning around Concord"}],
        AISettings(True, "openai", "gpt-5.5", "gpt-5.4-mini", 20, 0, "structured_map_plan", True, True),
    )

    assert result["ai_status"] == "ok"
    assert result["model_used"] == "gpt-5.4-mini"
    assert calls == ["gpt-5.5", "gpt-5.4-mini"]
