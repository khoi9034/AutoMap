import json

from app.webmap_builder import (
    build_operational_layer,
    build_popup_info,
    build_renderer,
    build_webmap_json,
    order_layers,
    validate_webmap_json,
)
from app.webmap_exporter import make_safe_filename


def layer(layer_key, layer_name, category, *, role="reference_layer", layer_id=0, geometry_type="esriGeometryPolygon", fields=None):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "layer_url": f"https://location.example.com/arcgis/rest/services/{layer_key}/MapServer/{layer_id}",
        "service_url": f"https://location.example.com/arcgis/rest/services/{layer_key}/MapServer",
        "source_key": "cabarrus_new_opendata",
        "source_status": "active",
        "source_priority": 1,
        "geometry_type": geometry_type,
        "layer_id": layer_id,
        "confidence_score": 0.91,
        "match_reasons": ["unit test"],
        "role": role,
        "display_field": "NAME",
        "object_id_field": "OBJECTID",
        "fields": fields
        or [
            {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID"},
            {"name": "NAME", "type": "esriFieldTypeString", "alias": "Name"},
        ],
        "extent": {
            "xmin": -80.8,
            "ymin": 35.1,
            "xmax": -80.4,
            "ymax": 35.5,
            "spatialReference": {"wkid": 4326},
        },
    }


def sample_recipe():
    return {
        "map_title": "Parcels And Flood In Concord",
        "user_intent": "Show parcels in Concord that are in the 100-year floodplain.",
        "parsed_request": {
            "geography_terms": [{"name": "Concord", "type": "municipality"}],
            "topics": ["parcel", "flood"],
        },
        "selected_layers": [
            layer("flood100", "FloodPlain100year", "flood", role="constraint_overlay", layer_id=2),
            layer(
                "parcels",
                "Tax Parcels",
                "parcel",
                role="base_layer",
                layer_id=0,
                fields=[
                    {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID"},
                    {"name": "PIN14", "type": "esriFieldTypeString", "alias": "Parcel PIN"},
                    {"name": "OWNER", "type": "esriFieldTypeString", "alias": "Owner"},
                ],
            ),
            layer("municipal", "MunicipalDistrict", "jurisdiction", role="jurisdiction_filter", layer_id=0),
        ],
        "filter_plan": {
            "municipal": {
                "draft_where_clause": "DISTRICT = 'CITY OF CONCORD'",
                "confidence_score": 0.58,
                "needs_review": True,
                "review_reason": "Confirm geography value exists in selected field samples.",
            },
            "flood100": {
                "draft_where_clause": None,
                "confidence_score": 0.9,
                "needs_review": False,
                "review_reason": None,
            },
        },
        "spatial_operations": [{"operation": "intersect", "output": "affected_parcels"}],
        "suggested_extent": {"type": "geography", "value": "Concord"},
        "confidence_score": 0.84,
        "needs_review": True,
        "review_reasons": ["Confirm geography value exists in selected field samples."],
        "missing_data_needed": [],
    }


def test_build_webmap_json_has_required_keys(monkeypatch):
    monkeypatch.setattr("app.webmap_builder._catalog_lookup", lambda: {})

    webmap = build_webmap_json(sample_recipe())

    assert webmap["version"] == "2.31"
    assert webmap["authoringApp"] == "AutoMap"
    assert webmap["authoringAppVersion"] == "0.4"
    assert "operationalLayers" in webmap
    assert "baseMap" in webmap
    assert "initialState" in webmap
    assert webmap["autoMapValidation"]["is_valid"] is True


def test_operational_layer_preserves_urls_and_definition_expression():
    selected = layer("municipal", "MunicipalDistrict", "jurisdiction", role="jurisdiction_filter")
    filter_plan = {
        "draft_where_clause": "DISTRICT = 'CITY OF CONCORD'",
        "confidence_score": 0.5,
        "needs_review": True,
        "review_reason": "Confirm the district value.",
    }

    operational_layer = build_operational_layer(selected, filter_plan)

    assert operational_layer["url"] == selected["layer_url"]
    assert operational_layer["layerUrl"] == selected["layer_url"]
    assert operational_layer["serviceUrl"] == selected["service_url"]
    assert operational_layer["layerDefinition"]["definitionExpression"] == "DISTRICT = 'CITY OF CONCORD'"
    assert operational_layer["autoMapDefinitionSource"] == "filter_plan"
    assert operational_layer["autoMapNeedsReview"] is True


def test_order_layers_bottom_to_top():
    layers = [
        layer("roads", "Road Centerlines", "transportation", geometry_type="esriGeometryPolyline"),
        layer("flood100", "FloodPlain100year", "flood", role="constraint_overlay"),
        layer("parcels", "Tax Parcels", "parcel", role="base_layer"),
        layer("municipal", "MunicipalDistrict", "jurisdiction", role="jurisdiction_filter"),
        layer("schools", "Elementary School District", "schools", role="school_boundary_layer"),
    ]

    assert [item["layer_key"] for item in order_layers(layers)] == [
        "municipal",
        "parcels",
        "schools",
        "flood100",
        "roads",
    ]


def test_flood_renderer_uses_transparent_blue_fill():
    renderer = build_renderer(layer("flood100", "FloodPlain100year", "flood"))

    assert renderer["type"] == "simple"
    assert renderer["symbol"]["color"][2] == 243
    assert renderer["symbol"]["color"][3] < 120


def test_zoning_renderer_preserves_review_warning_when_field_needs_review():
    selected = layer("zoning", "Concord Zoning", "zoning", role="constraint_overlay")

    operational_layer = build_operational_layer(
        selected,
        {
            "selected_field": None,
            "draft_where_clause": None,
            "confidence_score": 0.2,
            "needs_review": True,
            "review_reason": "Confirm which zoning codes count as commercial.",
        },
    )

    assert operational_layer["autoMapNeedsReview"] is True
    assert any("zoning" in warning.lower() for warning in operational_layer["autoMapReviewWarnings"])


def test_low_filter_confidence_without_expression_does_not_force_review():
    selected = layer("parcels", "Tax Parcels", "parcel", role="base_layer")

    operational_layer = build_operational_layer(
        selected,
        {
            "selected_field": "PIN14",
            "draft_where_clause": None,
            "confidence_score": 0.2,
            "needs_review": False,
            "review_reason": None,
        },
    )

    assert operational_layer["autoMapNeedsReview"] is False
    assert operational_layer["autoMapReviewWarnings"] == []


def test_popup_info_uses_real_field_metadata():
    popup = build_popup_info(
        layer(
            "parcels",
            "Tax Parcels",
            "parcel",
            fields=[
                {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID"},
                {"name": "PIN14", "type": "esriFieldTypeString", "alias": "Parcel PIN"},
            ],
        )
    )

    assert popup["fieldInfos"] == [{"fieldName": "PIN14", "label": "Parcel PIN", "visible": True}]


def test_safe_filename_removes_punctuation_and_spaces():
    assert make_safe_filename("Show commercial zoning around Concord!") == "show_commercial_zoning_around_concord.json"


def test_validation_catches_missing_url_and_unsourced_definition_expression():
    webmap = {
        "operationalLayers": [
            {
                "title": "Tax Parcels",
                "autoMapLayerKey": "parcels",
                "layerDefinition": {"definitionExpression": "PIN14 = '1'"},
            }
        ],
        "baseMap": {},
        "spatialReference": {},
        "version": "2.31",
        "authoringApp": "AutoMap",
        "authoringAppVersion": "0.4",
        "applicationProperties": {},
        "initialState": {"viewpoint": {"targetGeometry": {}}},
    }

    validation = validate_webmap_json(webmap)

    assert validation["is_valid"] is False
    assert any("missing url" in error.lower() for error in validation["errors"])
    assert any("filter_plan" in error for error in validation["errors"])


def test_draft_contains_no_portal_publish_or_login_keys(monkeypatch):
    monkeypatch.setattr("app.webmap_builder._catalog_lookup", lambda: {})
    webmap = build_webmap_json(sample_recipe())
    serialized = json.dumps(webmap).lower()

    assert "portalitem" not in serialized
    assert "portalurl" not in serialized
    assert "token" not in serialized
    assert "password" not in serialized
