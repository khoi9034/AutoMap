import os

import pytest

from app.arcgis_rest_inspector import inspect_layer


def test_inspect_layer_extracts_group_and_feature_flags(monkeypatch):
    def fake_fetch_json(_url):
        return {
            "id": 0,
            "name": "FloodPlain100year",
            "type": "Feature Layer",
            "geometryType": "esriGeometryPolygon",
            "fields": [{"name": "OBJECTID", "type": "esriFieldTypeOID"}],
            "capabilities": "Map,Query,Data",
            "advancedQueryCapabilities": {"supportsStatistics": True},
        }

    monkeypatch.setattr("app.arcgis_rest_inspector.fetch_json", fake_fetch_json)

    layer = inspect_layer("https://example.com/MapServer/0")

    assert layer["layer_id"] == 0
    assert layer["is_feature_layer"] is True
    assert layer["is_group_layer"] is False
    assert layer["capabilities"] == ["Map", "Query", "Data"]
    assert layer["supports_statistics"] is True


@pytest.mark.skipif(
    os.getenv("AUTOMAP_RUN_LIVE_REST_TESTS") != "true",
    reason="Live REST tests are skipped unless AUTOMAP_RUN_LIVE_REST_TESTS=true.",
)
def test_live_rest_layer_metadata_is_available():
    layer = inspect_layer(
        "https://location.cabarruscounty.us/arcgisservices/rest/services/"
        "OpenData/Flood_Hazard_Areas/MapServer/0"
    )

    assert layer["layer_name"]
