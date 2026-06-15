import json
from pathlib import Path
from uuid import uuid4

import pytest
import yaml
from app.approval_engine import (
    apply_approval_to_adjusted_packet,
    create_approval_template,
    evaluate_publish_readiness,
    list_approval_history,
    load_approval_file,
    record_approval_history,
    validate_approval_file,
    validate_approved_packet,
)
from app.arcgis_publisher import publish_webmap_draft
from app.config import get_settings


def adjusted_recipe(*, missing_data=None):
    return {
        "map_title": "Concord Flood Exposure Draft",
        "user_intent": "Show parcels in Concord that are in the 100-year floodplain.",
        "selected_layers": [
            {
                "layer_key": "flood100",
                "layer_name": "FloodPlain100year",
                "role": "constraint_overlay",
                "source_status": "active",
                "source_priority": 1,
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
                "service_url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer",
            }
        ],
        "missing_data_needed": missing_data or [],
        "review_reasons": [],
    }


def adjusted_webmap():
    return {
        "title": "Concord Flood Exposure Draft",
        "operationalLayers": [
            {
                "title": "FloodPlain100year",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood/MapServer/2",
                "autoMapLayerKey": "flood100",
                "autoMapRole": "constraint_overlay",
                "visibility": True,
                "opacity": 0.45,
            }
        ],
    }


def adjusted_warnings(active=None):
    return {
        "active": active
        if active is not None
        else {
            "layer_selection_warnings": [],
            "filter_warnings": [],
            "symbology_warnings": [],
            "missing_data_warnings": [],
            "historical_data_warnings": [],
            "publishing_blockers": ["Review and approval are required before any future publishing step."],
        },
        "publish_ready_requested": False,
        "publish_ready": False,
    }


def write_adjusted_packet(tmp_path: Path, *, missing_data=None, active=None) -> Path:
    packet = tmp_path / "adjusted_packet"
    packet.mkdir()
    (packet / "adjusted_recipe.json").write_text(json.dumps(adjusted_recipe(missing_data=missing_data)), encoding="utf-8")
    (packet / "adjusted_webmap.json").write_text(json.dumps(adjusted_webmap()), encoding="utf-8")
    (packet / "applied_adjustments.json").write_text(json.dumps({"adjustments": {}}), encoding="utf-8")
    (packet / "adjusted_warnings.json").write_text(json.dumps(adjusted_warnings(active=active)), encoding="utf-8")
    return packet


def approved_payload(packet: Path) -> dict:
    template_path = create_approval_template(packet)
    return load_approval_file(template_path)


def require_database_url():
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("AutoMap DATABASE_URL is not configured.")


def test_approval_template_creation_does_not_mutate_adjusted_packet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)

    template_path = create_approval_template(packet)

    assert template_path.exists()
    assert template_path.parent.name == "approval_templates"
    assert template_path.parent.parent.name == "outputs"
    assert not (packet / "approval.template.yaml").exists()


def test_approval_yaml_loading_and_validation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    template_path = create_approval_template(packet)

    approval = load_approval_file(template_path)
    validation = validate_approval_file(approval)

    assert approval["decision"] == "approved"
    assert approval["publish_ready_requested"] is True
    assert validation["is_valid"] is True


def test_decision_approved_can_make_publish_ready_when_warnings_accepted(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval = approved_payload(packet)
    recipe = json.loads((packet / "adjusted_recipe.json").read_text(encoding="utf-8"))
    warnings = json.loads((packet / "adjusted_warnings.json").read_text(encoding="utf-8"))

    readiness = evaluate_publish_readiness(recipe, warnings, approval, [])

    assert readiness["final_publish_ready"] is True
    assert readiness["block_reasons"] == []
    assert readiness["accepted_warnings"]


def test_needs_changes_keeps_publish_ready_false(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval = approved_payload(packet)
    approval["decision"] = "needs_changes"

    readiness = evaluate_publish_readiness(adjusted_recipe(), adjusted_warnings(), approval, [])

    assert readiness["final_publish_ready"] is False
    assert "Reviewer decision is not approved." in readiness["block_reasons"]


def test_rejected_keeps_publish_ready_false(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval = approved_payload(packet)
    approval["decision"] = "rejected"

    readiness = evaluate_publish_readiness(adjusted_recipe(), adjusted_warnings(), approval, [])

    assert readiness["final_publish_ready"] is False
    assert "Reviewer decision is not approved." in readiness["block_reasons"]


def test_unresolved_blockers_keep_publish_ready_false():
    approval = {
        "reviewer_name": "Reviewer",
        "reviewer_role": "GIS Reviewer",
        "decision": "approved",
        "publish_ready_requested": True,
        "warning_resolutions": [],
        "reviewer_notes": [],
        "accepted_risks": [],
        "missing_data_decisions": [],
    }

    readiness = evaluate_publish_readiness(adjusted_recipe(), adjusted_warnings(), approval, [])

    assert readiness["final_publish_ready"] is False
    assert any("Unresolved warning" in reason for reason in readiness["block_reasons"])


def test_missing_data_without_reviewer_decision_blocks_publish_ready(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path, missing_data=["current planning case layer"])
    approval = approved_payload(packet)
    approval["missing_data_decisions"] = []

    recipe = adjusted_recipe(missing_data=["current planning case layer"])
    readiness = evaluate_publish_readiness(recipe, adjusted_warnings(), approval, [])

    assert readiness["final_publish_ready"] is False
    assert any("Missing data requires reviewer decision" in reason for reason in readiness["block_reasons"])


def test_apply_approval_writes_and_validates_approved_packet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval_path = create_approval_template(packet)

    approved_path = apply_approval_to_adjusted_packet(packet, approval_path)
    validation = validate_approved_packet(approved_path)
    receipt = json.loads((approved_path / "approval_receipt.json").read_text(encoding="utf-8"))

    assert validation["is_valid"] is True
    assert validation["final_publish_ready"] is True
    assert receipt["local_approval_only"] is True
    assert receipt["no_arcgis_item_created"] is True
    assert receipt["cfs_database_not_touched"] is True
    assert (approved_path / "approved_review.html").exists()
    assert not (packet / "approved_webmap.json").exists()


def test_approved_packet_validation_rejects_missing_urls(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval_path = create_approval_template(packet)
    approved_path = apply_approval_to_adjusted_packet(packet, approval_path)
    webmap_path = approved_path / "approved_webmap.json"
    webmap = json.loads(webmap_path.read_text(encoding="utf-8"))
    webmap["operationalLayers"][0].pop("url")
    webmap_path.write_text(json.dumps(webmap), encoding="utf-8")

    validation = validate_approved_packet(approved_path)

    assert validation["is_valid"] is False
    assert any("missing URL" in error for error in validation["errors"])


def test_approval_history_insert_works_when_database_configured():
    require_database_url()
    marker = f"pytest reviewer {uuid4()}"
    receipt = {
        "source_adjusted_packet": "outputs/review_packets_adjusted/test",
        "reviewer_name": marker,
        "reviewer_role": "GIS Reviewer",
        "decision": "approved",
        "publish_ready_requested": True,
        "final_publish_ready": True,
        "block_reasons": [],
        "reviewer_notes": ["pytest approval history insert"],
    }

    inserted = record_approval_history(receipt, "outputs/review_packets_approved/test")
    rows = list_approval_history(limit=25)

    assert inserted == 1
    assert any(row["reviewer_name"] == marker for row in rows)


def test_dry_run_publisher_accepts_approved_publish_ready_packet(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval_path = create_approval_template(packet)
    approved_path = apply_approval_to_adjusted_packet(packet, approval_path)

    def fail_connect(*_args, **_kwargs):
        raise AssertionError("dry-run must not connect to ArcGIS")

    monkeypatch.setattr("app.arcgis_publisher.connect_to_arcgis", fail_connect)
    result = publish_webmap_draft(approved_path, dry_run=True)

    assert result["status"] == "dry_run"
    assert result["created_item"] is False
    assert result["published"] is False
    assert result["validation"]["packet_type"] == "approved"
    assert (approved_path / "publish_receipt.json").exists()


def test_dry_run_publisher_blocks_approved_packet_when_not_ready(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval = approved_payload(packet)
    approval["decision"] = "needs_changes"
    approval_path = tmp_path / "approval_needs_changes.yaml"
    approval_path.write_text(yaml.safe_dump(approval, sort_keys=False), encoding="utf-8")
    approved_path = apply_approval_to_adjusted_packet(packet, approval_path)

    result = publish_webmap_draft(approved_path, dry_run=True)

    assert result["status"] == "blocked"
    assert result["created_item"] is False
    assert any("final_publish_ready" in error for error in result["validation"]["errors"])


def test_no_secrets_or_protected_database_name_in_approved_packet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    packet = write_adjusted_packet(tmp_path)
    approval_path = create_approval_template(packet)
    approved_path = apply_approval_to_adjusted_packet(packet, approval_path)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in approved_path.iterdir()).lower()

    assert ".env" not in combined
    assert "database_url" not in combined
    assert "password" not in combined
    assert "token" not in combined
    assert "cfs_dev" not in combined
    assert "local_approval_only" in combined


def test_raw_review_packet_cannot_receive_approval_template(tmp_path):
    packet = tmp_path / "raw_review_packet"
    packet.mkdir()
    (packet / "recipe.json").write_text(json.dumps({}), encoding="utf-8")
    (packet / "webmap.json").write_text(json.dumps({}), encoding="utf-8")

    with pytest.raises(ValueError, match="Only adjusted packets"):
        create_approval_template(packet)
