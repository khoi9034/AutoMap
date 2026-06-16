import json

from app.scenario_builder import build_scenario
from app.scenario_comparison import compare_scenarios
from app.scenario_variant_engine import (
    build_variant_json,
    init_scenario_variant_table,
    normalize_variant_weights,
    validate_variant_safety,
)
from app.scenario_workbench import build_recipe_from_scenario
from tests.test_development_transportation_intelligence import external_catalog


def _commercial_scenario():
    return build_scenario(
        "Map commercial growth opportunities near high traffic roads but avoid floodplain.",
        layer_catalog=external_catalog(),
        persist=False,
    )


def test_scenario_variant_creation_applies_weight_overrides_and_aliases():
    scenario = _commercial_scenario()
    variant = build_variant_json(
        scenario,
        {
            "variant_name": "Road access priority",
            "weight_overrides": {"aadt_high_traffic": 40, "floodplain_avoidance": -30},
        },
    )
    factors = {factor["factor_key"]: factor for factor in variant["factor_weights"]}

    assert variant["variant_name"] == "Road access priority"
    assert factors["high_aadt"]["reviewer_weight"] == 40
    assert factors["flood_constraint"]["reviewer_weight"] == -30
    assert variant["normalized_weights"]
    assert variant["official_use_disclaimer"]


def test_proxy_factors_remain_context_only_by_default():
    scenario = _commercial_scenario()
    variant = build_variant_json(scenario, {"variant_name": "Default review"})
    factors = {factor["factor_key"]: factor for factor in variant["factor_weights"]}

    assert factors["development_proxy"]["factor_type"] == "proxy"
    assert factors["development_proxy"]["reviewer_weight"] == 0
    assert factors["stip_context"]["reviewer_weight"] == 0
    assert any("Proxy" in warning or "proxy" in warning for warning in variant["safety_warnings"])


def test_missing_official_data_is_not_scored_as_present():
    scenario = _commercial_scenario()
    variant = build_variant_json(
        scenario,
        {"weight_overrides": {"missing_current_permits": 15}},
    )
    factors = {factor["factor_key"]: factor for factor in variant["factor_weights"]}

    assert factors["missing_current_permits"]["reviewer_weight"] == 0
    assert any("Missing official" in warning for warning in variant["missing_data_warnings"])
    assert validate_variant_safety(variant)["is_safe"] is True


def test_normalized_weights_are_computed_for_enabled_factors():
    variant = normalize_variant_weights(
        {
            "factor_weights": [
                {"factor_key": "a", "reviewer_weight": 3, "enabled": True},
                {"factor_key": "b", "reviewer_weight": -1, "enabled": True},
                {"factor_key": "c", "reviewer_weight": 10, "enabled": False},
            ]
        }
    )
    weights = {item["factor_key"]: item for item in variant["factor_weights"]}

    assert weights["a"]["normalized_percent"] == 75
    assert weights["b"]["normalized_percent"] == 25
    assert weights["c"]["normalized_percent"] == 0


def test_scenario_comparison_shows_factor_and_layer_differences(monkeypatch):
    scenario = _commercial_scenario()
    variant = build_variant_json(
        scenario,
        {"variant_name": "Road access priority", "weight_overrides": {"high_aadt": 40}},
    )
    monkeypatch.setattr("app.scenario_comparison.get_scenario", lambda scenario_id, schema_name="automap": scenario)
    monkeypatch.setattr("app.scenario_comparison.get_scenario_variant", lambda variant_id, schema_name="automap": variant)

    comparison = compare_scenarios(["scenario_1"], ["variant_1"], persist=False)

    assert comparison["factor_differences"]
    assert comparison["layer_differences"]["common_layers"]
    assert comparison["recommended_review_focus"]


def test_scenario_to_recipe_preserves_source_warnings_and_does_not_publish(monkeypatch):
    scenario = _commercial_scenario()
    variant = build_variant_json(scenario, {"variant_name": "Road access priority", "weight_overrides": {"high_aadt": 40}})
    monkeypatch.setattr("app.scenario_workbench.get_scenario", lambda scenario_id, schema_name="automap": scenario)
    monkeypatch.setattr("app.scenario_workbench.get_scenario_variant", lambda variant_id, schema_name="automap": variant)

    result = build_recipe_from_scenario("scenario_1", "variant_1")
    serialized = json.dumps(result).lower()

    assert result["published"] is False
    assert result["recipe"]["needs_review"] is True
    assert result["recipe"]["scenario_context"]["variant_id"] == "variant_1"
    assert "proxy" in serialized
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "cfs_dev" not in serialized
    assert "database_url" not in serialized


def test_scenario_variant_table_creation_uses_automap_schema(monkeypatch):
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

    monkeypatch.setattr("app.scenario_variant_engine.get_engine", lambda: FakeEngine())

    init_scenario_variant_table()

    joined = "\n".join(statements).lower()
    assert "scenario_variants" in joined
    assert "automap" in joined
    assert "cfs_dev" not in joined
