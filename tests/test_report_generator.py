import json
from pathlib import Path

from fastapi.testclient import TestClient

from app import report_generator
from app.report_generator import generate_report, get_report, list_reports, validate_report
from app.web_ui import create_app


def sample_recipe() -> dict:
    return {
        "map_title": "Concord Flood Report",
        "user_intent": "Show parcels in Concord that are in the 100-year floodplain.",
        "selected_layers": [
            {
                "layer_key": "tax_parcels",
                "layer_name": "Tax Parcels",
                "role": "base_layer",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/0",
                "source_status": "active",
                "source_priority": 1,
                "confidence_score": 0.95,
            },
            {
                "layer_key": "floodplain",
                "layer_name": "FloodPlain100year",
                "role": "constraint_overlay",
                "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer/2",
                "source_status": "active",
                "source_priority": 1,
                "confidence_score": 0.94,
            },
        ],
        "spatial_operations": [{"operation": "intersect", "target": "Tax Parcels", "overlay": "FloodPlain100year"}],
        "symbology_recommendations": ["Highlight affected parcels."],
        "review_reasons": ["Human review required before publishing."],
        "missing_data_needed": ["current_planning_cases"],
    }


def sample_webmap() -> dict:
    return {
        "title": "Concord Flood Report",
        "operationalLayers": [
            {
                "id": "tax_parcels",
                "title": "Tax Parcels",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/0",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/0",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer",
                "layerId": 0,
                "autoMapLayerKey": "tax_parcels",
                "autoMapRole": "base_layer",
                "autoMapSourceStatus": "active",
                "autoMapSourcePriority": 1,
                "autoMapConfidence": 0.95,
                "layerDefinition": {"definitionExpression": "TOWN = 'CONCORD'"},
            },
            {
                "id": "floodplain",
                "title": "FloodPlain100year",
                "url": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer/2",
                "layerUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer/2",
                "serviceUrl": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer",
                "layerId": 2,
                "autoMapLayerKey": "floodplain",
                "autoMapRole": "constraint_overlay",
                "autoMapSourceStatus": "active",
                "autoMapSourcePriority": 1,
                "autoMapConfidence": 0.94,
            },
        ],
    }


def write_review_packet(root: Path) -> Path:
    packet = root / "review_packets" / "review_report_packet"
    packet.mkdir(parents=True)
    recipe = sample_recipe()
    webmap = sample_webmap()
    layer_review = [
        {
            "title": "Tax Parcels",
            "layer_key": "tax_parcels",
            "role": "base_layer",
            "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/0",
            "source_status": "active",
            "definition_expression": "TOWN = 'CONCORD'",
            "confidence_score": 0.95,
        },
        {
            "title": "FloodPlain100year",
            "layer_key": "floodplain",
            "role": "constraint_overlay",
            "layer_url": "https://location.example.com/arcgis/rest/services/OpenData/Flood_Hazard_Areas/MapServer/2",
            "source_status": "active",
            "confidence_score": 0.94,
        },
    ]
    (packet / "recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
    (packet / "webmap.json").write_text(json.dumps(webmap), encoding="utf-8")
    (packet / "warnings.json").write_text(
        json.dumps({"publishing_blockers": ["Review and approval required."]}),
        encoding="utf-8",
    )
    (packet / "layer_review.json").write_text(json.dumps(layer_review), encoding="utf-8")
    (packet / "review_summary.md").write_text("# Review", encoding="utf-8")
    (packet / "review.html").write_text("<html>review</html>", encoding="utf-8")
    return packet


def write_approved_packet(root: Path) -> Path:
    packet = root / "review_packets_approved" / "approved_report_packet"
    packet.mkdir(parents=True)
    recipe = sample_recipe()
    webmap = sample_webmap()
    (packet / "approved_recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
    (packet / "approved_webmap.json").write_text(json.dumps(webmap), encoding="utf-8")
    (packet / "approved_warnings.json").write_text(json.dumps({"active": {}, "final_publish_ready": True}), encoding="utf-8")
    (packet / "approved_layer_review.json").write_text(json.dumps([]), encoding="utf-8")
    (packet / "approval_receipt.json").write_text(
        json.dumps({"decision": "approved", "final_publish_ready": True, "block_reasons": []}),
        encoding="utf-8",
    )
    (packet / "publish_receipt.json").write_text(
        json.dumps({"status": "dry_run", "created_item": False, "real_publish_attempted": False}),
        encoding="utf-8",
    )
    (packet / "smoke_test_receipt.json").write_text(
        json.dumps({"dry_run": True, "item_created": False, "blocked": False}),
        encoding="utf-8",
    )
    return packet


def test_report_generator_creates_required_files(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "OUTPUTS_ROOT", tmp_path)
    packet = write_review_packet(tmp_path)

    package = generate_report(packet)

    assert package.validation["is_valid"] is True
    for file_name in report_generator.REQUIRED_REPORT_FILES:
        assert (package.report_path / file_name).exists()


def test_layer_table_and_report_data_preserve_layers(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "OUTPUTS_ROOT", tmp_path)
    packet = write_review_packet(tmp_path)

    package = generate_report(packet)
    csv_text = (package.report_path / "layer_table.csv").read_text(encoding="utf-8")
    report_data = json.loads((package.report_path / "report_data.json").read_text(encoding="utf-8"))

    assert "Tax Parcels" in csv_text
    assert "FloodPlain100year" in csv_text
    assert "MapServer/2" in csv_text
    assert report_data["original_prompt"].startswith("Show parcels")
    assert report_data["workflow_status"] == "review_packet"
    assert report_data["draft_only_disclaimer"]


def test_warning_report_preserves_warnings(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "OUTPUTS_ROOT", tmp_path)
    packet = write_review_packet(tmp_path)

    package = generate_report(packet)
    warning_report = json.loads((package.report_path / "warning_report.json").read_text(encoding="utf-8"))

    serialized = json.dumps(warning_report)
    assert "Review and approval required" in serialized
    assert "Human review required before publishing" in serialized


def test_validate_report_catches_missing_files_and_secrets(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "OUTPUTS_ROOT", tmp_path)
    packet = write_review_packet(tmp_path)
    package = generate_report(packet)

    (package.report_path / "layer_table.csv").unlink()
    missing_validation = validate_report(package.report_path)
    assert missing_validation["is_valid"] is False
    assert "Missing required report files" in missing_validation["errors"][0]

    (package.report_path / "layer_table.csv").write_text("DATABASE_URL=postgresql://bad", encoding="utf-8")
    secret_validation = validate_report(package.report_path)
    assert secret_validation["is_valid"] is False
    assert any("protected marker" in error for error in secret_validation["errors"])


def test_report_outputs_remain_ignored_by_git():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "outputs/*" in gitignore


def test_list_and_get_reports(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "OUTPUTS_ROOT", tmp_path)
    packet = write_approved_packet(tmp_path)
    package = generate_report(packet)

    reports = list_reports()
    detail = get_report(package.report_id)

    assert reports[0]["report_id"] == package.report_id
    assert detail["report_data"]["workflow_status"] == "approved_local_draft"
    assert detail["report_data"]["dry_run_publish_receipt"]["status"] == "dry_run"
    assert detail["report_data"]["portal_smoke_test_receipt"]["dry_run"] is True


def test_api_generate_report_route(monkeypatch, tmp_path):
    monkeypatch.setattr(report_generator, "OUTPUTS_ROOT", tmp_path)
    monkeypatch.setattr("app.api_routes.generate_report", report_generator.generate_report)
    monkeypatch.setattr("app.api_routes.list_reports", report_generator.list_reports)
    monkeypatch.setattr("app.api_routes.get_report", report_generator.get_report)
    packet = write_review_packet(tmp_path)
    client = TestClient(create_app())

    response = client.post("/api/generate-report", json={"packet_folder": str(packet)})
    reports = client.get("/api/reports")

    assert response.status_code == 200
    assert response.json()["validation"]["is_valid"] is True
    assert reports.status_code == 200
    assert reports.json()["reports"]
    serialized = json.dumps(response.json()).lower()
    assert "database_url" not in serialized
    assert "arcgis_password" not in serialized
    assert "cfs_dev" not in serialized
