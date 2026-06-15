import json

import yaml

from app.adjustment_engine import (
    apply_adjustments_to_recipe,
    apply_adjustments_to_review_packet,
    apply_adjustments_to_webmap,
    create_adjustment_template,
    load_adjustment_file,
    validate_adjusted_packet,
    validate_adjustment_file,
)
from app.review_packet_builder import save_review_packet


def sample_recipe():
    return {
        "map_title": "Parcel Flood in Concord",
        "map_description": "Original draft description.",
        "user_intent": "Show parcels in Concord that are in the 100-year floodplain.",
        "parsed_request": {"raw_prompt": "Show parcels in Concord that are in the 100-year floodplain."},
        "selected_layers": [
            {
                "layer_key": "municipal",
                "layer_name": "MunicipalDistrict",
                "category": "jurisdiction",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer/0",
                "service_url": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer",
                "source_status": "active",
                "source_priority": 1,
                "geometry_type": "esriGeometryPolygon",
                "confidence_score": 0.91,
                "match_reasons": ["municipal boundary requested"],
                "role": "jurisdiction_filter",
            },
            {
                "layer_key": "parcels",
                "layer_name": "Tax Parcels",
                "category": "parcel",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/1",
                "service_url": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer",
                "source_status": "active",
                "source_priority": 1,
                "geometry_type": "esriGeometryPolygon",
                "confidence_score": 0.9,
                "match_reasons": ["parcel requested"],
                "role": "base_layer",
            },
            {
                "layer_key": "flood100",
                "layer_name": "FloodPlain100year",
                "category": "flood",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
                "service_url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer",
                "source_status": "active",
                "source_priority": 1,
                "geometry_type": "esriGeometryPolygon",
                "confidence_score": 0.94,
                "match_reasons": ["100-year floodplain requested"],
                "role": "constraint_overlay",
            },
        ],
        "filter_plan": {
            "municipal": {
                "draft_where_clause": "DISTRICT = 'CITY OF CONCORD'",
                "needs_review": False,
                "review_reason": None,
            }
        },
        "spatial_operations": [{"operation": "intersect", "output": "affected_parcels"}],
        "symbology_recommendations": [],
        "suggested_extent": {"type": "geography", "value": "Concord"},
        "confidence_score": 0.9,
        "needs_review": True,
        "review_reasons": ["Human review required before publishing."],
        "missing_data_needed": [],
    }


def sample_webmap():
    return {
        "title": "Parcel Flood in Concord",
        "description": "Draft WebMap JSON generated locally.",
        "operationalLayers": [
            {
                "title": "MunicipalDistrict",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer/0",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer/0",
                "opacity": 0.9,
                "visibility": True,
                "showLegend": True,
                "autoMapLayerKey": "municipal",
                "autoMapRole": "jurisdiction_filter",
                "autoMapNeedsReview": False,
                "autoMapReviewWarnings": [],
                "layerDefinition": {
                    "definitionExpression": "DISTRICT = 'CITY OF CONCORD'",
                },
                "autoMapDefinitionSource": "filter_plan",
                "autoMapFilterPlanLayerKey": "municipal",
            },
            {
                "title": "Affected Tax Parcels",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/1",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/1",
                "opacity": 0.8,
                "visibility": True,
                "showLegend": True,
                "autoMapLayerKey": "parcels",
                "autoMapRole": "base_layer",
                "autoMapNeedsReview": False,
                "autoMapReviewWarnings": [],
                "layerDefinition": {},
            },
            {
                "title": "FloodPlain100year",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
                "opacity": 0.35,
                "visibility": True,
                "showLegend": True,
                "autoMapLayerKey": "flood100",
                "autoMapRole": "constraint_overlay",
                "autoMapNeedsReview": False,
                "autoMapReviewWarnings": [],
                "layerDefinition": {},
            },
        ],
        "baseMap": {},
        "spatialReference": {},
        "version": "2.31",
        "authoringApp": "AutoMap",
        "authoringAppVersion": "0.4",
        "applicationProperties": {},
        "initialState": {"viewpoint": {"targetGeometry": {}}},
        "autoMapValidation": {"is_valid": True, "errors": [], "warnings": [], "operational_layer_count": 3},
    }


def sample_adjustments():
    return {
        "map_title": "Concord Flood Exposure Draft",
        "map_description": "Draft map showing tax parcels in Concord and the 100-year floodplain.",
        "layer_order": ["MunicipalDistrict", "Tax Parcels", "FloodPlain100year"],
        "layer_adjustments": {
            "FloodPlain100year": {"opacity": 0.45, "visibility": True, "title": "100-Year Floodplain"},
            "Tax Parcels": {"opacity": 0.72, "visibility": False, "title": "Affected Tax Parcels"},
        },
        "definition_expression_overrides": {
            "MunicipalDistrict": "DISTRICT = 'CITY OF CONCORD'",
        },
        "symbology_overrides": {"FloodPlain100year": "Use transparent blue fill."},
        "popup_overrides": {"Tax Parcels": {"description": "Parcel review popup."}},
        "reviewer_notes": ["Confirm parcel selection logic before official use."],
        "warnings_to_resolve": ["Human review required before publishing."],
        "warnings_to_keep": [],
        "missing_data_notes": ["No additional missing data notes."],
        "publish_ready": True,
    }


def test_loading_yaml_adjustment_file(tmp_path):
    path = tmp_path / "adjustments.yaml"
    path.write_text(yaml.safe_dump(sample_adjustments(), sort_keys=False), encoding="utf-8")

    adjustments = load_adjustment_file(path)

    assert adjustments["map_title"] == "Concord Flood Exposure Draft"
    assert adjustments["layer_adjustments"]["FloodPlain100year"]["opacity"] == 0.45


def test_validate_adjustment_file():
    validation = validate_adjustment_file(sample_adjustments())

    assert validation["is_valid"] is True


def test_apply_map_title_override_to_recipe():
    adjusted = apply_adjustments_to_recipe(sample_recipe(), sample_adjustments())

    assert adjusted["map_title"] == "Concord Flood Exposure Draft"
    assert adjusted["map_description"].startswith("Draft map")
    assert adjusted["human_adjustment"]["audit"]["map_title_changed"] is True


def test_apply_layer_opacity_and_visibility_override_to_webmap():
    adjusted = apply_adjustments_to_webmap(sample_webmap(), sample_adjustments())
    layers = {layer["autoMapLayerKey"]: layer for layer in adjusted["operationalLayers"]}

    assert layers["flood100"]["opacity"] == 0.45
    assert layers["parcels"]["visibility"] is False
    assert layers["flood100"]["title"] == "100-Year Floodplain"


def test_apply_layer_order_override():
    adjustments = sample_adjustments()
    adjustments["layer_order"] = ["FloodPlain100year", "MunicipalDistrict", "Tax Parcels"]

    adjusted = apply_adjustments_to_webmap(sample_webmap(), adjustments)

    assert [layer["autoMapLayerKey"] for layer in adjusted["operationalLayers"]] == [
        "flood100",
        "municipal",
        "parcels",
    ]


def test_apply_definition_expression_override():
    adjustments = sample_adjustments()
    adjustments["definition_expression_overrides"] = {"FloodPlain100year": "ZONE = 'AE'"}

    adjusted = apply_adjustments_to_webmap(sample_webmap(), adjustments)
    flood_layer = next(layer for layer in adjusted["operationalLayers"] if layer["autoMapLayerKey"] == "flood100")

    assert flood_layer["layerDefinition"]["definitionExpression"] == "ZONE = 'AE'"
    assert flood_layer["autoMapDefinitionSource"] == "human_adjustment"


def test_remove_layer_and_preserve_audit_trail():
    adjustments = sample_adjustments()
    adjustments["layer_adjustments"]["FloodPlain100year"]["remove_layer"] = True

    adjusted_recipe = apply_adjustments_to_recipe(sample_recipe(), adjustments)
    adjusted_webmap = apply_adjustments_to_webmap(sample_webmap(), adjustments)

    assert "flood100" not in {layer["layer_key"] for layer in adjusted_recipe["selected_layers"]}
    assert "flood100" not in {layer["autoMapLayerKey"] for layer in adjusted_webmap["operationalLayers"]}
    assert adjusted_recipe["human_adjustment"]["audit"]["removed_layers"]
    assert adjusted_webmap["autoMapAdjustment"]["audit"]["removed_layers"]


def test_adjusted_packet_validation_and_no_original_mutation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet_path = save_review_packet(
        "Show parcels in Concord that are in the 100-year floodplain.",
        sample_recipe(),
        sample_webmap(),
        output_dir=tmp_path / "outputs" / "review_packets",
    )
    original_recipe_before = (packet_path / "recipe.json").read_text(encoding="utf-8")
    adjustment_path = packet_path / "adjustments.yaml"
    adjustment_path.write_text(yaml.safe_dump(sample_adjustments(), sort_keys=False), encoding="utf-8")

    adjusted_path = apply_adjustments_to_review_packet(packet_path, adjustment_path)
    validation = validate_adjusted_packet(adjusted_path)

    assert validation["is_valid"] is True
    assert (adjusted_path / "adjusted_review.html").exists()
    assert (packet_path / "recipe.json").read_text(encoding="utf-8") == original_recipe_before


def test_warning_resolution_and_publish_ready_blocker_behavior(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    adjustments = sample_adjustments()
    packet_path = save_review_packet(
        "Show parcels in Concord that are in the 100-year floodplain.",
        sample_recipe(),
        sample_webmap(),
        output_dir=tmp_path / "outputs" / "review_packets",
    )
    adjustment_path = packet_path / "adjustments.yaml"
    adjustment_path.write_text(yaml.safe_dump(adjustments, sort_keys=False), encoding="utf-8")

    adjusted_path = apply_adjustments_to_review_packet(packet_path, adjustment_path)
    warnings = json.loads((adjusted_path / "adjusted_warnings.json").read_text(encoding="utf-8"))

    assert warnings["reviewer_resolved"]
    assert warnings["publish_ready_requested"] is True
    assert warnings["publish_ready"] is False
    assert any("Publishing blocked" in item for item in warnings["active"]["publishing_blockers"])


def test_create_adjustment_template(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet_path = save_review_packet(
        "Show parcels in Concord that are in the 100-year floodplain.",
        sample_recipe(),
        sample_webmap(),
        output_dir=tmp_path,
    )

    template_path = create_adjustment_template(packet_path)

    assert template_path.exists()
    assert template_path.parent.name == "adjustment_templates"
    assert not (packet_path / "adjustments.template.yaml").exists()
    loaded = load_adjustment_file(template_path)
    assert "MunicipalDistrict" in loaded["layer_adjustments"]


def test_adjusted_packet_does_not_include_secrets_or_login_or_publish(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet_path = save_review_packet(
        "Show parcels in Concord that are in the 100-year floodplain.",
        sample_recipe(),
        sample_webmap(),
        output_dir=tmp_path / "outputs" / "review_packets",
    )
    adjustment_path = packet_path / "adjustments.yaml"
    adjustment_path.write_text(yaml.safe_dump(sample_adjustments(), sort_keys=False), encoding="utf-8")

    adjusted_path = apply_adjustments_to_review_packet(packet_path, adjustment_path)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in adjusted_path.iterdir()).lower()

    assert ".env" not in combined
    assert "database_url" not in combined
    assert "password" not in combined
    assert "portalurl" not in combined
    assert "portalitem" not in combined
    assert "adjusted_draft_only_not_published" in combined
    assert validate_adjusted_packet(adjusted_path)["is_valid"] is True
