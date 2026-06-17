import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.local_output_server import make_local_output_file_id
from app.web_ui import create_app


def _encode(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def test_local_output_server_serves_only_approved_geojson(monkeypatch, tmp_path):
    monkeypatch.setattr("app.local_output_server.repo_root", lambda: tmp_path)
    folder = tmp_path / "outputs" / "proximity" / "sample"
    folder.mkdir(parents=True)
    geojson_path = folder / "origin_point.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"name": "Origin"}, "geometry": {"type": "Point", "coordinates": [-80, 35]}}
                ],
            }
        ),
        encoding="utf-8",
    )
    file_id = make_local_output_file_id("outputs/proximity/sample/origin_point.geojson", output_type="proximity")
    client = TestClient(create_app())

    response = client.get(f"/api/local-outputs/geojson/proximity/{file_id}")
    metadata = client.get(f"/api/local-outputs/metadata/proximity/{file_id}")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/geo+json")
    assert response.json()["features"][0]["properties"]["name"] == "Origin"
    assert metadata.status_code == 200
    assert metadata.json()["feature_count"] == 1


def test_local_output_server_blocks_path_traversal(monkeypatch, tmp_path):
    monkeypatch.setattr("app.local_output_server.repo_root", lambda: tmp_path)
    (tmp_path / "outputs" / "proximity").mkdir(parents=True)
    unsafe_id = _encode("outputs/proximity/../secret.geojson")
    client = TestClient(create_app())

    response = client.get(f"/api/local-outputs/geojson/proximity/{unsafe_id}")

    assert response.status_code == 404


def test_local_output_server_blocks_protected_markers(monkeypatch, tmp_path):
    monkeypatch.setattr("app.local_output_server.repo_root", lambda: tmp_path)
    folder = tmp_path / "outputs" / "proximity" / "sample"
    folder.mkdir(parents=True)
    geojson_path = folder / "bad.geojson"
    geojson_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {"type": "Feature", "properties": {"note": "secret token"}, "geometry": {"type": "Point", "coordinates": [-80, 35]}}
                ],
            }
        ),
        encoding="utf-8",
    )
    file_id = make_local_output_file_id("outputs/proximity/sample/bad.geojson", output_type="proximity")
    client = TestClient(create_app())

    response = client.get(f"/api/local-outputs/geojson/proximity/{file_id}")

    assert response.status_code == 404
