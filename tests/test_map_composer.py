import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.map_composer import apply_composer_adjustments, generate_composer_draft
from app.recipe_engine import build_recipe
from app.web_ui import create_app


def catalog_record(layer_key, layer_name, category, role="base_layer"):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "role": role,
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
        catalog_record("flood_100", "FloodPlain100year", "flood", role="constraint_overlay"),
        catalog_record("roads", "Road Centerlines", "transportation", role="transportation_layer"),
        catalog_record("municipal", "Municipal District", "jurisdiction", role="jurisdiction_filter"),
    ]


def selected_parcel_geojson(path: Path) -> None:
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


def test_composer_unmatched_parcel_blocks_preview_without_countywide_extent(monkeypatch, tmp_path):
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )

    result = generate_composer_draft(
        "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads."
    )

    assert result["can_preview"] is False
    assert result["next_action"] == "correct_parcel_identifier"
    assert result["review_packet_id"] is None
    assert result["preview_config"] is None
    assert result["parcel_context"]["can_focus_map"] is False
    assert result["recipe"]["suggested_extent"]["type"] == "blocked_until_parcel_matched"
    assert result["webmap_json"]["initialState"]["viewpoint"]["targetGeometry"] == {}
    assert "parcel" in result["preview_blockers"][0].lower()


def test_composer_matched_parcel_adds_selected_layer_on_top(monkeypatch, tmp_path):
    geojson_path = tmp_path / "selected_parcels.geojson"
    selected_parcel_geojson(geojson_path)

    def fake_recipe(prompt):
        recipe = build_recipe(prompt, sample_catalog(), persist_data_gaps=False)
        recipe["parcel_context"] = {
            "parcel_set_id": "parcel_set_test",
            "match_status": "matched",
            "matched_count": 1,
            "unmatched_identifiers": [],
            "candidate_matches": [],
            "can_focus_map": True,
            "can_fetch_geometry": True,
            "preview_status": "ready",
            "analysis_status": "not_needed_for_basic_context_map",
            "focus_mode": "parcel",
            "parcel_extent": {"xmin": -80.6, "ymin": 35.4, "xmax": -80.59, "ymax": 35.41, "spatialReference": {"wkid": 4326}},
            "parcel_buffer_extent": {"xmin": -80.61, "ymin": 35.39, "xmax": -80.58, "ymax": 35.42, "spatialReference": {"wkid": 4326}},
            "selected_parcel_geojson_path": str(geojson_path),
            "parcel_warnings": [],
        }
        recipe["suggested_extent"] = recipe["parcel_context"]["parcel_buffer_extent"]
        recipe["analysis_execution"] = {
            "executable": False,
            "analysis_status": "not_needed_for_basic_context_map",
            "operation_type": "parcel_context_preview",
            "derived_outputs": [
                {
                    "type": "selected_parcels_geojson",
                    "path": str(geojson_path),
                    "title": "Selected Parcel",
                    "layer_key": "derived_selected_parcel_test",
                }
            ],
        }
        return recipe

    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr("app.map_composer.build_recipe", fake_recipe)
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})

    result = generate_composer_draft(
        "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads."
    )

    assert result["can_preview"] is True
    assert result["parcel_context"]["can_focus_map"] is True
    assert result["webmap_json"]["initialState"]["viewpoint"]["targetGeometry"]["xmin"] == -80.61
    assert result["webmap_json"]["operationalLayers"][-1]["title"] == "Selected Parcel"
    assert result["webmap_json"]["operationalLayers"][-1]["autoMapDisplayRole"] == "selected_result"


def test_geography_prompt_uses_focused_review_extent(monkeypatch, tmp_path):
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})

    result = generate_composer_draft("Show parcels in Concord that are in the 100-year floodplain.")

    extent = result["webmap_json"]["initialState"]["viewpoint"]["targetGeometry"]
    assert result["can_preview"] is True
    assert extent["xmin"] == -80.72
    assert extent["xmax"] == -80.46


def test_composer_adjust_changes_title_visibility_opacity_and_order(monkeypatch, tmp_path):
    session_root = tmp_path / "composer_sessions"
    packet_path = tmp_path / "review_packets" / "packet"
    adjusted_path = tmp_path / "adjusted" / "packet_adjusted"
    packet_path.mkdir(parents=True)
    adjusted_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: session_root)
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer.write_adjusted_packet", lambda packet, recipe, webmap, adjustments: adjusted_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})

    result = generate_composer_draft("Show parcels in Concord that are in the 100-year floodplain.")
    adjusted = apply_composer_adjustments(
        result["composer_session_id"],
        {
            "map_title": "Concord Flood Draft",
            "layers": [
                {"layer_key": "flood_100", "title": "100-Year Floodplain", "visibility": True, "opacity": 0.45},
                {"layer_key": "tax_parcels", "title": "Tax Parcels", "visibility": False, "opacity": 0.2},
            ],
        },
    )

    assert adjusted["map_title"] == "Concord Flood Draft"
    assert adjusted["webmap_json"]["title"] == "Concord Flood Draft"
    first_layer = adjusted["webmap_json"]["operationalLayers"][0]
    assert first_layer["autoMapLayerKey"] == "flood_100"
    assert first_layer["title"] == "100-Year Floodplain"
    assert first_layer["opacity"] == 0.45
    assert adjusted["adjusted_packet_id"] == "packet_adjusted"


def test_composer_api_has_no_secrets_or_cfs_markers(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.generate_composer_draft",
        lambda prompt: {
            "composer_session_id": "composer_test",
            "raw_prompt": prompt,
            "map_title": "Safe draft",
            "recipe": {"map_title": "Safe draft", "selected_layers": []},
            "webmap_json": {"operationalLayers": []},
            "selected_layers": [],
            "warnings": [],
            "missing_data": [],
            "can_preview": False,
            "can_analyze": False,
            "preview_blockers": ["Parcel not matched."],
            "next_action": "correct_parcel_identifier",
            "published": False,
        },
    )
    client = TestClient(create_app())

    response = client.post("/api/composer/generate", json={"prompt": "Make a parcel map."})

    assert response.status_code == 200
    serialized = json.dumps(response.json()).lower()
    assert "database_url" not in serialized
    assert "password" not in serialized
    assert "cfs_dev" not in serialized
