import json
from pathlib import Path

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


def approval_receipt(*, final_publish_ready=True, block_reasons=None):
    return {
        "reviewer_name": "Reviewer",
        "reviewer_role": "GIS Reviewer",
        "decision": "approved" if final_publish_ready else "needs_changes",
        "publish_ready_requested": True,
        "final_publish_ready": final_publish_ready,
        "approved_at": "2026-06-15T00:00:00+00:00",
        "block_reasons": block_reasons or [],
        "reviewer_notes": ["Reviewed layers and warning status."],
        "accepted_risks": ["Private draft only."],
        "local_approval_only": True,
        "no_arcgis_item_created": True,
        "cfs_database_not_touched": True,
    }


def approved_warnings(*, final_publish_ready=True, block_reasons=None):
    return {
        "active": {} if final_publish_ready else {"publishing_blockers": block_reasons or ["Needs changes."]},
        "block_reasons": block_reasons or [],
        "final_publish_ready": final_publish_ready,
        "resolved_warnings": [],
        "accepted_warnings": [],
        "kept_non_blocking_warnings": [],
    }


def write_approved_packet(tmp_path, *, final_publish_ready=True, block_reasons=None):
    packet = tmp_path / "approved_packet"
    packet.mkdir()
    (packet / "approved_recipe.json").write_text(json.dumps(adjusted_recipe()), encoding="utf-8")
    (packet / "approved_webmap.json").write_text(json.dumps(adjusted_webmap()), encoding="utf-8")
    (packet / "approval_file.json").write_text(json.dumps({"decision": "approved"}), encoding="utf-8")
    (packet / "approval_receipt.json").write_text(
        json.dumps(approval_receipt(final_publish_ready=final_publish_ready, block_reasons=block_reasons)),
        encoding="utf-8",
    )
    (packet / "approved_warnings.json").write_text(
        json.dumps(approved_warnings(final_publish_ready=final_publish_ready, block_reasons=block_reasons)),
        encoding="utf-8",
    )
    return packet


def allow_real_publish_env(monkeypatch):
    monkeypatch.setenv("ARCGIS_PUBLISH_ENV", "dev")
    monkeypatch.setenv("AUTOMAP_ALLOW_REAL_PUBLISH", "true")
    monkeypatch.setenv("AUTOMAP_PUBLISH_DRY_RUN", "false")
    monkeypatch.setenv("ARCGIS_USERNAME", "user")
    monkeypatch.setenv("ARCGIS_PASSWORD", "configured-for-test")
    monkeypatch.setenv("ARCGIS_TARGET_FOLDER", "AutoMap Drafts")


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
    properties = build_item_properties(adjusted_recipe(), adjusted_webmap(), approval_receipt(), approved_warnings())

    assert properties["title"].startswith("AutoMap Draft -")
    assert properties["type"] == "Web Map"
    assert properties["tags"] == PUBLISH_TAGS
    assert properties["snippet"] == "Draft web map generated by AutoMap. Requires GIS review before official use."
    assert "Reviewed layers and warning status." in properties["description"]
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
    assert any("Raw review packets" in error for error in validation["errors"])


def test_real_publish_blocked_without_approved_packet(monkeypatch, tmp_path):
    allow_real_publish_env(monkeypatch)
    packet = write_adjusted_packet(tmp_path)

    def fail_connect(*_args, **_kwargs):
        raise AssertionError("real publish must not connect for adjusted packets")

    monkeypatch.setattr("app.arcgis_publisher.connect_to_arcgis", fail_connect)
    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=True)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert result["real_publish_attempted"] is False
    assert any("approved packet" in reason for reason in result["block_reasons"])


def test_real_publish_blocked_if_final_publish_ready_false(monkeypatch, tmp_path):
    allow_real_publish_env(monkeypatch)
    packet = write_approved_packet(tmp_path, final_publish_ready=False, block_reasons=["Needs more review."])

    def fail_connect(*_args, **_kwargs):
        raise AssertionError("real publish must not connect when approval blocks remain")

    monkeypatch.setattr("app.arcgis_publisher.connect_to_arcgis", fail_connect)
    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=True)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert result["real_publish_attempted"] is False
    assert any("final_publish_ready" in reason for reason in result["block_reasons"])


def test_real_publish_blocked_without_confirm(monkeypatch, tmp_path):
    allow_real_publish_env(monkeypatch)
    packet = write_approved_packet(tmp_path)

    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=False)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert any("--confirm-publish" in reason for reason in result["block_reasons"])


def test_real_publish_blocked_when_allow_flag_false(monkeypatch, tmp_path):
    allow_real_publish_env(monkeypatch)
    monkeypatch.setenv("AUTOMAP_ALLOW_REAL_PUBLISH", "false")
    packet = write_approved_packet(tmp_path)

    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=True)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert any("AUTOMAP_ALLOW_REAL_PUBLISH" in reason for reason in result["block_reasons"])


def test_real_publish_blocked_when_env_dry_run_true(monkeypatch, tmp_path):
    allow_real_publish_env(monkeypatch)
    monkeypatch.setenv("AUTOMAP_PUBLISH_DRY_RUN", "true")
    packet = write_approved_packet(tmp_path)

    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=True)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert any("AUTOMAP_PUBLISH_DRY_RUN" in reason for reason in result["block_reasons"])


def test_real_arcgis_calls_are_mocked(monkeypatch, tmp_path):
    allow_real_publish_env(monkeypatch)
    packet = write_approved_packet(tmp_path)

    class FakeItem:
        id = "abc123"
        url = "https://example.com/items/abc123"

        def share(self, *_args, **_kwargs):
            raise AssertionError("publisher must not share items")

        def update(self, *_args, **_kwargs):
            raise AssertionError("publisher must not update existing items")

        def delete(self, *_args, **_kwargs):
            raise AssertionError("publisher must not delete items")

    class FakeContent:
        def __init__(self):
            self.add_calls = []
            self.create_folder_calls = []

        def add(self, **kwargs):
            self.add_calls.append(kwargs)
            return FakeItem()

        def create_folder(self, folder_name):
            self.create_folder_calls.append(folder_name)
            return {"title": folder_name}

    class FakeUsers:
        me = type("FakeUser", (), {"folders": []})()

    class FakeGIS:
        def __init__(self):
            self.content = FakeContent()
            self.users = FakeUsers()

    fake_gis = FakeGIS()
    monkeypatch.setattr("app.arcgis_publisher.connect_to_arcgis", lambda settings: fake_gis)

    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=True)

    assert result["status"] == "published_private_draft"
    assert result["real_publish_attempted"] is True
    assert result["created_item"] is True
    assert result["item_id"] == "abc123"
    assert result["item_url"] == "https://example.com/items/abc123"
    assert result["shared_public"] is False
    assert result["shared_organization"] is False
    assert result["overwrite_used"] is False
    assert result["delete_used"] is False
    assert fake_gis.content.add_calls
    assert fake_gis.content.create_folder_calls == ["AutoMap Drafts"]
    added = fake_gis.content.add_calls[0]
    assert added["folder"] == "AutoMap Drafts"
    assert added["item_properties"]["title"].startswith("AutoMap Draft -")
    assert added["item_properties"]["type"] == "Web Map"
    receipt_text = (packet / "publish_receipt.json").read_text(encoding="utf-8")
    assert "configured-for-test" not in receipt_text
    receipt = json.loads(receipt_text)
    assert receipt["created_item"] is True
    assert receipt["item_id"] == "abc123"
    assert receipt["shared_public"] is False
    assert receipt["shared_organization"] is False
    assert receipt["overwrite_used"] is False
    assert receipt["delete_used"] is False


def test_load_publish_settings_defaults_to_dry_run(monkeypatch):
    monkeypatch.delenv("AUTOMAP_PUBLISH_DRY_RUN", raising=False)
    monkeypatch.delenv("AUTOMAP_ALLOW_REAL_PUBLISH", raising=False)
    monkeypatch.delenv("ARCGIS_PUBLISH_ENV", raising=False)
    settings = load_arcgis_publish_settings(load_env_file=False)

    assert settings.dry_run is True
    assert settings.allow_real_publish is False
    assert settings.publish_env == "dev"
    assert settings.portal_url == "https://www.arcgis.com"


def test_real_publish_requires_confirm(monkeypatch, tmp_path):
    allow_real_publish_env(monkeypatch)
    packet = write_approved_packet(tmp_path)

    result = publish_webmap_draft(packet, dry_run=False, confirm_publish=False)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert any("--confirm-publish" in reason for reason in result["block_reasons"])
