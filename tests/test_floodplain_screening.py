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


def test_live_floodplain_screening_is_explicit_opt_in(monkeypatch):
    monkeypatch.delenv("AUTOMAP_ENABLE_LIVE_FLOODPLAIN_SCREENING", raising=False)
    assert live_floodplain_screening_enabled() is False

    monkeypatch.setenv("AUTOMAP_ENABLE_LIVE_FLOODPLAIN_SCREENING", "true")
    assert live_floodplain_screening_enabled() is True


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
    assert flood_legend["drawing_info"]["renderer"]["symbol"]["color"] == [56, 189, 248, 74]
    assert flood_legend["fill_color"] == [56, 189, 248, 74]
    assert flood_legend["outline_color"] == [3, 105, 161, 210]
    assert boundary_legend["fill_color"] == [255, 255, 255, 0]
    assert affected_legend["fill_color"] == [249, 115, 22, 86]
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
