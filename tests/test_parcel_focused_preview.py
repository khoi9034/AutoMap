import json

from fastapi.testclient import TestClient

from app.recipe_engine import build_recipe
from app.web_ui import create_app
from app.webmap_builder import build_webmap_json
from app.workflow_runner import run_prompt_workflow


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
        "fields": [{"name": "PIN14", "type": "esriFieldTypeString", "alias": "PIN14"}],
    }


def sample_catalog():
    return [
        catalog_record("tax_parcels", "Tax Parcels", "parcel"),
        catalog_record("zoning", "Cabarrus County Zoning", "zoning"),
        catalog_record("flood_100", "FloodPlain100year", "flood"),
        catalog_record("roads", "Road Centerlines", "transportation"),
    ]


def selected_parcel_geojson(path):
    path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"PIN14": "5528123456"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [[[-80.6, 35.4], [-80.59, 35.4], [-80.59, 35.41], [-80.6, 35.41], [-80.6, 35.4]]],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_unmatched_parcel_request_blocks_focused_preview_and_countywide_extent():
    recipe = build_recipe(
        "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.",
        sample_catalog(),
        persist_data_gaps=False,
    )

    parcel_context = recipe["parcel_context"]
    assert parcel_context["can_focus_map"] is False
    assert parcel_context["can_fetch_geometry"] is False
    assert recipe["preview_status"] == "blocked_until_parcel_matched"
    assert recipe["analysis_execution"]["analysis_status"] == "blocked_until_parcel_matched"
    assert recipe["analysis_execution"]["operation_type"] == "parcel_context_preview_blocked"
    assert recipe["suggested_extent"]["type"] == "blocked_until_parcel_matched"

    webmap = build_webmap_json(recipe)
    assert webmap["initialState"]["viewpoint"]["targetGeometry"] == {}


def test_matched_parcel_mock_adds_buffer_extent_and_selected_layer(monkeypatch, tmp_path):
    geojson_path = tmp_path / "selected_parcels.geojson"
    selected_parcel_geojson(geojson_path)

    monkeypatch.setattr(
        "app.recipe_engine.create_parcel_set",
        lambda raw_input, layer_catalog=None, persist=True: {
            "parcel_set_id": "parcel_set_test",
            "raw_input": raw_input,
            "input_type": "pin",
            "parsed_identifiers": [{"identifier_type": "pin", "value": "5528-12-3456"}],
            "match_status": "matched",
            "matched_count": 1,
            "matched_parcels": [{"pin14": "5528123456", "object_id": 1}],
            "unmatched_identifiers": [],
            "candidate_matches": [],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "app.recipe_engine.fetch_selected_parcels",
        lambda parcel_set_id: {"geometry_output_path": str(geojson_path), "warnings": [], "receipt": {"feature_count": 1}},
    )

    recipe = build_recipe(
        "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.",
        sample_catalog(),
        persist_data_gaps=False,
        match_parcel_context=True,
    )

    parcel_context = recipe["parcel_context"]
    assert parcel_context["can_focus_map"] is True
    assert parcel_context["matched_count"] == 1
    assert parcel_context["parcel_buffer_extent"]["xmin"] < parcel_context["parcel_extent"]["xmin"]
    assert recipe["suggested_extent"] == parcel_context["parcel_buffer_extent"]
    assert recipe["analysis_execution"]["analysis_status"] == "not_needed_for_basic_context_map"
    assert recipe["analysis_execution"]["operation_type"] == "parcel_context_preview"
    assert any(output.get("type") == "selected_parcels_geojson" for output in recipe["analysis_execution"]["derived_outputs"])


def test_workflow_run_returns_corrective_action_for_unmatched_parcel(monkeypatch):
    fake_recipe = {
        "map_title": "Parcel context",
        "selected_layers": [{"layer_key": "tax_parcels", "layer_name": "Tax Parcels", "category": "parcel"}],
        "review_reasons": ["This parcel ID was not matched."],
        "missing_data_needed": [],
        "needs_review": True,
        "parcel_context": {
            "match_status": "needs_review",
            "matched_count": 0,
            "can_focus_map": False,
            "can_fetch_geometry": False,
            "reason_if_not_focusable": "This parcel ID was not matched.",
            "parcel_warnings": ["This parcel ID was not matched."],
        },
        "analysis_execution": {"executable": False},
    }
    monkeypatch.setattr("app.workflow_runner.build_recipe", lambda prompt: fake_recipe)

    response = run_prompt_workflow("Make a map of parcel 5528-12-3456")

    assert response["can_preview"] is False
    assert response["can_analyze"] is False
    assert response["next_recommended_action"] == "correct_parcel_identifier"


def test_workflow_api_has_no_secrets_or_cfs_markers(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.run_prompt_workflow",
        lambda prompt: {
            "workflow_id": "workflow_test",
            "prompt": prompt,
            "recipe": {"map_title": "Safe recipe", "selected_layers": []},
            "can_preview": True,
            "can_analyze": False,
            "can_report": False,
            "next_recommended_action": "create_preview",
            "published": False,
        },
    )
    client = TestClient(create_app())

    response = client.post("/api/workflow/run", json={"prompt": "Show zoning."})

    assert response.status_code == 200
    serialized = json.dumps(response.json()).lower()
    assert "database_url" not in serialized
    assert "password" not in serialized
    assert "cfs_dev" not in serialized
