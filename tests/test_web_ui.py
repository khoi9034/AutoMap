import subprocess
import sys
from pathlib import Path
import json

from fastapi.testclient import TestClient

from app import packet_index
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


def sample_webmap():
    return {
        "title": "Parcel Flood in Concord",
        "initialState": {"viewpoint": {"targetGeometry": {"xmin": -80.8, "ymin": 35.1, "xmax": -80.4, "ymax": 35.6}}},
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
                "layerDefinition": {"definitionExpression": "ZONE = 'AE'"},
                "autoMapRole": "constraint_overlay",
                "autoMapLayerKey": "floodplain",
                "autoMapSourceStatus": "active",
                "autoMapSourcePriority": 1,
                "autoMapConfidence": 0.9,
            }
        ],
    }


def write_ui_packet(root: Path, name="ui_packet") -> Path:
    folder = root / "review_packets" / name
    folder.mkdir(parents=True)
    (folder / "recipe.json").write_text(json.dumps(sample_recipe()), encoding="utf-8")
    (folder / "webmap.json").write_text(json.dumps(sample_webmap()), encoding="utf-8")
    (folder / "warnings.json").write_text(json.dumps({"preview_warnings": ["Draft only."]}), encoding="utf-8")
    (folder / "review.html").write_text("<html>review</html>", encoding="utf-8")
    return folder


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
    assert "Create Recipe" in response.text
    assert "Verified Layers" in response.text


def test_demo_page_loads():
    client = TestClient(create_app())
    response = client.get("/demo")

    assert response.status_code == 200
    assert "Approved Demo Scenarios" in response.text
    assert "Show commercial zoning around Concord" in response.text


def test_status_page_loads_without_secrets():
    client = TestClient(create_app())
    response = client.get("/status")
    lowered = response.text.lower()

    assert response.status_code == 200
    assert "System Status" in response.text
    assert "ArcGIS Publisher Mode" in response.text
    assert "database_url" not in lowered
    assert "arcgis_password" not in lowered
    assert ".env" not in lowered


def test_history_page_loads():
    client = TestClient(create_app())
    response = client.get("/history")

    assert response.status_code == 200
    assert "Request History" in response.text


def test_homepage_lists_latest_drafts(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_ui_packet(tmp_path, name="latest_ui_packet")
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "Latest Drafts" in response.text
    assert "/preview/latest_ui_packet" in response.text


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
    assert "Preview Adjusted Map" in response.text


def test_preview_route_loads(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_ui_packet(tmp_path, name="preview_ui_packet")
    client = TestClient(create_app())

    response = client.get("/preview/preview_ui_packet")

    assert response.status_code == 200
    assert "automap-preview-map" in response.text
    assert "Review Details" in response.text
    assert "Open WebMap JSON" in response.text


def test_preview_config_endpoint_is_sanitized(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_ui_packet(tmp_path, name="config_ui_packet")
    client = TestClient(create_app())

    response = client.get("/api/preview-config?packet_id=config_ui_packet")
    serialized = json.dumps(response.json()).lower()

    assert response.status_code == 200
    assert response.json()["operational_layers"][0]["preview_type"] == "map_image_sublayer"
    assert response.json()["operational_layers"][0]["layer_id"] == 2
    assert "arcgis_password" not in serialized
    assert "database_url" not in serialized
    assert ".env" not in serialized


def test_review_packet_page_includes_preview_link(monkeypatch):
    monkeypatch.setattr(
        "app.ui_routes.build_review_packet",
        lambda prompt: {
            "recipe": sample_recipe(),
            "webmap_json": sample_webmap(),
            "warnings": {"preview_warnings": ["Draft only."]},
        },
    )
    monkeypatch.setattr("app.ui_routes.save_review_packet", lambda prompt, recipe, webmap: Path("outputs/review_packets/sample_packet"))
    monkeypatch.setattr("app.ui_routes.validate_review_packet", lambda path: {"is_valid": True})
    monkeypatch.setattr("app.ui_routes.build_layer_review_table", lambda recipe, webmap: [])
    client = TestClient(create_app())

    response = client.post("/review-packet", data={"prompt": "Show parcels in Concord that are in the 100-year floodplain."})

    assert response.status_code == 200
    assert "Preview Map" in response.text
    assert "/preview?path=outputs%2Freview_packets%2Fsample_packet" in response.text


def test_preview_route_does_not_publish(monkeypatch, tmp_path):
    monkeypatch.setattr(packet_index, "OUTPUTS_ROOT", tmp_path)
    write_ui_packet(tmp_path, name="no_publish_preview")

    def fail_publish(*_args, **_kwargs):
        raise AssertionError("Preview route must not publish.")

    monkeypatch.setattr("app.ui_routes.publish_webmap_draft", fail_publish)
    client = TestClient(create_app())

    response = client.get("/preview/no_publish_preview")

    assert response.status_code == 200


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
    monkeypatch.setattr("app.ui_routes.list_review_packets", lambda: [])
    monkeypatch.setattr("app.ui_routes.list_adjusted_packets", lambda: [])
    monkeypatch.setattr("app.ui_routes.find_latest_packet", lambda: None)
    monkeypatch.setattr(
        "app.ui_routes.get_system_status",
        lambda: {
            "catalog": {"verified_layer_count": 0},
            "profiles": {"field_profile_count": 0, "value_profile_count": 0},
            "data_gap_count": 0,
            "packets": {"review_packet_count": 0, "adjusted_packet_count": 0},
        },
    )
    client = TestClient(create_app())

    combined = "\n".join(
        [
            client.get("/").text,
            client.get("/catalog?q=flood").text,
            client.get("/data-gaps").text,
            client.get("/status").text,
        ]
    ).lower()

    assert "cfs" not in combined
    assert "cfs_dev" not in combined


def test_cli_commands_exist():
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--help"],
        cwd=Path(__file__).resolve().parent.parent,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "--serve-ui" in result.stdout
    assert "--system-status" in result.stdout
    assert "--run-demo-workflow" in result.stdout
    assert "--list-packets" in result.stdout
