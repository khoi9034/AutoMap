import json
import os
from pathlib import Path

from app import packet_index


def sample_recipe(title="Concord Flood Preview"):
    return {
        "map_title": title,
        "user_intent": "Show parcels in Concord that are in the 100-year floodplain.",
        "parsed_request": {"raw_prompt": "Show parcels in Concord that are in the 100-year floodplain."},
        "missing_data_needed": ["permits"],
        "review_reasons": ["Human review required before publishing."],
    }


def sample_webmap(title="Concord Flood Preview"):
    return {
        "title": title,
        "initialState": {
            "viewpoint": {
                "targetGeometry": {
                    "xmin": -80.8,
                    "ymin": 35.1,
                    "xmax": -80.4,
                    "ymax": 35.6,
                    "spatialReference": {"wkid": 4326},
                }
            }
        },
        "operationalLayers": [
            {
                "id": "automap_flood",
                "title": "FloodPlain100year",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer/2",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer/2",
                "layerId": 2,
                "visibility": True,
                "opacity": 0.45,
                "showLegend": True,
                "layerDefinition": {"definitionExpression": "ZONE = 'AE'"},
                "autoMapRole": "constraint_overlay",
                "autoMapLayerKey": "cabarrus_new_flood_hazard_areas_2_floodplain100year",
                "autoMapSourceStatus": "active",
                "autoMapSourcePriority": 1,
                "autoMapConfidence": 0.93,
            }
        ],
        "autoMapWarnings": ["Draft review only."],
    }


def write_review_packet(root: Path, name="review_one", title="Concord Flood Preview") -> Path:
    folder = root / "review_packets" / name
    folder.mkdir(parents=True)
    (folder / "recipe.json").write_text(json.dumps(sample_recipe(title)), encoding="utf-8")
    (folder / "webmap.json").write_text(json.dumps(sample_webmap(title)), encoding="utf-8")
    (folder / "warnings.json").write_text(json.dumps({"preview_warnings": ["Draft review only."]}), encoding="utf-8")
    (folder / "review.html").write_text("<html>review</html>", encoding="utf-8")
    return folder


def write_adjusted_packet(root: Path, name="adjusted_one", title="Adjusted Flood Preview") -> Path:
    folder = root / "review_packets_adjusted" / name
    folder.mkdir(parents=True)
    (folder / "adjusted_recipe.json").write_text(json.dumps(sample_recipe(title)), encoding="utf-8")
    (folder / "adjusted_webmap.json").write_text(json.dumps(sample_webmap(title)), encoding="utf-8")
    (folder / "adjusted_warnings.json").write_text(
        json.dumps({"active": {"publishing_blockers": []}, "publish_ready": True}),
        encoding="utf-8",
    )
    (folder / "adjusted_review.html").write_text("<html>adjusted</html>", encoding="utf-8")
    return folder


def write_approved_packet(root: Path, name="approved_one", title="Approved Flood Preview") -> Path:
    folder = root / "review_packets_approved" / name
    folder.mkdir(parents=True)
    recipe = sample_recipe(title)
    recipe["reviewer_approval"] = {"final_publish_ready": True, "local_approval_only": True}
    (folder / "approved_recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
    webmap = sample_webmap(title)
    webmap["autoMapApproval"] = {"finalPublishReady": True, "localApprovalOnly": True}
    (folder / "approved_webmap.json").write_text(json.dumps(webmap), encoding="utf-8")
    (folder / "approved_warnings.json").write_text(
        json.dumps({"active": {}, "final_publish_ready": True}),
        encoding="utf-8",
    )
    (folder / "approval_receipt.json").write_text(
        json.dumps({"final_publish_ready": True, "block_reasons": []}),
        encoding="utf-8",
    )
    (folder / "approved_review.html").write_text("<html>approved</html>", encoding="utf-8")
    return folder


def set_tree_mtime(path: Path, timestamp: int) -> None:
    os.utime(path, (timestamp, timestamp))
    for item in path.iterdir():
        os.utime(item, (timestamp, timestamp))


def test_packet_discovery_and_latest_packet(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    review = write_review_packet(tmp_path, name="older_review")
    adjusted = write_adjusted_packet(tmp_path, name="newer_adjusted")
    set_tree_mtime(review, 1000)
    set_tree_mtime(adjusted, 2000)

    review_packets = packet_index.list_review_packets()
    adjusted_packets = packet_index.list_adjusted_packets()
    latest = packet_index.find_latest_packet()

    assert review_packets[0]["packet_id"] == "older_review"
    assert adjusted_packets[0]["packet_id"] == "newer_adjusted"
    assert latest["packet_id"] == "newer_adjusted"
    assert latest["preview_url"] == "/preview/newer_adjusted"


def test_resolve_packet_id(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    folder = write_review_packet(tmp_path, name="packet_by_id")

    resolved = packet_index.resolve_packet_id("packet_by_id")

    assert resolved == folder.resolve()


def test_preview_config_supports_approved_packets(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_approved_packet(tmp_path, name="approved_packet")

    config = packet_index.build_preview_config("approved_packet")

    assert config["draft_status"] == "approved_review"
    assert config["publish_ready"] is True
    assert config["webmap_path"] == "outputs/review_packets_approved/approved_packet/approved_webmap.json"


def test_preview_config_preserves_mapserver_sublayer(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_review_packet(tmp_path, name="mapserver_packet")

    config = packet_index.build_preview_config("mapserver_packet")
    layer = config["operational_layers"][0]

    assert layer["preview_type"] == "map_image_sublayer"
    assert layer["service_url"].endswith("/MapServer")
    assert layer["layer_id"] == 2
    assert layer["definition_expression"] == "ZONE = 'AE'"


def test_preview_config_redacts_secret_markers(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_review_packet(tmp_path, name="secret_packet", title="DATABASE_URL should not leak")

    config = packet_index.build_preview_config("secret_packet")
    serialized = json.dumps(config).lower()

    assert "database_url" not in serialized
    assert ".env" not in serialized
    assert "password" not in serialized


def test_preview_config_supports_generated_webmap_path(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    webmap_path = tmp_path / "webmaps" / "draft.json"
    webmap_path.parent.mkdir(parents=True)
    webmap_path.write_text(json.dumps(sample_webmap("Generated WebMap")), encoding="utf-8")

    config = packet_index.build_preview_config("outputs/webmaps/draft.json")

    assert config["draft_status"] == "webmap_draft"
    assert config["map_title"] == "Generated WebMap"
    assert config["webmap_path"] == "outputs/webmaps/draft.json"


def test_preview_config_has_no_cfs_references(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_review_packet(tmp_path, name="clean_packet")

    serialized = json.dumps(packet_index.build_preview_config("clean_packet")).lower()

    assert "cfs" not in serialized
    assert "cfs_dev" not in serialized


def test_packet_index_includes_approval_and_dry_run_receipts(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    approved = write_approved_packet(tmp_path, name="receipt_packet")
    (approved / "publish_receipt.json").write_text(
        json.dumps(
            {
                "status": "dry_run",
                "published": False,
                "created_item": False,
                "real_publish_attempted": False,
            }
        ),
        encoding="utf-8",
    )
    (approved / "smoke_test_receipt.json").write_text(
        json.dumps({"dry_run": True, "item_created": False, "blocked": False}),
        encoding="utf-8",
    )

    packet = packet_index.list_approved_packets()[0]

    assert packet["final_publish_ready"] is True
    assert packet["latest_publish_receipt"]["exists"] is True
    assert packet["latest_publish_receipt"]["status"] == "dry_run"
    assert packet["latest_publish_receipt"]["real_publish_attempted"] is False
    assert packet["latest_smoke_test_receipt"]["exists"] is True
    assert packet["latest_smoke_test_receipt"]["item_created"] is False
