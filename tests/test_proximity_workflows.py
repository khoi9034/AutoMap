import json

from app.geometry_utils import build_straight_line_geojson, compute_straight_line_distance
from app.proximity_engine import (
    build_proximity_context,
    extract_origin_and_destination,
    find_target_layer,
    resolve_address_point,
    resolve_origin,
    run_nearest_facility,
    run_route_draft,
)


def point_feature(name, x=-80.0, y=35.0):
    return {
        "type": "Feature",
        "properties": {"OBJECTID": 1, "Name": name},
        "geometry": {"type": "Point", "coordinates": [x, y]},
    }


def polygon_feature(name):
    return {
        "type": "Feature",
        "properties": {"DISTRICT": name},
        "geometry": {"type": "Polygon", "coordinates": [[[-80, 35], [-80, 36], [-79, 36], [-80, 35]]]},
    }


def proximity_catalog():
    return [
        {
            "layer_key": "schools_point",
            "layer_name": "Schools",
            "category": "schools",
            "aliases": ["school", "schools"],
            "geometry_type": "esriGeometryPoint",
            "is_verified": True,
            "is_active": True,
            "is_group_layer": False,
            "source_status": "legacy",
            "source_priority": 2,
            "layer_url": "https://example.test/Schools/0",
        },
        {
            "layer_key": "fire_stations",
            "layer_name": "Fire and EMS Stations",
            "category": "public_facilities",
            "aliases": ["fire station", "ems station"],
            "geometry_type": "esriGeometryPoint",
            "is_verified": True,
            "is_active": True,
            "is_group_layer": False,
            "source_status": "legacy",
            "source_priority": 2,
            "layer_url": "https://example.test/Fire/0",
        },
        {
            "layer_key": "fire_districts",
            "layer_name": "Fire Districts",
            "category": "general",
            "aliases": ["fire district"],
            "geometry_type": "esriGeometryPolygon",
            "is_verified": True,
            "is_active": True,
            "is_group_layer": False,
            "source_status": "legacy",
            "source_priority": 2,
            "layer_url": "https://example.test/FireDistricts/0",
        },
    ]


class MockSpatialClient:
    def __init__(self, counts=None, features=None):
        self.counts = list(counts or [1])
        self.features = features or [point_feature("Target", -80.01, 35.01)]
        self.count_queries = []
        self.feature_queries = []

    def query_count(self, layer_url, *, where=None, geometry=None, geometry_type=None, spatial_rel=None):
        self.count_queries.append(
            {
                "layer_url": layer_url,
                "where": where,
                "geometry": geometry,
                "geometry_type": geometry_type,
                "spatial_rel": spatial_rel,
                "return_geometry": False,
            }
        )
        count = self.counts.pop(0) if self.counts else 1
        return {"count": count, "return_geometry": False}

    def query_features(self, layer_url, *, where=None, geometry=None, return_geometry=True, result_record_count=None, **kwargs):
        self.feature_queries.append(
            {
                "layer_url": layer_url,
                "where": where,
                "geometry": geometry,
                "return_geometry": return_geometry,
                "result_record_count": result_record_count,
            }
        )
        return {"status": "ok", "features": self.features, "feature_collection": {"type": "FeatureCollection", "features": self.features}}


def test_proximity_intent_detected_for_nearest_school():
    context = build_proximity_context("How far is parcel 5528-12-3456 from the nearest school?")

    assert context["proximity_detected"] is True
    assert context["target_type"] == "nearest_school"
    assert context["straight_line_supported"] is True
    assert context["road_route_supported"] is False
    assert context["clarifying_questions"]


def test_address_fire_station_prompt_extracts_address_origin():
    prompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"
    context = build_proximity_context(prompt)
    parts = extract_origin_and_destination(prompt)

    assert context["proximity_detected"] is True
    assert context["target_type"] == "nearest_fire_station"
    assert parts["origin_input"].lower() == "793 bartram ave"
    assert parts["destination_input"] is None


def test_address_origin_unmatched_uses_address_warning(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.resolve_address_point",
        lambda address_value, **kwargs: {
            "status": "unmatched",
            "origin_type": "address",
            "origin_feature": None,
            "warnings": ["Address not matched. AutoMap cannot zoom to or map this address until a valid public address record or related parcel/PIN is matched."],
        },
    )
    monkeypatch.setattr(
        "app.proximity_engine.create_parcel_set",
        lambda raw_input, **kwargs: {
            "parcel_set_id": "parcel_set_unmatched",
            "input_type": "address",
            "matched_count": 0,
            "matched_parcels": [],
            "candidate_matches": [],
            "warnings": [],
        },
    )

    result = resolve_origin("793 bartram ave")

    assert result["status"] == "needs_review"
    assert result["origin_type"] == "address"
    assert "Address not matched" in " ".join(result["warnings"])


def test_target_layer_mapping_uses_verified_catalog_only():
    catalog = proximity_catalog()

    assert find_target_layer("nearest_school", layer_catalog=catalog)["layer_key"] == "schools_point"
    assert find_target_layer("nearest_fire_station", layer_catalog=catalog)["layer_key"] == "fire_stations"
    assert find_target_layer("containing_fire_district", layer_catalog=catalog)["layer_key"] == "fire_districts"
    assert find_target_layer("nearest_school", layer_catalog=[{**catalog[0], "is_verified": False}]) is None


def test_address_origin_uses_return_geometry_false_first(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.build_verified_address_field_map",
        lambda schema_name="automap": {
            "layer_key": "addresses",
            "layer_url": "https://example.test/Addresses/0",
            "fields_by_role": {"full_address": ["FULLADDR"]},
        },
    )
    client = MockSpatialClient(counts=[1], features=[point_feature("65 Church St S")])

    result = resolve_address_point("65 Church St S", client=client)

    assert result["status"] == "matched"
    assert client.count_queries[0]["return_geometry"] is False
    assert client.feature_queries[0]["return_geometry"] is True


def test_nearest_facility_uses_bounded_rings_and_no_countywide_download(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "matched",
            "origin_type": "parcel",
            "origin_feature": point_feature("Origin", -80, 35),
            "warnings": [],
        },
    )
    monkeypatch.setattr("app.proximity_engine._write_line_output", lambda result, output_folder, line_geojson: result)
    client = MockSpatialClient(counts=[0, 1], features=[point_feature("Cabarrus School", -80.01, 35.01)])

    result = run_nearest_facility(
        "parcel 5528-12-3456",
        target_type="nearest_school",
        layer_catalog=proximity_catalog(),
        client=client,
        persist=False,
    )

    assert result["status"] == "ok"
    assert result["bounded_search"]["ring_used_miles"] == 1
    assert result["downloaded_countywide"] is False
    assert all(query["geometry_type"] == "esriGeometryEnvelope" for query in client.count_queries)


def test_candidate_download_cap_blocks_large_target_search(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "matched",
            "origin_type": "parcel",
            "origin_feature": point_feature("Origin", -80, 35),
            "warnings": [],
        },
    )
    client = MockSpatialClient(counts=[300, 0, 0, 0, 0], features=[])

    result = run_nearest_facility(
        "parcel 5528-12-3456",
        target_type="nearest_school",
        layer_catalog=proximity_catalog(),
        client=client,
        persist=False,
    )

    assert result["status"] == "needs_review"
    assert "above hard max" in " ".join(result["warnings"])
    assert client.feature_queries == []


def test_route_draft_without_network_service_warns(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "matched",
            "origin_type": "address",
            "origin_feature": point_feature("Origin", -80, 35),
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "app.proximity_engine.resolve_address_point",
        lambda destination_input, **kwargs: {
            "status": "matched",
            "origin_type": "address",
            "origin_feature": point_feature("Destination", -80.02, 35.02),
            "warnings": [],
        },
    )
    monkeypatch.setattr("app.proximity_engine._write_line_output", lambda result, output_folder, line_geojson: result)

    result = run_route_draft("65 Church St S", "123 Main St", persist=False)

    assert result["status"] == "ok"
    assert result["route_status"] == "network_route_not_available"
    assert "Road-network routing requires" in " ".join(result["warnings"])
    assert result["published"] is False


def test_line_geojson_and_distance_validate_on_mocked_points():
    origin = point_feature("Origin", -80, 35)
    target = point_feature("Target", -80.01, 35.01)

    distance = compute_straight_line_distance(origin, target)
    line = build_straight_line_geojson(origin, target, properties={"label": "Straight-line distance"})

    assert distance > 0
    assert line["geometry"]["type"] == "LineString"
    assert line["properties"]["not_a_road_route"] is True


def test_proximity_result_has_no_cfs_or_secrets(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "needs_review",
            "origin_type": "pin",
            "origin_feature": None,
            "warnings": ["unmatched"],
        },
    )

    result = run_nearest_facility("parcel 5528-12-3456", target_type="nearest_school", persist=False)
    serialized = json.dumps(result).lower()

    assert "database_url" not in serialized
    assert "password" not in serialized
    assert "secret" not in serialized
    assert "cfs_dev" not in serialized
