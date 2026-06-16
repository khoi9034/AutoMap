import json

from fastapi.testclient import TestClient

from app.recipe_engine import build_recipe
from app.web_ui import create_app


def catalog_record(layer_key, layer_name, category, *, fields=None):
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
        "fields": fields or [],
    }


def sample_catalog():
    return [
        catalog_record(
            "parcels",
            "Tax Parcels",
            "parcel",
            fields=[{"name": "PIN14", "type": "esriFieldTypeString", "alias": "Parcel PIN"}],
        ),
        catalog_record(
            "zoning",
            "Cabarrus County Zoning",
            "zoning",
            fields=[{"name": "ZONE_CODE", "type": "esriFieldTypeString", "alias": "Zoning Code"}],
        ),
        catalog_record("flood", "FloodPlain100year", "flood"),
        catalog_record("roads", "Road Centerlines", "transportation"),
    ]


def test_recipe_for_fake_parcel_prompt_returns_metadata_only():
    recipe = build_recipe(
        "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.",
        sample_catalog(),
        persist_data_gaps=False,
    )

    parcel_context = recipe["parcel_context"]
    assert parcel_context["input_type"] == "pin"
    assert parcel_context["parsed_identifiers"][0]["value"] == "5528-12-3456"
    assert parcel_context["matched_count"] is None
    assert parcel_context["parcel_extent"]["type"] == "parcel_workspace_required"
    assert "geometry_output_path" not in json.dumps(recipe).lower()
    assert recipe["needs_review"] is True
    assert recipe["recipe_timing"]["total_ms"] >= 0


def test_recipe_response_includes_timing_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.build_recipe",
        lambda prompt: {
            "map_title": "Parcel context map",
            "user_intent": prompt,
            "selected_layers": [],
            "missing_data_needed": [],
            "recipe_timing": {
                "parse_ms": 1,
                "intelligence_ms": 2,
                "layer_match_ms": 3,
                "field_filter_ms": 4,
                "parcel_context_ms": 5,
                "total_ms": 15,
            },
        },
    )
    monkeypatch.setattr("app.api_routes.data_gap_records_from_recipe", lambda recipe: [])
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    response = client.post(
        "/api/recipe",
        json={"prompt": "Make a map of parcel 5528-12-3456 and show zoning."},
    )

    assert response.status_code == 200
    assert response.json()["recipe"]["recipe_timing"]["total_ms"] == 15
    assert response.json()["recipe_timing"]["field_filter_ms"] == 4


def test_recipe_response_has_no_secret_or_cfs_markers(monkeypatch):
    recipe = build_recipe(
        "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.",
        sample_catalog(),
        persist_data_gaps=False,
    )

    serialized = json.dumps(recipe).lower()
    assert "database_url" not in serialized
    assert "password" not in serialized
    assert "secret" not in serialized
    assert "cfs_dev" not in serialized
