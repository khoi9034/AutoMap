import json

from app.review_packet_builder import (
    build_layer_review_table,
    build_review_packet,
    build_review_summary,
    build_warning_report,
    make_packet_folder_name,
    save_review_packet,
    validate_review_packet,
)


def sample_recipe(*, needs_warning=True, missing_data=None):
    review_reasons = []
    filter_plan = {}
    if needs_warning:
        review_reasons = ["Commercial zoning field/code needs review.", "Proximity distance needs review."]
        filter_plan = {
            "zoning": {
                "needs_review": True,
                "review_reason": "Confirm which zoning codes count as commercial.",
                "draft_where_clause": None,
            }
        }
    return {
        "map_title": "Zoning in Concord",
        "user_intent": "Show commercial zoning around Concord.",
        "parsed_request": {
            "raw_prompt": "Show commercial zoning around Concord.",
            "historical_year": None,
        },
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
                "layer_key": "zoning",
                "layer_name": "Concord Zoning",
                "category": "zoning",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Zoning/MapServer/0",
                "service_url": "https://location.example.com/arcgis/rest/services/OpenData/Zoning/MapServer",
                "source_status": "active",
                "source_priority": 1,
                "geometry_type": "esriGeometryPolygon",
                "confidence_score": 0.84,
                "match_reasons": ["category matches zoning"],
                "role": "constraint_overlay",
            },
        ],
        "filter_plan": filter_plan,
        "spatial_operations": [{"operation": "proximity_search", "notes": "Needs distance review."}],
        "suggested_extent": {"type": "geography", "value": "Concord"},
        "confidence_score": 0.84,
        "needs_review": needs_warning,
        "review_reasons": review_reasons,
        "missing_data_needed": missing_data or [],
    }


def sample_webmap(*, missing_url=False):
    return {
        "title": "Zoning in Concord",
        "operationalLayers": [
            {
                "title": "MunicipalDistrict",
                "url": "" if missing_url else "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer/0",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer",
                "layerUrl": "" if missing_url else "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer/0",
                "opacity": 0.9,
                "visibility": True,
                "autoMapLayerKey": "municipal",
                "autoMapRole": "jurisdiction_filter",
                "autoMapNeedsReview": False,
                "autoMapReviewWarnings": [],
                "layerDefinition": {"definitionExpression": "DISTRICT = 'CITY OF CONCORD'"},
                "autoMapDefinitionSource": "filter_plan",
                "autoMapFilterPlanLayerKey": "municipal",
            },
            {
                "title": "Concord Zoning",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Zoning/MapServer/0",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/Zoning/MapServer",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/Zoning/MapServer/0",
                "opacity": 0.65,
                "visibility": True,
                "autoMapLayerKey": "zoning",
                "autoMapRole": "constraint_overlay",
                "autoMapNeedsReview": True,
                "autoMapReviewWarnings": ["Zoning code field or selected zoning values need review."],
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
        "autoMapWarnings": ["Commercial zoning field/code needs review."],
        "autoMapValidation": {"is_valid": not missing_url, "errors": [], "warnings": [], "operational_layer_count": 2},
    }


def test_packet_folder_name_generation():
    assert make_packet_folder_name("Show parcels in Concord!") == "show_parcels_in_concord"


def test_review_summary_generation_includes_required_context():
    summary = build_review_summary(sample_recipe(), sample_webmap())

    assert "Show commercial zoning around Concord." in summary
    assert "Zoning in Concord" in summary
    assert "MunicipalDistrict" in summary
    assert "DISTRICT = 'CITY OF CONCORD'" in summary
    assert "This is a draft review packet and not an official map." in summary


def test_warning_grouping():
    recipe = sample_recipe(missing_data=["planning cases"])

    warnings = build_warning_report(recipe, sample_webmap())

    assert any("Commercial zoning" in item for item in warnings["filter_warnings"])
    assert any("planning cases" in item for item in warnings["missing_data_warnings"])
    assert any("No ArcGIS item was published." in item for item in warnings["publishing_blockers"])


def test_historical_warning_grouping():
    recipe = sample_recipe(needs_warning=False)
    recipe["parsed_request"]["historical_year"] = 2014
    recipe["selected_layers"][0]["source_status"] = "legacy_historical"
    recipe["selected_layers"][0]["layer_name"] = "PARCELTAXVIEW_2014"

    warnings = build_warning_report(recipe, sample_webmap())

    assert any("2014" in item for item in warnings["historical_data_warnings"])


def test_layer_review_table_generation():
    rows = build_layer_review_table(sample_recipe(), sample_webmap())

    assert rows[0]["title"] == "MunicipalDistrict"
    assert rows[0]["definition_expression"] == "DISTRICT = 'CITY OF CONCORD'"
    assert rows[1]["layer_key"] == "zoning"
    assert rows[1]["needs_review"] is True


def test_review_html_generation_and_packet_validation(tmp_path):
    packet_path = save_review_packet(
        "Show commercial zoning around Concord.",
        sample_recipe(),
        sample_webmap(),
        output_dir=tmp_path,
    )

    assert (packet_path / "review.html").exists()
    html = (packet_path / "review.html").read_text(encoding="utf-8")
    assert "Selected Layers" in html
    assert "Draft WebMap JSON" in html
    assert "No ArcGIS login is required" in html
    validation = validate_review_packet(packet_path)
    assert validation["is_valid"] is True


def test_packet_validation_catches_missing_files(tmp_path):
    packet_path = tmp_path / "packet"
    packet_path.mkdir()
    (packet_path / "recipe.json").write_text("{}", encoding="utf-8")

    validation = validate_review_packet(packet_path)

    assert validation["is_valid"] is False
    assert any("Missing required packet files" in error for error in validation["errors"])


def test_packet_validation_catches_missing_layer_url(tmp_path):
    packet_path = save_review_packet(
        "Show commercial zoning around Concord.",
        sample_recipe(needs_warning=False),
        sample_webmap(missing_url=True),
        output_dir=tmp_path,
    )

    validation = validate_review_packet(packet_path)

    assert validation["is_valid"] is False
    assert any("missing URL" in error for error in validation["errors"])


def test_generated_review_packet_does_not_include_secrets(tmp_path):
    packet_path = save_review_packet(
        "Show zoning.",
        sample_recipe(needs_warning=False),
        sample_webmap(),
        output_dir=tmp_path,
    )

    combined = "\n".join(path.read_text(encoding="utf-8") for path in packet_path.iterdir())
    lowered = combined.lower()
    assert ".env" not in lowered
    assert "database_url" not in lowered
    assert "password" not in lowered
    assert "token" not in lowered
    assert validate_review_packet(packet_path)["is_valid"] is True


def test_no_arcgis_login_required_and_no_publishing_occurs(monkeypatch):
    monkeypatch.setattr("app.review_packet_builder.build_recipe", lambda prompt: sample_recipe())
    monkeypatch.setattr("app.review_packet_builder.build_webmap_json", lambda recipe: sample_webmap())

    packet = build_review_packet("Show commercial zoning around Concord.")
    serialized = json.dumps(packet).lower()

    assert "no arcgis item was published" in serialized
    assert "no arcgis login is required" in serialized
    assert "portalurl" not in serialized
    assert "portalitem" not in serialized
