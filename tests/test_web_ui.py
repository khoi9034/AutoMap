import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.web_ui import create_app


def sample_recipe():
    return {
        "map_title": "Parcel Flood in Concord",
        "user_intent": "Show parcels in Concord that are in the 100-year floodplain.",
        "parsed_request": {
            "geography_terms": [{"name": "Concord", "type": "municipality"}],
            "topics": ["parcel", "flood"],
            "raw_prompt": "Show parcels in Concord that are in the 100-year floodplain.",
        },
        "selected_layers": [
            {
                "layer_key": "parcels",
                "layer_name": "Tax Parcels",
                "role": "base_layer",
                "source_status": "active",
                "confidence_score": 0.9,
                "layer_url": "https://location.example.com/MapServer/1",
            }
        ],
        "filter_plan": {
            "municipal": {
                "layer_name": "MunicipalDistrict",
                "draft_where_clause": "DISTRICT = 'CITY OF CONCORD'",
                "review_reason": None,
            }
        },
        "spatial_operations": [{"operation": "intersect", "output": "affected_parcels"}],
        "review_reasons": [],
        "missing_data_needed": [],
        "confidence_score": 0.9,
        "needs_review": False,
    }


def test_app_starts_and_health_loads():
    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["real_publishing_enabled_in_ui"] is False


def test_homepage_loads():
    client = TestClient(create_app())
    response = client.get("/")

    assert response.status_code == 200
    assert "AutoMap: County GIS Request Engine" in response.text
    assert "Show parcels in Concord" in response.text


def test_recipe_route_works_with_sample_prompt(monkeypatch):
    monkeypatch.setattr("app.ui_routes.build_recipe", lambda prompt: sample_recipe())
    client = TestClient(create_app())

    response = client.post("/recipe", data={"prompt": "Show parcels in Concord that are in the 100-year floodplain."})

    assert response.status_code == 200
    assert "Parcel Flood in Concord" in response.text
    assert "Tax Parcels" in response.text
    assert "DISTRICT = &#39;CITY OF CONCORD&#39;" in response.text


def test_catalog_search_route_works(monkeypatch):
    monkeypatch.setattr(
        "app.ui_routes.search_layers",
        lambda query: [
            {
                "layer_name": "FloodPlain100year",
                "category": "flood",
                "source_status": "active",
                "source_priority": 1,
                "is_verified": True,
                "is_historical": False,
                "layer_url": "https://location.example.com/MapServer/2",
            }
        ],
    )
    client = TestClient(create_app())

    response = client.get("/catalog?q=flood")

    assert response.status_code == 200
    assert "FloodPlain100year" in response.text


def test_data_gaps_route_works(monkeypatch):
    monkeypatch.setattr(
        "app.ui_routes.list_data_gaps",
        lambda: [
            {
                "gap_key": "current_permits",
                "topic": "permits",
                "missing_layer_type": "current permit layer",
                "reason": "Current permit layer missing.",
                "status": "open",
                "created_at": "2026-06-15",
            }
        ],
    )
    client = TestClient(create_app())

    response = client.get("/data-gaps")

    assert response.status_code == 200
    assert "current_permits" in response.text
    assert "Current permit layer missing." in response.text


def test_dry_run_publish_route_does_not_create_real_item(monkeypatch):
    called = {}

    def fake_publish(path, dry_run=True, confirm_publish=False):
        called["path"] = path
        called["dry_run"] = dry_run
        called["confirm_publish"] = confirm_publish
        return {
            "status": "dry_run",
            "created_item": False,
            "published": False,
            "shared_public": False,
            "shared_organization": False,
        }

    monkeypatch.setattr("app.ui_routes.publish_webmap_draft", fake_publish)
    client = TestClient(create_app())

    response = client.post("/publish-dry-run", data={"adjusted_packet_folder": "outputs/review_packets_adjusted/sample"})

    assert response.status_code == 200
    assert called["dry_run"] is True
    assert called["confirm_publish"] is False
    assert "Created item:</strong> False" in response.text


def test_ui_does_not_require_arcgis_login_or_expose_secrets():
    client = TestClient(create_app())
    response = client.get("/")
    lowered = response.text.lower()

    assert response.status_code == 200
    assert "arcgis_username" not in lowered
    assert "arcgis_password" not in lowered
    assert ".env" not in lowered
    assert "database_url" not in lowered


def test_ui_does_not_reference_cfs_on_main_pages(monkeypatch):
    monkeypatch.setattr("app.ui_routes.search_layers", lambda query: [])
    monkeypatch.setattr("app.ui_routes.list_data_gaps", lambda: [])
    client = TestClient(create_app())

    combined = "\n".join(
        [
            client.get("/").text,
            client.get("/catalog?q=flood").text,
            client.get("/data-gaps").text,
        ]
    ).lower()

    assert "cfs" not in combined
    assert "cfs_dev" not in combined


def test_serve_command_exists():
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--help"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "--serve-ui" in result.stdout
