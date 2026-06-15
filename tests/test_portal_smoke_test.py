import json

from app.portal_smoke_test import (
    run_publish_smoke_test,
    validate_smoke_test_prerequisites,
)


def approved_recipe():
    return {
        "map_title": "Concord Flood Exposure Draft",
        "selected_layers": [
            {
                "layer_key": "flood100",
                "layer_name": "FloodPlain100year",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
            }
        ],
    }


def approved_webmap():
    return {
        "title": "Concord Flood Exposure Draft",
        "operationalLayers": [
            {
                "title": "FloodPlain100year",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
                "autoMapLayerKey": "flood100",
            }
        ],
    }


def approval_receipt(*, final_publish_ready=True):
    return {
        "reviewer_name": "Reviewer",
        "decision": "approved" if final_publish_ready else "needs_changes",
        "publish_ready_requested": True,
        "final_publish_ready": final_publish_ready,
        "block_reasons": [] if final_publish_ready else ["Needs more review."],
        "reviewer_notes": ["Reviewed locally."],
    }


def approved_warnings(*, final_publish_ready=True):
    return {
        "active": {} if final_publish_ready else {"publishing_blockers": ["Needs more review."]},
        "block_reasons": [] if final_publish_ready else ["Needs more review."],
        "final_publish_ready": final_publish_ready,
    }


def write_approved_packet(tmp_path, *, final_publish_ready=True):
    packet = tmp_path / "approved_packet"
    packet.mkdir()
    (packet / "approved_recipe.json").write_text(json.dumps(approved_recipe()), encoding="utf-8")
    (packet / "approved_webmap.json").write_text(json.dumps(approved_webmap()), encoding="utf-8")
    (packet / "approval_file.json").write_text(json.dumps({"decision": "approved"}), encoding="utf-8")
    (packet / "approval_receipt.json").write_text(
        json.dumps(approval_receipt(final_publish_ready=final_publish_ready)),
        encoding="utf-8",
    )
    (packet / "approved_warnings.json").write_text(
        json.dumps(approved_warnings(final_publish_ready=final_publish_ready)),
        encoding="utf-8",
    )
    return packet


def write_adjusted_packet(tmp_path):
    packet = tmp_path / "adjusted_packet"
    packet.mkdir()
    (packet / "adjusted_recipe.json").write_text(json.dumps(approved_recipe()), encoding="utf-8")
    (packet / "adjusted_webmap.json").write_text(json.dumps(approved_webmap()), encoding="utf-8")
    (packet / "applied_adjustments.json").write_text(json.dumps({}), encoding="utf-8")
    (packet / "adjusted_warnings.json").write_text(json.dumps({"publish_ready": True, "active": {}}), encoding="utf-8")
    return packet


def allow_smoke_env(monkeypatch):
    monkeypatch.setenv("ARCGIS_PUBLISH_ENV", "dev")
    monkeypatch.setenv("AUTOMAP_ALLOW_REAL_PUBLISH", "true")
    monkeypatch.setenv("AUTOMAP_PUBLISH_DRY_RUN", "false")
    monkeypatch.setenv("ARCGIS_PORTAL_URL", "https://www.arcgis.com")
    monkeypatch.setenv("ARCGIS_USERNAME", "user")
    monkeypatch.setenv("ARCGIS_PASSWORD", "configured-for-test")
    monkeypatch.setenv("ARCGIS_TARGET_FOLDER", "AutoMap Drafts")


def test_smoke_test_dry_run_creates_no_arcgis_item(monkeypatch, tmp_path):
    packet = write_approved_packet(tmp_path)

    def fail_connect(*_args, **_kwargs):
        raise AssertionError("dry-run smoke test must not connect to ArcGIS")

    monkeypatch.setattr("app.portal_smoke_test.connect_to_arcgis", fail_connect)
    result = run_publish_smoke_test(packet, confirm_publish=False)

    assert result["dry_run"] is True
    assert result["real_publish_attempted"] is False
    assert result["item_created"] is False
    assert (packet / "smoke_test_receipt.json").exists()


def test_smoke_test_without_confirm_remains_dry_run(monkeypatch, tmp_path):
    allow_smoke_env(monkeypatch)
    packet = write_approved_packet(tmp_path)

    def fail_real_publish(*_args, **_kwargs):
        raise AssertionError("smoke test without confirm must not real-publish")

    monkeypatch.setattr("app.portal_smoke_test.publish_one_private_draft_item", fail_real_publish)

    result = run_publish_smoke_test(packet)

    assert result["dry_run"] is True
    assert result["real_publish_attempted"] is False
    assert result["item_created"] is False


def test_real_smoke_test_blocked_without_env_flags(monkeypatch, tmp_path):
    packet = write_approved_packet(tmp_path)
    monkeypatch.delenv("AUTOMAP_ALLOW_REAL_PUBLISH", raising=False)
    monkeypatch.delenv("AUTOMAP_PUBLISH_DRY_RUN", raising=False)

    result = run_publish_smoke_test(packet, confirm_publish=True)

    assert result["blocked"] is True
    assert result["item_created"] is False
    assert result["real_publish_attempted"] is False
    assert result["block_reasons"]


def test_real_smoke_test_blocked_for_non_approved_packet(monkeypatch, tmp_path):
    allow_smoke_env(monkeypatch)
    packet = write_adjusted_packet(tmp_path)

    result = run_publish_smoke_test(packet, confirm_publish=True)

    assert result["blocked"] is True
    assert result["item_created"] is False
    assert any("approved packet" in reason.lower() for reason in result["block_reasons"])


def test_dry_run_smoke_test_blocked_for_non_approved_packet(tmp_path):
    packet = write_adjusted_packet(tmp_path)

    result = run_publish_smoke_test(packet, confirm_publish=False)

    assert result["dry_run"] is True
    assert result["blocked"] is True
    assert result["item_created"] is False
    assert any("approved packet" in reason.lower() for reason in result["block_reasons"])


def test_real_smoke_test_blocked_when_final_publish_ready_false(monkeypatch, tmp_path):
    allow_smoke_env(monkeypatch)
    packet = write_approved_packet(tmp_path, final_publish_ready=False)

    result = run_publish_smoke_test(packet, confirm_publish=True)

    assert result["blocked"] is True
    assert result["item_created"] is False
    assert any("final_publish_ready" in reason for reason in result["block_reasons"])


def test_validate_smoke_test_prerequisites_accepts_ready_approved_packet(tmp_path):
    packet = write_approved_packet(tmp_path)

    validation = validate_smoke_test_prerequisites(packet)

    assert validation["is_valid"] is True
    assert validation["errors"] == []


def test_mocked_real_smoke_test_creates_exactly_one_private_item(monkeypatch, tmp_path):
    allow_smoke_env(monkeypatch)
    packet = write_approved_packet(tmp_path)

    class FakeItem:
        id = "abc123"
        url = "https://example.com/items/abc123"
        title = "AutoMap Draft - Concord Flood Exposure Draft"
        type = "Web Map"
        access = "private"
        tags = ["AutoMap", "Draft", "GIS Request Engine", "Cabarrus County", "Human Review Required"]
        shared_with = {"everyone": False, "org": False, "groups": []}

        def get_data(self):
            return approved_webmap()

        def share(self, *_args, **_kwargs):
            raise AssertionError("smoke test must not share items")

        def update(self, *_args, **_kwargs):
            raise AssertionError("smoke test must not update existing items")

        def delete(self, *_args, **_kwargs):
            raise AssertionError("smoke test must not delete items")

    class FakeContent:
        def __init__(self):
            self.add_calls = []
            self.item = None

        def add(self, **kwargs):
            self.add_calls.append(kwargs)
            self.item = FakeItem()
            return self.item

        def create_folder(self, folder_name):
            return {"title": folder_name}

        def get(self, item_id):
            assert item_id == "abc123"
            return self.item or FakeItem()

    class FakeUsers:
        me = type("FakeUser", (), {"folders": []})()

    class FakeGIS:
        def __init__(self):
            self.content = FakeContent()
            self.users = FakeUsers()

    fake_gis = FakeGIS()
    monkeypatch.setattr("app.arcgis_publisher.connect_to_arcgis", lambda settings: fake_gis)
    monkeypatch.setattr("app.portal_smoke_test.connect_to_arcgis", lambda settings: fake_gis)

    result = run_publish_smoke_test(packet, confirm_publish=True)

    assert result["blocked"] is False
    assert result["real_publish_attempted"] is True
    assert result["item_created"] is True
    assert result["item_id"] == "abc123"
    assert result["verified_private"] is True
    assert result["verified_not_public"] is True
    assert result["verified_not_org_shared"] is True
    assert result["verified_layer_urls"] is True
    assert len(fake_gis.content.add_calls) == 1
    receipt_text = (packet / "smoke_test_receipt.json").read_text(encoding="utf-8").lower()
    assert "configured-for-test" not in receipt_text
    assert "manual cleanup" in receipt_text
    assert "cfs_dev" not in receipt_text
