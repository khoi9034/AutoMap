import json
from pathlib import Path

import pytest

from app.arcgis_publisher import (
    PUBLISH_TAGS,
    build_item_properties,
    check_arcgis_connection,
    load_arcgis_publish_settings,
    publish_webmap_draft,
    validate_publish_packet,
    write_publish_receipt,
)


def adjusted_recipe():
    return {
        "map_title": "Concord Flood Exposure Draft",
        "map_description": "Draft map showing parcels and 100-year floodplain context.",
        "selected_layers": [
            {
                "layer_key": "municipal",
                "layer_name": "MunicipalDistrict",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer/0",
            }
        ],
    }


def adjusted_webmap():
    return {
        "title": "Concord Flood Exposure Draft",
        "description": "Adjusted draft WebMap JSON.",
        "operationalLayers": [
            {
                "title": "MunicipalDistrict",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/MunicipalDistrict/MapServer/0",
                "autoMapLayerKey": "municipal",
                "layerDefinition": {
                    "definitionExpression": "DISTRICT = 'CITY OF CONCORD'",
                },
                "autoMapDefinitionSource": "human_adjustment",
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


def adjusted_warnings(*, publish_ready=True, active=None):
    return {
        "active": active if active is not None else {
            "layer_selection_warnings": [],
            "filter_warnings": [],
            "symbology_warnings": [],
            "missing_data_warnings": [],
            "historical_data_warnings": [],
            "publishing_blockers": [],
        },
        "reviewer_resolved": [],
        "publish_ready_requested": publish_ready,
        "publish_ready": publish_ready,
    }


def write_adjusted_packet(tmp_path, *, publish_ready=True, active=None):
    packet = tmp_path / "adjusted_packet"
    packet.mkdir()
    (packet / "adjusted_recipe.json").write_text(json.dumps(adjusted_recipe()), encoding="utf-8")
    (packet / "adjusted_webmap.json").write_text(json.dumps(adjusted_webmap()), encoding="utf-8")
    (packet / "applied_adjustments.json").write_text(json.dumps({"publication_status": "adjusted_draft_only_not_published"}), encoding="utf-8")
    (packet / "adjusted_warnings.json").write_text(json.dumps(adjusted_warnings(publish_ready=publish_ready, active=active)), encoding="utf-8")
    return packet


def test_dry_run_creates_no_arcgis_item(monkeypatch, tmp_path):
    packet = write_adjusted_packet(tmp_path)

    def fail_connect(*_args, **_kwargs):
        raise AssertionError("dry-run must not connect to ArcGIS")

    monkeypatch.setattr("app.arcgis_publisher.connect_to_arcgis", fail_connect)
    result = publish_webmap_draft(packet, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["created_item"] is False
    assert result["published"] is False
    assert result["shared_public"] is False
    assert result["shared_organization"] is False
    assert (packet / "publish_receipt.json").exists()


def test_publish_blocked_when_publish_ready_false(tmp_path):
    packet = write_adjusted_packet(tmp_path, publish_ready=False)

    result = publish_webmap_draft(packet, dry_run=True)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert any("publish_ready" in error for error in result["validation"]["errors"])


def test_publish_blocked_when_warnings_remain(tmp_path):
    active = adjusted_warnings()["active"]
    active["filter_warnings"] = ["Confirm zoning expression before publishing."]
    packet = write_adjusted_packet(tmp_path, active=active)

    validation = validate_publish_packet(packet)

    assert validation["is_valid"] is False
    assert any("unresolved warnings" in error for error in validation["errors"])


def test_missing_credentials_fail_safely(monkeypatch):
    monkeypatch.delenv("ARCGIS_USERNAME", raising=False)
    monkeypatch.delenv("ARCGIS_PASSWORD", raising=False)

    result = check_arcgis_connection()

    assert result["connected"] is False
    assert result["username_configured"] is False
    assert result["password_configured"] is False


def test_item_properties_are_private_draft_ready():
    properties = build_item_properties(adjusted_recipe(), adjusted_webmap())

    assert properties["title"].startswith("AutoMap Draft -")
    assert properties["type"] == "Web Map"
    assert properties["tags"] == PUBLISH_TAGS
    assert "Human Review Required" in properties["tags"]
    assert "Private" in properties["licenseInfo"]


def test_receipt_is_written_without_secrets(tmp_path):
    packet = write_adjusted_packet(tmp_path)
    result = {
        "status": "dry_run",
        "dry_run": True,
        "created_item": False,
        "published": False,
        "shared_public": False,
        "shared_organization": False,
        "overwrite_used": False,
        "delete_used": False,
        "title": "AutoMap Draft - Test",
    }

    receipt = write_publish_receipt(packet, result)
    receipt_text = receipt.read_text(encoding="utf-8").lower()

    assert receipt.exists()
    assert "password" not in receipt_text
    assert "token" not in receipt_text
    assert "cfs_dev" not in receipt_text


def test_only_adjusted_packets_can_be_published(tmp_path):
    packet = tmp_path / "raw_packet"
    packet.mkdir()
    (packet / "recipe.json").write_text("{}", encoding="utf-8")
    (packet / "webmap.json").write_text("{}", encoding="utf-8")

    validation = validate_publish_packet(packet)

    assert validation["is_valid"] is False
    assert any("Only adjusted packets" in error for error in validation["errors"])


def test_real_arcgis_calls_are_mocked(monkeypatch, tmp_path):
    packet = write_adjusted_packet(tmp_path)

    class FakeItem:
        id = "abc123"
        url = "https://example.com/items/abc123"

    class FakeContent:
        def __init__(self):
            self.add_calls = []

        def add(self, **kwargs):
            self.add_calls.append(kwargs)
            return FakeItem()

    class FakeGIS:
        def __init__(self):
            self.content = FakeContent()

    fake_gis = FakeGIS()
    monkeypatch.setattr("app.arcgis_publisher.connect_to_arcgis", lambda settings: fake_gis)
    monkeypatch.setenv("ARCGIS_USERNAME", "user")
    monkeypatch.setenv("ARCGIS_PASSWORD", "not-written-to-receipt")

    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=True)

    assert result["status"] == "published_private_draft"
    assert result["shared_public"] is False
    assert result["shared_organization"] is False
    assert result["overwrite_used"] is False
    assert result["delete_used"] is False
    assert fake_gis.content.add_calls
    receipt_text = (packet / "publish_receipt.json").read_text(encoding="utf-8")
    assert "not-written-to-receipt" not in receipt_text


def test_load_publish_settings_defaults_to_dry_run(monkeypatch):
    monkeypatch.delenv("AUTOMAP_PUBLISH_DRY_RUN", raising=False)
    settings = load_arcgis_publish_settings(load_env_file=False)

    assert settings.dry_run is True
    assert settings.portal_url == "https://www.arcgis.com"


def test_real_publish_requires_confirm(tmp_path):
    packet = write_adjusted_packet(tmp_path)

    with pytest.raises(ValueError, match="--confirm-publish"):
        publish_webmap_draft(packet, dry_run=False, confirm_publish=False)
