import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.web_ui import create_app


def test_api_status_is_json_and_sanitized(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.get_system_status",
        lambda: {
            "version": "1.5.0",
            "database_connected": True,
            "DATABASE_URL": "postgresql://secret-password",
            "protected_note": "cfs_dev should never leave the API",
            "real_publish_enabled": False,
        },
    )
    client = TestClient(create_app())

    response = client.get("/api/status")
    serialized = json.dumps(response.json()).lower()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["version"] == "1.5.0"
    assert "database_url" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
    assert "cfs" not in serialized
    assert "cfs_dev" not in serialized


def test_cors_allows_local_next_frontend():
    client = TestClient(create_app())

    response = client.options(
        "/api/status",
        headers={
            "Origin": "http://localhost:3010",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3010"


def test_no_real_publish_endpoint_exposed():
    client = TestClient(create_app())
    paths = client.get("/openapi.json").json()["paths"]
    serialized_paths = json.dumps(paths).lower()

    assert "/api/publish-dry-run" in paths
    assert "/api/portal-smoke-test-dry-run" in paths
    assert "confirm-publish" not in serialized_paths
    assert "publish-draft-webmap" not in serialized_paths


def test_frontend_workflow_api_routes_exist():
    client = TestClient(create_app())
    paths = client.get("/openapi.json").json()["paths"]

    expected_paths = {
        "/api/status",
        "/api/catalog/search",
        "/api/data-gaps",
        "/api/history",
        "/api/packets",
        "/api/preview-config/{packet_id}",
        "/api/recipe",
        "/api/review-packet",
        "/api/webmap-draft",
        "/api/adjustment-template",
        "/api/apply-adjustments",
        "/api/approval-template",
        "/api/apply-approval",
        "/api/publish-dry-run",
        "/api/portal-smoke-test-dry-run",
    }

    assert expected_paths.issubset(set(paths))


def test_api_status_includes_sanitized_port_separation(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.get_system_status",
        lambda: {
            "version": "1.5.0",
            "database_connected": True,
            "ports": {"frontend": 3010, "backend_api": 8010, "reserved": [3000, 8000]},
            "real_publish_enabled": False,
        },
    )
    client = TestClient(create_app())

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["ports"] == {"frontend": 3010, "backend_api": 8010, "reserved": [3000, 8000]}


def test_api_publish_dry_run_cannot_real_publish(monkeypatch):
    calls = []

    def fake_publish(path, dry_run=True, confirm_publish=False):
        calls.append({"path": path, "dry_run": dry_run, "confirm_publish": confirm_publish})
        return {
            "status": "dry_run",
            "created_item": False,
            "real_publish_attempted": False,
            "shared_public": False,
            "shared_organization": False,
            "cfs_database_not_touched": True,
        }

    monkeypatch.setattr("app.api_routes.publish_webmap_draft", fake_publish)
    client = TestClient(create_app())

    response = client.post("/api/publish-dry-run", json={"approved_packet_folder": "outputs/review_packets_approved/sample"})
    serialized = json.dumps(response.json()).lower()

    assert response.status_code == 200
    assert calls == [
        {
            "path": "outputs/review_packets_approved/sample",
            "dry_run": True,
            "confirm_publish": False,
        }
    ]
    assert response.json()["result"]["status"] == "dry_run"
    assert "cfs" not in serialized


def test_api_portal_smoke_test_dry_run_cannot_real_publish(monkeypatch):
    calls = []

    def fake_smoke(path, confirm_publish=False):
        calls.append({"path": path, "confirm_publish": confirm_publish})
        return {
            "dry_run": True,
            "real_publish_attempted": False,
            "item_created": False,
            "blocked": False,
            "cfs_untouched_statement": "Protected external database was not touched.",
        }

    monkeypatch.setattr("app.api_routes.run_publish_smoke_test", fake_smoke)
    client = TestClient(create_app())

    response = client.post(
        "/api/portal-smoke-test-dry-run",
        json={"approved_packet_folder": "outputs/review_packets_approved/sample"},
    )
    serialized = json.dumps(response.json()).lower()

    assert response.status_code == 200
    assert calls == [{"path": "outputs/review_packets_approved/sample", "confirm_publish": False}]
    assert response.json()["result"]["dry_run"] is True
    assert response.json()["result"]["item_created"] is False
    assert "cfs" not in serialized


def test_api_recipe_returns_json(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.build_recipe",
        lambda prompt: {
            "map_title": "Flood parcel review",
            "user_intent": prompt,
            "parsed_request": {"topics": ["parcel", "flood"], "geography_terms": ["Concord"]},
            "selected_layers": [{"layer_name": "FloodPlain100year", "source_status": "active"}],
            "missing_data_needed": [],
            "confidence_score": 0.91,
        },
    )
    monkeypatch.setattr("app.api_routes.data_gap_records_from_recipe", lambda recipe: [])
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    response = client.post("/api/recipe", json={"prompt": "Show parcels in Concord floodplain"})

    assert response.status_code == 200
    assert response.json()["recipe"]["map_title"] == "Flood parcel review"
    assert response.json()["recipe"]["selected_layers"][0]["layer_name"] == "FloodPlain100year"


def test_api_review_packet_returns_stable_identifiers(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.build_review_packet",
        lambda prompt: {
            "recipe": {
                "map_title": "Flood parcel review",
                "selected_layers": [],
                "missing_data_needed": [],
                "review_reasons": [],
            },
            "webmap_json": {"title": "Flood parcel review", "operationalLayers": []},
            "warnings": {"preview_warnings": ["Draft only."]},
        },
    )
    monkeypatch.setattr(
        "app.api_routes.save_review_packet",
        lambda prompt, recipe, webmap: Path("outputs/review_packets/frontend_packet"),
    )
    monkeypatch.setattr("app.api_routes.validate_review_packet", lambda path: {"is_valid": True})
    monkeypatch.setattr("app.api_routes.build_layer_review_table", lambda recipe, webmap: [])
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    response = client.post("/api/review-packet", json={"prompt": "Show parcels in Concord floodplain"})

    assert response.status_code == 200
    assert response.json()["packet_id"] == "frontend_packet"
    assert response.json()["packet_path"] == "outputs\\review_packets\\frontend_packet" or response.json()["packet_path"] == "outputs/review_packets/frontend_packet"
    assert response.json()["preview_url"]
