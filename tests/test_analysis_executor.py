import json
import os
from pathlib import Path

import pytest

from app.analysis_executor import build_analysis_plan, execute_analysis
from app.analysis_models import DEFAULT_MAX_FEATURES
from app.geometry_utils import compute_basic_stats, intersect_features
from app.spatial_query_client import SpatialQueryClient


def feature(name: str, coords: list[list[float]], **props):
    return {
        "type": "Feature",
        "properties": {"name": name, **props},
        "geometry": {"type": "Polygon", "coordinates": [coords]},
    }


CONCORD = feature("CITY OF CONCORD", [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]], OBJECTID=1)
OTHER = feature("OTHER TOWN", [[20, 20], [30, 20], [30, 30], [20, 30], [20, 20]], OBJECTID=2)
FLOOD100 = feature("FloodPlain100year", [[2, 2], [5, 2], [5, 5], [2, 5], [2, 2]], OBJECTID=10)
PARCEL_IN = feature("Parcel A", [[3, 3], [4, 3], [4, 4], [3, 4], [3, 3]], OBJECTID=100, PIN="A")
PARCEL_OUT = feature("Parcel B", [[6, 6], [7, 6], [7, 7], [6, 7], [6, 6]], OBJECTID=101, PIN="B")


def catalog_record(layer_key, layer_name, category, *, role=None, service_name=None, layer_id=0, fields=None):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "aliases": [category, layer_name],
        "service_name": service_name or layer_name,
        "layer_url": f"https://example.test/{layer_key}/MapServer/{layer_id}",
        "service_url": f"https://example.test/{layer_key}/MapServer",
        "source_priority": 1,
        "source_status": "active",
        "is_verified": True,
        "is_feature_layer": True,
        "is_group_layer": False,
        "geometry_type": "esriGeometryPolygon",
        "layer_id": layer_id,
        "fields": fields or [{"name": "OBJECTID", "type": "esriFieldTypeOID"}],
        "object_id_field": "OBJECTID",
        "role": role,
    }


def sample_catalog():
    return [
        catalog_record("parcels", "Tax Parcels", "parcel", service_name="Tax_Parcels", layer_id=0),
        catalog_record("municipal", "MunicipalDistrict", "jurisdiction", service_name="MunicipalDistrict", layer_id=0),
        catalog_record("floodway", "FloodWay", "flood", service_name="Flood_Hazard_Areas", layer_id=0),
        catalog_record("flood100", "FloodPlain100year", "flood", service_name="Flood_Hazard_Areas", layer_id=2),
        catalog_record(
            "concord_zoning",
            "Concord Zoning",
            "zoning",
            service_name="Zoning_By_Municipalities",
            layer_id=0,
            fields=[
                {"name": "OBJECTID", "type": "esriFieldTypeOID"},
                {"name": "ZONE_TYPE", "type": "esriFieldTypeString", "alias": "Zoning Class"},
            ],
        ),
        {
            **catalog_record("legacy_parcels_2014", "Tax Parcels 2014", "parcel", layer_id=14),
            "source_priority": 2,
            "source_status": "legacy_historical",
            "is_historical": True,
            "historical_year": 2014,
        },
    ]


class FakeSpatialQueryClient:
    def __init__(self, *, block_target=False):
        self.block_target = block_target
        self.feature_queries: list[str] = []

    def query_count(self, layer_url, **kwargs):
        if "parcels" in layer_url and kwargs.get("geometry"):
            return {"count": 6000 if self.block_target else 2, "return_geometry": False, "geometry_used": True}
        if "parcels" in layer_url:
            return {"count": 90000, "return_geometry": False, "geometry_used": False}
        if "municipal" in layer_url:
            return {"count": 2, "return_geometry": False, "geometry_used": False}
        if "flood" in layer_url:
            return {"count": 1, "return_geometry": False, "geometry_used": bool(kwargs.get("geometry"))}
        if "zoning" in layer_url:
            return {"count": 1, "return_geometry": False, "geometry_used": bool(kwargs.get("geometry"))}
        return {"count": 0, "return_geometry": False, "geometry_used": False}

    def query_features(self, layer_url, **kwargs):
        self.feature_queries.append(layer_url)
        if "municipal" in layer_url:
            return {"status": "ok", "count": 2, "features": [CONCORD, OTHER]}
        if "flood100" in layer_url or "floodway" in layer_url:
            return {"status": "ok", "count": 1, "features": [FLOOD100]}
        if "parcels" in layer_url:
            return {"status": "ok", "count": 2, "features": [PARCEL_IN, PARCEL_OUT]}
        if "zoning" in layer_url:
            return {"status": "ok", "count": 1, "features": [feature("Commercial", [[1, 1], [2, 1], [2, 2], [1, 2], [1, 1]], ZONE_TYPE="COMMERCIAL")]}
        return {"status": "ok", "count": 0, "features": []}


def isolate_outputs(monkeypatch, tmp_path):
    monkeypatch.setattr("app.analysis_result_store.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.analysis_executor.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.analysis_executor.init_analysis_tables", lambda: None)
    monkeypatch.setattr("app.analysis_executor.record_analysis_run", lambda result: result.to_dict())


def test_analysis_plan_created_for_flood_parcel_request():
    plan = build_analysis_plan(
        "Show parcels in Concord that are in the 100-year floodplain.",
        catalog_records=sample_catalog(),
        query_client=FakeSpatialQueryClient(),
    )

    assert plan["executable"] is True
    assert plan["operation_type"] == "select_by_intersection"
    assert plan["target_layer"]["layer_key"] == "parcels"
    assert plan["constraint_layer"]["layer_key"] == "flood100"
    assert "Write selected parcel GeoJSON" in " ".join(plan["recommended_execution_plan"])


def test_bounded_query_count_blocks_huge_requests_before_target_download(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)
    fake = FakeSpatialQueryClient(block_target=True)

    result = execute_analysis(
        "Show parcels in Concord that are in the 100-year floodplain.",
        catalog_records=sample_catalog(),
        query_client=fake,
    )

    assert result["status"] == "blocked"
    assert "exceeds max feature limit" in json.dumps(result["blocked_reasons"])
    assert not any("parcels" in url for url in fake.feature_queries)


def test_intersection_execution_writes_receipt_and_valid_geojson(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)

    result = execute_analysis(
        "Show parcels in Concord that are in the 100-year floodplain.",
        catalog_records=sample_catalog(),
        query_client=FakeSpatialQueryClient(),
    )

    output_path = tmp_path / result["output_geojson_path"]
    receipt_path = tmp_path / result["output_folder"] / "analysis_receipt.json"
    data = json.loads(output_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    assert result["status"] == "completed"
    assert result["output_count"] == 1
    assert data["type"] == "FeatureCollection"
    assert data["features"][0]["properties"]["PIN"] == "A"
    assert receipt["published"] is False
    assert receipt["protected_external_database_touched"] is False


def test_geometry_intersection_function_works_on_small_mock_features():
    selected = intersect_features([PARCEL_IN, PARCEL_OUT], [FLOOD100])

    assert len(selected) == 1
    assert selected[0]["properties"]["automap_selected"] is True
    assert compute_basic_stats(selected)["feature_count"] == 1


def test_attribute_filter_operation_writes_geojson(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)

    result = execute_analysis(
        "Show commercial zoning around Concord.",
        catalog_records=sample_catalog(),
        query_client=FakeSpatialQueryClient(),
    )

    assert result["status"] == "completed"
    assert result["operation_type"] == "attribute_filter_only"
    assert result["output_count"] == 1
    assert (tmp_path / result["output_geojson_path"]).exists()


def test_historical_request_is_planning_only_not_spatial_execution():
    plan = build_analysis_plan("Show 2014 parcels and zoning.", catalog_records=sample_catalog(), estimate_counts=False)

    assert plan["executable"] is False
    assert plan["operation_type"] == "unsupported_operation"
    assert any("Historical comparison" in reason for reason in plan["blocked_reasons"])


def test_spatial_query_client_blocks_over_limit_without_feature_download(monkeypatch):
    calls = []

    def fake_fetch(url):
        calls.append(url)
        return {"count": DEFAULT_MAX_FEATURES + 1}

    monkeypatch.setattr("app.spatial_query_client._fetch_json_or_geojson", fake_fetch)
    client = SpatialQueryClient(max_features=DEFAULT_MAX_FEATURES)

    result = client.query_features("https://example.test/Layer/0")

    assert result["status"] == "blocked"
    assert result["features"] == []
    assert len(calls) == 1
    assert "returnCountOnly" in calls[0]


def test_analysis_outputs_have_no_secrets_or_protected_database_refs(monkeypatch, tmp_path):
    isolate_outputs(monkeypatch, tmp_path)

    result = execute_analysis(
        "Show parcels in Concord that are in the 100-year floodplain.",
        catalog_records=sample_catalog(),
        query_client=FakeSpatialQueryClient(),
    )
    serialized = json.dumps(result).lower()

    assert "database_url" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
    assert "cfs_dev" not in serialized
    assert "publish-draft-webmap" not in serialized


@pytest.mark.skipif(os.getenv("AUTOMAP_RUN_LIVE_REST_TESTS") != "true", reason="Live REST tests are opt-in.")
def test_live_rest_analysis_plan_is_opt_in_only():
    plan = build_analysis_plan("Show parcels in Concord that are in the 100-year floodplain.")

    assert "estimated_query_counts" in plan
