import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.map_composer import apply_composer_adjustments, export_composer_session, generate_composer_draft
from app.print_options_models import export_manifest_metadata, normalize_print_options
from app.report_statistics_builder import build_report_statistics
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


def test_composer_table_prompt_hands_off_to_table_center(monkeypatch, tmp_path):
    table_recipe = {
        "table_request_id": "table_test",
        "table_title": "Parcel Table",
        "raw_prompt": "Give me a table of parcels in Concord.",
        "table_intent": "parcel_table",
        "source_layers": [{"layer_key": "tax_parcels", "layer_name": "Tax Parcels", "returnGeometry": False}],
        "selected_fields": [{"layer_key": "tax_parcels", "name": "PIN14", "alias": "PIN14"}],
        "estimated_count": 12,
        "export_ready": True,
        "safety_status": "export_ready",
        "missing_data_needed": [],
        "warnings": [],
        "query_options": {"returnGeometry": False},
    }
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr("app.map_composer.plan_table_query", lambda prompt: table_recipe)
    monkeypatch.setattr(
        "app.map_composer.preview_table_rows",
        lambda recipe: {"preview_rows": [{"PIN14": "preview_1"}], "returnGeometry": False},
    )

    result = generate_composer_draft("Give me a table of parcels in Concord.")

    assert result["request_type"] == "table_request"
    assert result["can_preview"] is False
    assert result["next_action"] == "open_table_center"
    assert result["table_context"]["table_recipe"]["query_options"]["returnGeometry"] is False
    assert result["table_context"]["preview_status"] == "table_preview_live"
    assert result["table_context"]["export_status"] == "export_ready"
    assert result["table_context"]["preview_rows"] == [{"PIN14": "preview_1"}]
    assert result["preview_blockers"] == []
    assert result["webmap_json"] is None


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
    assert result["can_analyze"] is False
    assert result["next_action"] == "correct_parcel_identifier"
    assert result["review_packet_id"] is None
    assert result["preview_config"] is None
    assert result["parcel_context"]["can_focus_map"] is False
    assert result["recipe"]["suggested_extent"]["type"] == "blocked_until_parcel_matched"
    assert result["webmap_json"]["initialState"]["viewpoint"]["targetGeometry"] == {}
    assert "parcel" in result["preview_blockers"][0].lower()


def test_composer_address_proximity_unmatched_says_address_not_parcel(monkeypatch, tmp_path):
    prompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr(
        "app.map_composer.run_proximity_request",
        lambda prompt, **kwargs: {
            "status": "needs_review",
            "raw_prompt": prompt,
            "origin_input": "793 bartram ave",
            "origin_type": "address",
            "target_type": "nearest_fire_station",
            "candidate_matches": [],
            "warnings": [
                "Address not found in Cabarrus County records. AutoMap's live address lookup currently supports Cabarrus County, NC only. Try a Cabarrus County address, parcel/PIN, or planning request."
            ],
            "published": False,
        },
    )

    result = generate_composer_draft(prompt)

    assert result["request_type"] == "proximity"
    assert result["origin_type"] == "address"
    assert result["origin_match_status"] == "needs_review"
    assert result["can_preview"] is False
    assert result["next_action"] == "correct_address"
    assert "Address not found" in result["preview_blockers"][0]
    assert "Parcel not matched" not in result["preview_blockers"][0]
    assert result["review_packet_id"] is None


def test_composer_address_proximity_matched_adds_line_output(monkeypatch, tmp_path):
    prompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"
    line_path = tmp_path / "proximity_line.geojson"
    line_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"label": "Straight-line distance"},
                        "geometry": {"type": "LineString", "coordinates": [[-80.6, 35.4], [-80.58, 35.42]]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})
    monkeypatch.setattr(
        "app.map_composer.run_proximity_request",
        lambda prompt, **kwargs: {
            "status": "ok",
            "raw_prompt": prompt,
            "origin_input": "793 bartram ave",
            "origin_type": "address",
            "target_type": "nearest_fire_station",
            "target_name": "Fire Station 1",
            "distance_value": 1.25,
            "distance_unit": "miles",
            "route_mode": "straight_line_fallback",
            "route_label": "Straight-line fallback",
            "route_warning": "Road route unavailable; showing straight-line reference only.",
            "line_geojson_path": str(line_path),
            "proximity_result_id": "prox_result_test",
            "target_layer": {
                "layer_key": "fire_stations",
                "layer_name": "Fire and EMS Stations",
                "category": "public_facilities",
                "layer_url": "https://example.test/Fire/0",
            },
            "derived_layer": {"layer_key": "derived_proximity_line_test"},
            "warnings": [],
            "published": False,
        },
    )

    result = generate_composer_draft(prompt)

    assert result["can_preview"] is True
    assert result["request_type"] == "proximity"
    assert result["origin_type"] == "address"
    assert result["map_title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert result["proximity_result"]["target_type"] == "nearest_fire_station"
    assert result["webmap_json"]["operationalLayers"][-1]["title"] == "Straight-line fallback"
    assert result["map_layout"]["title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert result["map_layout"]["subtitle"] == "Straight-line fallback. Road route unavailable."
    assert result["map_layout"]["scale_bar_enabled"] is True
    assert result["map_layout"]["scale_bar_position"] == "bottom_center"
    assert result["map_layout"]["scale_bar_width_percent"] == 64
    assert result["map_layout"]["scale_bar_style"] == "centered_enterprise"
    assert result["map_layout"]["north_arrow_enabled"] is True
    assert "not official" in result["map_layout"]["disclaimer"].lower()
    assert result["review_packet_id"] == "packet"
    assert result["composer_map_state"]["map_title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert result["composer_map_state"]["preview_config"]["map_layout"]["title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert result["composer_map_state"]["basemap"] == "streets-vector"
    assert result["composer_map_state"]["scale_bar_config"]["width_percent"] == 64
    assert result["composer_map_state"]["north_arrow_config"]["enabled"] is True
    assert result["report_statistics"]["proximity"]["distance"]["value"] == 1.25


def test_composer_address_proximity_attempts_initial_route_mode(monkeypatch, tmp_path):
    prompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"
    captured_kwargs = {}
    line_path = tmp_path / "proximity_line.geojson"
    line_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"label": "Straight-line distance"},
                        "geometry": {"type": "LineString", "coordinates": [[-80.6, 35.4], [-80.58, 35.42]]},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})

    def fake_proximity(prompt, **kwargs):
        captured_kwargs.update(kwargs)
        return {
            "status": "ok",
            "raw_prompt": prompt,
            "origin_input": "793 bartram ave",
            "origin_type": "address",
            "property_match_status": "not_resolved",
            "target_type": "nearest_fire_station",
            "target_name": "Fire Station 1",
            "distance_value": 1.25,
            "distance_unit": "miles",
            "line_geojson_path": str(line_path),
            "proximity_result_id": "prox_result_test",
            "target_layer": {
                "layer_key": "fire_stations",
                "layer_name": "Fire and EMS Stations",
                "category": "public_facilities",
                "layer_url": "https://example.test/Fire/0",
            },
            "derived_layer": {"layer_key": "derived_proximity_line_test"},
            "route_mode": "straight_line_fallback",
            "route_refinement_available": True,
            "route_refinement_status": "available",
            "proximity_timing": {
                "address_match_ms": 12,
                "parcel_resolve_ms": 0,
                "nearest_facility_ms": 34,
                "route_generation_ms": 0,
                "geojson_write_ms": 7,
            },
            "warnings": ["Road-following route can be refined separately."],
            "published": False,
        }

    monkeypatch.setattr("app.map_composer.run_proximity_request", fake_proximity)

    result = generate_composer_draft(prompt)

    assert captured_kwargs["allow_route_draft"] is True
    assert captured_kwargs["resolve_property"] is False
    assert result["can_preview"] is True
    assert result["proximity_result"]["route_refinement_available"] is True
    assert result["route_refinement_available"] is True
    assert result["composer_timing"]["address_match_ms"] == 12
    assert result["composer_timing"]["geojson_write_ms"] == 7
    assert "composer_timing" in result["debug_details"]


def test_composer_proximity_preview_config_includes_derived_overlays(monkeypatch, tmp_path):
    prompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr(
        "app.map_composer._preview_config_for",
        lambda path, can_preview: {
            "operational_layers": [
                {"layer_key": "addresses", "title": "Addresses", "role": "reference_layer", "url": "https://example.test/Addresses/0"},
                {"layer_key": "tax_parcels", "title": "Tax Parcels", "role": "base_layer", "url": "https://example.test/Parcels/0"},
                {"layer_key": "fire_stations", "title": "Fire and EMS Stations", "role": "nearest_facility_target", "url": "https://example.test/Fire/0"},
            ]
        },
    )
    monkeypatch.setattr(
        "app.map_composer.run_proximity_request",
        lambda prompt, **kwargs: {
            "status": "ok",
            "raw_prompt": prompt,
            "origin_input": "793 bartram ave",
            "origin_type": "address",
            "property_match_status": "not_resolved",
            "target_type": "nearest_fire_station",
            "target_name": "Fire Station 1",
            "distance_value": 1.11,
            "distance_unit": "miles",
            "route_mode": "straight_line_fallback",
            "route_label": "Straight-line fallback",
            "route_warning": "Road route unavailable; showing straight-line reference only.",
            "line_geojson_path": "outputs/proximity/test/proximity_line.geojson",
            "line_geojson_url": "/api/local-outputs/geojson/proximity/line-id",
            "proximity_result_id": "prox_result_test",
            "target_layer": {
                "layer_key": "fire_stations",
                "layer_name": "Fire and EMS Stations",
                "category": "public_facilities",
                "layer_url": "https://example.test/Fire/0",
            },
            "derived_layer": {"layer_key": "derived_proximity_line_test"},
            "derived_overlays": [
                {"id": "origin_address_point", "title": "Origin Address", "role": "origin", "symbol_key": "origin_home", "url": "/api/local-outputs/geojson/proximity/origin-id"},
                {"id": "nearest_fire_station", "title": "Nearest Fire Station", "role": "target", "symbol_key": "target_fire_station", "url": "/api/local-outputs/geojson/proximity/target-id"},
                {"id": "straight_line_fallback", "title": "Straight-line fallback", "role": "distance_line", "symbol_key": "route_straight_line", "route_mode": "straight_line_fallback", "url": "/api/local-outputs/geojson/proximity/line-id"},
            ],
            "warnings": [],
            "published": False,
        },
    )

    result = generate_composer_draft(prompt)

    assert result["can_preview"] is True
    assert result["map_title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert result["preview_config"]["basemap"] == "streets-vector"
    assert result["preview_config"]["map_layout"]["title"] == "Nearest Fire Station from 793 Bartram Ave"
    assert result["preview_config"]["map_layout"]["subtitle"] == "Straight-line fallback. Road route unavailable."
    assert result["preview_config"]["map_layout"]["legend_items"]
    assert result["preview_config"]["map_layout"]["print_ready"] is True
    assert "context_layers" in result["preview_config"]
    assert result["preview_config"]["derived_overlays"][0]["id"] == "origin_address_point"
    assert result["preview_config"]["derived_overlays"][2]["id"] == "straight_line_fallback"
    assert result["preview_config"]["derived_overlays"][0]["symbol_key"] == "origin_home"
    assert result["preview_config"]["derived_overlays"][1]["symbol_key"] == "target_fire_station"
    assert result["preview_config"]["derived_overlays"][2]["symbol_key"] == "route_straight_line"
    assert all(layer["default_visible"] is False for layer in result["preview_config"]["context_layers"])
    assert result["preview_config"]["origin_summary"]["origin_type"] == "address"
    assert result["preview_config"]["target_summary"]["target_type"] == "nearest_fire_station"
    assert result["preview_config"]["distance_summary"]["distance_value"] == 1.11
    assert result["preview_config"]["parcel_resolution_summary"]["property_match_status"] == "not_resolved"
    assert result["proximity_result"]["property_match_status"] == "not_resolved"
    assert "Address matched, but related parcel was not resolved" in " ".join(result["warnings"])


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
    assert result["review_packet_id"] == "packet"
    assert result["packet_id"] == "packet"
    assert result["recipe"]["selected_layers"]
    assert result["webmap_json"]["operationalLayers"]
    assert result["preview_config"]["operational_layers"] == []
    assert result["preview_config"]["basemap"] == "streets-vector"
    assert result["preview_config"]["context_layers"] == []
    assert result["preview_config"]["map_title"] == result["map_title"]
    assert extent["xmin"] == -80.72
    assert extent["xmax"] == -80.46


def test_composer_commercial_zoning_preview_carries_visible_qa(monkeypatch, tmp_path):
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr(
        "app.map_composer._preview_config_for",
        lambda path, can_preview: {
            "initial_extent": {"xmin": -80.72, "ymin": 35.30, "xmax": -80.46, "ymax": 35.49, "spatialReference": {"wkid": 4326}},
            "operational_layers": [
                {"layer_key": "zoning", "title": "Cabarrus County Zoning", "category": "zoning", "role": "constraint_overlay", "url": "https://example.test/Zoning/0", "visibility": True, "definition_expression": "ZONING_GEN IN ('COMMERCIAL', 'OFFICE')"},
                {"layer_key": "roads", "title": "Road Centerlines", "category": "transportation", "role": "transportation_layer", "url": "https://example.test/Roads/0", "visibility": True},
                {"layer_key": "tax_parcels", "title": "Tax Parcels", "category": "parcel", "role": "base_layer", "url": "https://example.test/Parcels/0", "visibility": True},
            ],
        },
    )
    monkeypatch.setattr(
        "app.map_composer.visible_map_qa",
        lambda config, recipe: {
            "visible_feature_summary": [
                {"layer_id": "zoning", "layer_title": "Cabarrus County Zoning", "expected_role": "zoning", "feature_count": 18, "visible": True, "opacity": 0.48, "fallback_used": False, "warning": None},
                {"layer_id": "roads", "layer_title": "Road Centerlines", "expected_role": "roads", "feature_count": 41, "visible": True, "opacity": 0.92, "fallback_used": True, "warning": "Major-road classification was unavailable; showing road context."},
                {"layer_id": "tax_parcels", "layer_title": "Tax Parcels", "expected_role": "parcel_context", "feature_count": None, "visible": False, "opacity": 0.34, "fallback_used": False, "warning": None},
            ],
            "visible_feature_total": 59,
            "visible_extent": {"xmin": -80.7, "ymin": 35.31, "xmax": -80.47, "ymax": 35.48, "spatialReference": {"wkid": 4326}},
            "warnings": ["Major-road classification was unavailable; showing road context."],
            "fallback_used": True,
        },
    )

    result = generate_composer_draft("show commercial zoning around Concord with nearby major roads")

    assert result["request_type"] == "zoning_context"
    assert result["request_plan"]["parameters"]["geography"] == "Concord"
    assert result["can_preview"] is True
    assert result["visible_feature_summary"][0]["feature_count"] == 18
    assert result["visible_feature_summary"][0]["opacity"] == 0.48
    assert result["preview_config"]["visible_feature_total"] == 59
    assert result["preview_config"]["focus_extent"]["xmin"] == -80.7
    assert result["preview_config"]["aoi"]["type"] == "municipality"
    assert result["preview_config"]["aoi"]["summary"] == "Concord boundary + 2 mile buffer"
    context_layers = result["preview_config"]["context_layers"]
    zoning_layer = next(layer for layer in context_layers if layer["layer_key"] == "zoning")
    roads_layer = next(layer for layer in context_layers if layer["layer_key"] == "roads")
    parcel_layer = next(layer for layer in result["preview_config"]["context_layers"] if layer["layer_key"] == "tax_parcels")
    assert zoning_layer["title"] == "Commercial zoning"
    assert zoning_layer["legend_label"] == "Commercial zoning"
    assert zoning_layer["cartography_role"] == "commercial_zoning"
    assert zoning_layer["opacity"] == 0.48
    assert zoning_layer["clipped_to_aoi"] is True
    assert roads_layer["legend_label"] == "Road context"
    assert roads_layer["cartography_role"] == "roads"
    assert roads_layer["map_role"] == "road_context"
    assert roads_layer["clipped_to_aoi"] is True
    assert roads_layer["opacity"] == 0.92
    assert roads_layer["draw_order"] > zoning_layer["draw_order"]
    assert parcel_layer["visibility"] is False
    assert parcel_layer["diagnostics_only"] is True
    assert "Major-road classification was unavailable" in " ".join(result["warnings"])


def test_commercial_zoning_empty_filter_fallback_is_visible_on_map(monkeypatch, tmp_path):
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr(
        "app.map_composer._preview_config_for",
        lambda path, can_preview: {
            "initial_extent": {"xmin": -80.72, "ymin": 35.30, "xmax": -80.46, "ymax": 35.49, "spatialReference": {"wkid": 4326}},
            "operational_layers": [
                {
                    "layer_key": "zoning",
                    "title": "Commercial zoning",
                    "category": "zoning",
                    "role": "constraint_overlay",
                    "url": "https://example.test/Zoning/0",
                    "visibility": True,
                    "definition_expression": "ZONING_GEN = 'COMMERCIAL'",
                    "opacity": 0.48,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "app.map_composer.visible_map_qa",
        lambda config, recipe: {
            "visible_feature_summary": [
                {
                    "layer_id": "zoning",
                    "layer_title": "Commercial zoning",
                    "expected_role": "zoning",
                    "feature_count": 27,
                    "visible": True,
                    "opacity": 0.48,
                    "fallback_used": True,
                    "warning": "Commercial zoning values were not confidently identified; showing zoning context around Concord.",
                }
            ],
            "visible_feature_total": 27,
            "visible_extent": {"xmin": -80.7, "ymin": 35.31, "xmax": -80.47, "ymax": 35.48, "spatialReference": {"wkid": 4326}},
            "warnings": ["Commercial zoning values were not confidently identified; showing zoning context around Concord."],
            "fallback_used": True,
        },
    )

    result = generate_composer_draft("show commercial zoning around Concord")

    zoning_layer = result["preview_config"]["context_layers"][0]
    assert zoning_layer["title"] == "Zoning context"
    assert zoning_layer["legend_label"] == "Zoning context"
    assert zoning_layer["cartography_role"] == "zoning"
    assert zoning_layer["opacity"] == 0.22
    assert zoning_layer["fallback_used"] is True
    assert "definition_expression" not in zoning_layer


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
    assert adjusted["composer_map_state"]["map_title"] == "Concord Flood Draft"
    assert adjusted["composer_map_state"]["adjusted_state_applied"] is True
    assert adjusted["composer_map_state"]["layer_titles"]["flood_100"] == "100-Year Floodplain"
    assert adjusted["composer_map_state"]["layer_opacity"]["flood_100"] == 0.45
    assert "tax_parcels" in {layer["layer_key"] for layer in adjusted["composer_map_state"]["hidden_layers"]}


def test_composer_map_state_saves_after_generate(monkeypatch, tmp_path):
    captured: dict[str, dict] = {}
    session_root = tmp_path / "composer_sessions"
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: session_root)
    monkeypatch.setattr("app.map_composer.upsert_composer_map_state", lambda session_id, state: captured.setdefault(session_id, state))
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})

    result = generate_composer_draft("Show parcels in Concord that are in the 100-year floodplain.")
    state_path = session_root / result["composer_session_id"] / "composer_map_state.json"

    assert state_path.exists()
    assert result["composer_map_state"]["composer_session_id"] == result["composer_session_id"]
    assert captured[result["composer_session_id"]]["map_title"] == result["map_title"]
    assert result["composer_map_state_persisted"] is True
    assert result["composer_map_state"]["export_mode"] == "map_sheet"
    assert result["composer_map_state"]["report_section_config"]["include_layer_table"] is False
    assert result["composer_map_state"]["report_section_config"]["include_statistics"] is False


def test_composer_export_updates_saved_state_and_report_options(monkeypatch, tmp_path):
    session_root = tmp_path / "composer_sessions"
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: session_root)
    monkeypatch.setattr("app.map_composer.upsert_composer_map_state", lambda session_id, state: None)
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})
    monkeypatch.setattr(
        "app.map_composer.generate_report",
        lambda packet_path: SimpleNamespace(
            report_id="report_test",
            report_path=tmp_path / "report",
            report_title="Report",
            files={},
            validation={"is_valid": True, "errors": [], "warnings": []},
        ),
    )
    result = generate_composer_draft("Show parcels in Concord that are in the 100-year floodplain.")

    exported = export_composer_session(
        result["composer_session_id"],
        {
            "map_title": "Adjusted Export Title",
            "report_config": {"include_statistics": True, "include_permit_summary": True},
            "layers": [{"layer_key": "flood_100", "title": "Flood Context", "visibility": True, "opacity": 0.4}],
        },
    )

    assert exported["composer_map_state"]["map_title"] == "Adjusted Export Title"
    assert exported["composer_map_state"]["report_section_config"]["include_permit_summary"] is True
    assert exported["report_statistics"]["permit_summary"]["available"] is False
    assert "unresolved" in exported["report_statistics"]["permit_summary"]["reason"]


def test_full_report_export_mode_enables_appendix_sections(monkeypatch, tmp_path):
    session_root = tmp_path / "composer_sessions"
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer._session_root", lambda: session_root)
    monkeypatch.setattr("app.map_composer.upsert_composer_map_state", lambda session_id, state: None)
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr("app.map_composer._preview_config_for", lambda path, can_preview: {"operational_layers": []})
    monkeypatch.setattr(
        "app.map_composer.generate_report",
        lambda packet_path: SimpleNamespace(
            report_id="report_test",
            report_path=tmp_path / "report",
            report_title="Report",
            files={},
            validation={"is_valid": True, "errors": [], "warnings": []},
        ),
    )
    result = generate_composer_draft("Show parcels in Concord that are in the 100-year floodplain.")

    exported = export_composer_session(
        result["composer_session_id"],
        {
            "export_mode": "full_report",
            "map_state": {
                "map_extent": {"xmin": -80.7, "ymin": 35.2, "xmax": -80.4, "ymax": 35.5},
                "current_center": {"longitude": -80.55, "latitude": 35.36},
                "current_zoom": 14,
                "current_scale": 9028.4,
            },
        },
    )

    state = exported["composer_map_state"]
    assert state["export_mode"] == "full_report"
    assert state["export_options"]["include_appendix"] is True
    assert state["report_section_config"]["include_layer_table"] is True
    assert state["report_section_config"]["include_statistics"] is True
    assert state["map_extent"]["xmin"] == -80.7
    assert state["current_center"]["longitude"] == -80.55
    assert state["current_zoom"] == 14
    assert state["current_scale"] == 9028.4


def test_map_sheet_export_options_preserve_dimensions_and_furniture():
    options = normalize_print_options(
        {
            "export_mode": "map_sheet",
            "sheet_size_preset": "custom",
            "sheet_width": 17,
            "sheet_height": 11,
            "sheet_orientation": "landscape",
            "sheet_dpi": 300,
            "sheet_margin": "narrow",
            "scale_mode": "fixed_scale",
            "fixed_scale": "12000",
            "include_legend": False,
            "include_north_arrow": True,
            "include_layer_table": True,
        }
    )
    manifest = export_manifest_metadata(options, locked_map_state_used=True)

    assert options["export_mode"] == "map_sheet"
    assert options["include_layer_table"] is True
    assert options["sheet_width"] == 17
    assert options["sheet_height"] == 11
    assert manifest["exportMode"] == "map_sheet"
    assert manifest["sheetSize"]["preset"] == "custom"
    assert manifest["sheetSize"]["width"] == 17
    assert manifest["mapScale"]["scaleMode"] == "fixed_scale"
    assert manifest["mapScale"]["fixedScale"] == "12000"
    assert manifest["mapFurniture"]["legend"] is False
    assert manifest["mapFurniture"]["northArrow"] is True
    assert manifest["lockedMapStateUsed"] is True


def test_save_map_state_api_returns_exact_state(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.update_composer_map_state_for_session",
        lambda session_id, payload: {
            "composer_session_id": session_id,
            "composer_map_state": {
                "composer_session_id": session_id,
                "map_title": payload["map_title"],
                "map_extent": payload["map_state"]["map_extent"],
                "current_center": payload["map_state"]["current_center"],
                "current_zoom": payload["map_state"]["current_zoom"],
                "current_scale": payload["map_state"]["current_scale"],
                "export_mode": payload["export_mode"],
            },
            "composer_map_state_persisted": True,
        },
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/composer/composer_test/save-map-state",
        json={
            "composer_session_id": "composer_test",
            "map_title": "Adjusted Print Title",
            "export_mode": "map_exhibit_only",
            "map_state": {
                "map_extent": {"xmin": 1, "ymin": 2, "xmax": 3, "ymax": 4},
                "current_center": {"longitude": -80.5, "latitude": 35.4},
                "current_zoom": 13,
                "current_scale": 12000,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["composer_map_state"]["map_title"] == "Adjusted Print Title"
    assert body["composer_map_state"]["map_extent"]["xmax"] == 3
    assert body["composer_map_state"]["current_center"]["latitude"] == 35.4
    assert body["composer_map_state"]["current_zoom"] == 13
    assert body["composer_map_state"]["current_scale"] == 12000
    assert body["export_mode"] == "map_exhibit_only"


def test_report_statistics_marks_missing_data_unavailable_without_fake_counts():
    stats = build_report_statistics(
        {
            "visible_layers": [{"layer_key": "origin", "source_role": "derived local"}],
            "derived_overlays": [{"id": "route_line", "local_output": True}],
            "warnings": ["Draft only"],
            "missing_data": ["current_permits"],
            "proximity_summary": {"distance_value": 1.11, "distance_unit": "miles", "route_mode": "straight_line_fallback"},
        }
    )

    assert stats["proximity"]["distance"]["value"] == 1.11
    assert stats["source_coverage_counts"]["derived_local"] == 2
    assert stats["permit_summary"]["available"] is False
    assert stats["planning_cases_summary"]["available"] is False


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
