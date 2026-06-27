import json

from app.automap_brain.floodplain_screening import attach_floodplain_screening_result, live_floodplain_screening_enabled
from app.automap_brain.request_parser import build_brain_plan
from app.map_composer import generate_composer_draft
from app.recipe_engine import build_recipe
from tests.test_analysis_executor import FakeSpatialQueryClient, isolate_outputs, sample_catalog


def test_floodplain_screening_plan_extracts_spatial_relationship():
    plan = build_brain_plan("show parcels in Concord that are in the 100-year floodplain")

    assert plan["request_type"] == "floodplain_screening"
    assert plan["primary_domain"] == "parcels"
    assert "floodplain" in plan["secondary_domains"]
    assert plan["geography"] == "Concord"
    assert plan["spatial_relationships"] == ["intersects"]
    assert plan["floodplain_type"] == "100_year"
    assert plan["constraint_domain"] == "floodplain"
    assert plan["result_layer"] == "affected_parcels"
    assert plan["parameters"]["result_layer"] == "affected_parcels"


def test_floodplain_screening_typo_variant_normalizes_to_same_intent():
    plan = build_brain_plan("show parcles in conord in the 100 year flood plane")

    assert plan["request_type"] == "floodplain_screening"
    assert plan["geography"] == "Concord"
    assert plan["floodplain_type"] == "100_year"
    assert plan["parameters"]["spatial_relationship"] == "intersects"


def test_live_floodplain_screening_is_enabled_by_default_with_disable_switch(monkeypatch):
    monkeypatch.delenv("AUTOMAP_ENABLE_LIVE_FLOODPLAIN_SCREENING", raising=False)
    monkeypatch.delenv("AUTOMAP_DISABLE_LIVE_FLOODPLAIN_SCREENING", raising=False)
    assert live_floodplain_screening_enabled() is True

    monkeypatch.setenv("AUTOMAP_DISABLE_LIVE_FLOODPLAIN_SCREENING", "true")
    assert live_floodplain_screening_enabled() is False

    monkeypatch.setenv("AUTOMAP_DISABLE_LIVE_FLOODPLAIN_SCREENING", "false")
    monkeypatch.setenv("AUTOMAP_ENABLE_LIVE_FLOODPLAIN_SCREENING", "false")
    assert live_floodplain_screening_enabled() is False


def test_floodplain_screening_attaches_affected_parcel_overlay(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)
    recipe = build_recipe(
        "show parcels in Concord that are in the 100-year floodplain",
        sample_catalog(),
        persist_data_gaps=False,
    )

    screened = attach_floodplain_screening_result(
        recipe,
        catalog_records=sample_catalog(),
        query_client=FakeSpatialQueryClient(),
    )

    output_path = tmp_path / screened["analysis_execution"]["derived_outputs"][0]["path"]
    output_geojson = json.loads(output_path.read_text(encoding="utf-8"))
    overlay = screened["derived_overlays"][0]

    assert screened["floodplain_screening"]["analysis_type"] == "floodplain_parcel_screening"
    assert screened["floodplain_screening"]["affected_feature_count"] == 1
    assert screened["floodplain_screening"]["spatial_relationship"] == "intersects"
    assert screened["analysis_execution"]["operation_type"] == "floodplain_parcel_screening"
    assert output_geojson["features"][0]["properties"]["PIN"] == "A"
    assert overlay["role"] == "affected_parcels"
    assert overlay["symbol_key"] == "affected_floodplain_parcel"
    assert overlay["legend_label"] == "Parcels in 100-year floodplain"
    assert overlay["feature_count"] == 1
    assert overlay["extent"]["xmin"] < overlay["extent"]["xmax"]


def test_composer_floodplain_preview_promotes_affected_parcels(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr(
        "app.map_composer.build_recipe",
        lambda prompt: build_recipe(prompt, sample_catalog(), persist_data_gaps=False),
    )
    monkeypatch.setattr(
        "app.map_composer.attach_floodplain_screening_result",
        lambda recipe: attach_floodplain_screening_result(
            recipe,
            catalog_records=sample_catalog(),
            query_client=FakeSpatialQueryClient(),
        ),
    )
    packet_path = tmp_path / "review_packets" / "packet"
    packet_path.mkdir(parents=True)
    monkeypatch.setattr("app.map_composer.save_review_packet", lambda prompt, recipe, webmap: packet_path)
    monkeypatch.setattr(
        "app.map_composer._preview_config_for",
        lambda path, can_preview: {
            "initial_extent": {"xmin": -80.72, "ymin": 35.30, "xmax": -80.46, "ymax": 35.49, "spatialReference": {"wkid": 4326}},
            "operational_layers": [
                {"layer_key": "parcels", "title": "Tax Parcels", "category": "parcel", "role": "base_layer", "url": "https://example.test/parcels/0", "visibility": True},
                {"layer_key": "flood100", "title": "FloodPlain100year", "category": "flood", "role": "constraint_overlay", "url": "https://example.test/flood100/2", "visibility": True},
                {"layer_key": "municipal", "title": "MunicipalDistrict", "category": "jurisdiction", "role": "jurisdiction_filter", "url": "https://example.test/municipal/0", "visibility": True},
            ],
        },
    )
    monkeypatch.setattr(
        "app.map_composer.visible_map_qa",
        lambda config, recipe: {
            "visible_feature_summary": [
                {"layer_id": "affected", "layer_title": "Parcels in 100-year floodplain", "expected_role": "affected_parcels", "feature_count": 1, "visible": True, "clipped_to_aoi": True},
                {"layer_id": "flood100", "layer_title": "100-year floodplain", "expected_role": "floodplain_overlay", "feature_count": 1, "visible": True, "clipped_to_aoi": True},
                {"layer_id": "parcels", "layer_title": "Tax Parcels", "expected_role": "parcel_context", "feature_count": None, "visible": False, "clipped_to_aoi": True},
            ],
            "visible_feature_total": 2,
            "visible_extent": {"xmin": 2.9, "ymin": 2.9, "xmax": 5.1, "ymax": 5.1, "spatialReference": {"wkid": 4326}},
            "warnings": [],
            "fallback_used": False,
        },
    )

    result = generate_composer_draft("show parcels in Concord that are in the 100-year floodplain")

    assert result["request_type"] == "floodplain_screening"
    assert result["result_state"] == "ready"
    assert result["can_preview"] is True
    assert result["requested_result"] == "Parcels in 100-year floodplain"
    assert result["primary_result_role"] == "affected_parcels"
    assert result["analysis_type"] == "floodplain_parcel_screening"
    assert result["affected_feature_count"] == 1
    assert result["result_layer_role"] == "affected_parcels"
    assert result["map_layout"]["title"] == "Concord Floodplain Parcel Screening"
    assert result["map_layout"]["subtitle"].startswith("Parcels intersecting the 100-year floodplain")
    overlays = result["preview_config"]["derived_overlays"]
    assert overlays[0]["legend_label"] == "Parcels in 100-year floodplain"
    legend_items = result["map_layout"]["legend_items"]
    flood_legend = next(item for item in legend_items if item["label"] == "100-year floodplain")
    boundary_legend = next(item for item in legend_items if item["label"] == "Concord boundary")
    affected_legend = next(item for item in legend_items if item["label"] == "Parcels in 100-year floodplain")
    assert flood_legend["drawing_info"]["renderer"]["symbol"]["color"] == [14, 165, 233, 112]
    assert flood_legend["fill_color"] == [14, 165, 233, 112]
    assert flood_legend["fill_opacity"] > 0.4
    assert flood_legend["outline_color"] == [2, 132, 199, 235]
    assert flood_legend["outline_width"] >= 1.5
    assert boundary_legend["fill_color"] == [255, 255, 255, 0]
    assert boundary_legend["outline_width"] >= 2.4
    assert affected_legend["fill_color"] == [245, 158, 11, 118]
    assert affected_legend["outline_width"] <= 1.5
    assert all(item["label"] != "Tax Parcels" for item in legend_items)
    context_layers = result["preview_config"]["context_layers"]
    parcel_layer = next(layer for layer in context_layers if layer["layer_key"] == "parcels")
    flood_layer = next(layer for layer in context_layers if layer["layer_key"] == "flood100")
    boundary_layer = next(layer for layer in context_layers if layer["layer_key"] == "municipal")
    assert parcel_layer["visibility"] is False
    assert parcel_layer["diagnostics_only"] is True
    assert parcel_layer["map_role"] == "diagnostics_only"
    assert flood_layer["legend_label"] == "100-year floodplain"
    assert boundary_layer["legend_label"] == "Concord boundary"
    assert result["visible_feature_summary"][0]["expected_role"] == "affected_parcels"


def test_dense_floodplain_result_uses_generalized_display_geojson(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)
    recipe = build_recipe(
        "show parcels in Concord that are in the 100-year floodplain",
        sample_catalog(),
        persist_data_gaps=False,
    )
    output_path = tmp_path / "outputs" / "analysis_runs" / "run" / "affected_parcels.geojson"
    output_path.parent.mkdir(parents=True)

    features = []
    for index in range(120):
        x = float(index % 20)
        y = float(index // 20)
        features.append(
            {
                "type": "Feature",
                "properties": {"OBJECTID": index + 1},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[x, y], [x + 0.4, y], [x + 0.4, y + 0.4], [x, y + 0.4], [x, y]]],
                },
            }
        )
    output_path.write_text(json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8")

    monkeypatch.setattr(
        "app.analysis_executor.execute_analysis",
        lambda *_args, **_kwargs: {
            "status": "completed",
            "analysis_run_id": "run",
            "output_count": 120,
            "output_geojson_path": "outputs/analysis_runs/run/affected_parcels.geojson",
        },
    )

    screened = attach_floodplain_screening_result(
        recipe,
        catalog_records=sample_catalog(),
        query_client=FakeSpatialQueryClient(),
    )

    overlay = screened["derived_overlays"][0]
    derived_output = screened["analysis_execution"]["derived_outputs"][0]
    display_path = tmp_path / overlay["path"]
    display_geojson = json.loads(display_path.read_text(encoding="utf-8"))

    assert overlay["display_mode"] == "dissolved_result_area"
    assert overlay["display_generalized"] is True
    assert overlay["feature_count"] == 120
    assert overlay["display_feature_count"] == 1
    assert overlay["analysis_geojson_path"] == "outputs/analysis_runs/run/affected_parcels.geojson"
    assert overlay["path"].endswith("affected_parcels_display.geojson")
    assert display_geojson["features"][0]["properties"]["automap_source_feature_count"] == 120
    assert derived_output["display_path"] == overlay["display_geojson_path"]
    assert screened["focus_mode"] == "result_focused_with_aoi_context"
    assert screened["analysis_execution"]["display_generalized"] is True


def test_floodplain_context_only_fallback_is_not_ready(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)
    monkeypatch.delenv("AUTOMAP_ENABLE_LIVE_FLOODPLAIN_SCREENING", raising=False)
    monkeypatch.setenv("AUTOMAP_DISABLE_LIVE_FLOODPLAIN_SCREENING", "true")
    monkeypatch.setattr("app.map_composer._session_root", lambda: tmp_path / "composer_sessions")
    monkeypatch.setattr("app.map_composer._can_use_fast_floodplain_fallback", lambda _path: True)

    result = generate_composer_draft("show parcels in Concord that are in the 100-year floodplain")

    assert result["can_preview"] is False
    assert result["result_state"] == "partial"
    assert result["requested_result"] == "Parcels in 100-year floodplain"
    assert result["available_context"] == ["100-year floodplain", "Concord boundary"]
    assert result["missing_operation"] == "Parcel-floodplain intersection"
    assert result["context_map_available"] is True
    assert result["primary_result_available"] is False
    assert result["requested_result_missing"] is True
    assert result["analysis_status"] == "partial_context_only"
    assert result["preview_quality"] == "partial_context_only"
    assert result["preview_blockers"]
    assert result["map_layout"]["title"] == "Concord Floodplain Context"
    assert result["map_layout"]["subtitle"] == "Affected parcel extraction unavailable. Showing 100-year floodplain context only."
    assert result["map_layout"]["print_ready"] is False
    assert result["next_action"] == "context_preview"
    labels = {item["label"] for item in result["map_layout"]["legend_items"]}
    assert "Parcels in 100-year floodplain" not in labels
    assert {"100-year floodplain", "Concord boundary"}.issubset(labels)


def test_floodplain_zero_matches_is_honest_not_blocked(monkeypatch):
    recipe = build_recipe(
        "show parcels in Concord that are in the 100-year floodplain",
        sample_catalog(),
        persist_data_gaps=False,
    )
    monkeypatch.setattr(
        "app.analysis_executor.execute_analysis",
        lambda *_args, **_kwargs: {"status": "completed", "output_count": 0, "blocked_reasons": []},
    )

    screened = attach_floodplain_screening_result(
        recipe,
        catalog_records=sample_catalog(),
        query_client=FakeSpatialQueryClient(),
    )

    assert screened["floodplain_screening"]["status"] == "no_matches"
    assert screened["analysis_execution"]["analysis_status"] == "no_matching_parcels"
    assert screened["analysis_execution"]["output_count"] == 0
