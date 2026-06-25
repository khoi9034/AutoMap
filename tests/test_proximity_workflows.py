import json
from pathlib import Path

from app.geometry_utils import build_straight_line_geojson, compute_straight_line_distance
from app.road_network_route_engine import build_road_following_draft
from app.proximity_engine import (
    _PROXIMITY_CACHE,
    build_proximity_context,
    extract_origin_and_destination,
    find_target_layer,
    resolve_address_point,
    resolve_origin,
    run_nearest_facility,
    run_proximity_request,
    run_route_draft,
)
from app.route_models import RouteDraftResult


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


def line_feature(name, coordinates):
    return {
        "type": "Feature",
        "properties": {"Name": name},
        "geometry": {"type": "LineString", "coordinates": coordinates},
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
        {
            "layer_key": "streets_centerlines",
            "layer_name": "Streets Centerlines",
            "category": "transportation",
            "aliases": ["streets", "roads", "centerlines"],
            "geometry_type": "esriGeometryPolyline",
            "is_verified": True,
            "is_active": True,
            "is_group_layer": False,
            "source_status": "active",
            "source_priority": 1,
            "layer_url": "https://example.test/Streets/0",
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
            "warnings": [
                "Address not found in Cabarrus County records. AutoMap's live address lookup currently supports Cabarrus County, NC only. Try a Cabarrus County address, parcel/PIN, or planning request."
            ],
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
    assert "Address not found" in " ".join(result["warnings"])


def test_target_layer_mapping_uses_verified_catalog_only():
    catalog = proximity_catalog()

    assert find_target_layer("nearest_school", layer_catalog=catalog)["layer_key"] == "schools_point"
    assert find_target_layer("nearest_fire_station", layer_catalog=catalog)["layer_key"] == "fire_stations"
    assert find_target_layer("nearest_fire_ems_station", layer_catalog=catalog)["layer_key"] == "fire_stations"
    assert find_target_layer("containing_fire_district", layer_catalog=catalog)["layer_key"] == "fire_districts"
    assert find_target_layer("nearest_school", layer_catalog=[{**catalog[0], "is_verified": False}]) is None


def test_address_origin_uses_return_geometry_false_first(monkeypatch):
    monkeypatch.setattr(
        "app.address_parcel_resolver.build_verified_address_field_map",
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


def test_proximity_result_writes_origin_target_and_line_geojson(monkeypatch, tmp_path):
    monkeypatch.setattr("app.proximity_engine.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.local_output_server.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.proximity_engine._safe_output_folder", lambda prompt: Path("outputs/proximity/test_result"))
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "matched",
            "origin_type": "address",
            "property_match_status": "not_resolved",
            "origin_feature": point_feature("Origin", -80, 35),
            "warnings": ["Address matched, but related parcel was not resolved from verified fields."],
        },
    )
    client = MockSpatialClient(counts=[1], features=[point_feature("Fire Station 1", -80.01, 35.01)])

    result = run_nearest_facility(
        "793 bartram ave",
        target_type="nearest_fire_station",
        layer_catalog=proximity_catalog(),
        client=client,
        persist=False,
    )

    output_folder = tmp_path / "outputs" / "proximity" / "test_result"
    assert (output_folder / "origin_point.geojson").exists()
    assert (output_folder / "target_feature.geojson").exists()
    assert (output_folder / "proximity_line.geojson").exists()
    assert (output_folder / "straight_line.geojson").exists()
    assert result["origin_point_geojson_url"].startswith("/api/local-outputs/geojson/proximity/")
    assert result["target_feature_geojson_url"].startswith("/api/local-outputs/geojson/proximity/")
    assert result["line_geojson_url"].startswith("/api/local-outputs/geojson/proximity/")
    assert {overlay["role"] for overlay in result["derived_overlays"]} >= {"origin", "target", "distance_line"}
    assert {overlay["symbol_key"] for overlay in result["derived_overlays"]} >= {"origin_home", "target_fire_station", "route_straight_line"}
    origin_overlay = next(overlay for overlay in result["derived_overlays"] if overlay["role"] == "origin")
    target_overlay = next(overlay for overlay in result["derived_overlays"] if overlay["role"] == "target")
    assert origin_overlay["kind"] == "generated_graphic"
    assert origin_overlay["layer_type"] == "graphics_overlay"
    assert origin_overlay["geojson"]["features"][0]["geometry"]["type"] == "Point"
    assert target_overlay["kind"] == "generated_graphic"
    assert target_overlay["geojson"]["features"][0]["geometry"]["type"] == "Point"
    assert "selected_parcel" not in {overlay["role"] for overlay in result["derived_overlays"]}
    assert result["property_match_status"] == "not_resolved"


def test_road_following_output_is_preferred_over_straight_line(monkeypatch, tmp_path):
    monkeypatch.setattr("app.proximity_engine.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.local_output_server.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.proximity_engine._safe_output_folder", lambda prompt: Path("outputs/proximity/test_road_route"))
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "matched",
            "origin_type": "address",
            "property_match_status": "not_resolved",
            "origin_feature": point_feature("Origin", -80, 35),
            "warnings": [],
        },
    )
    route_geojson = {
        "type": "FeatureCollection",
        "features": [
            line_feature("Road route", [[-80.0, 35.0], [-80.005, 35.006], [-80.01, 35.01]])
            | {"properties": {"automap_line_type": "road_following_draft", "route_mode": "road_following_draft"}}
        ],
    }
    straight_geojson = {
        "type": "FeatureCollection",
        "features": [line_feature("Straight reference", [[-80.0, 35.0], [-80.01, 35.01]])],
    }
    monkeypatch.setattr(
        "app.proximity_engine.build_road_following_draft",
        lambda *args, **kwargs: RouteDraftResult(
            route_mode="road_following_draft",
            route_label="Road-following draft route",
            route_warning="Road-following draft route, not official driving directions.",
            route_geojson=route_geojson,
            straight_line_geojson=straight_geojson,
            road_feature_count=2,
            metadata={"street_layer_key": "streets_centerlines"},
        ),
    )
    client = MockSpatialClient(counts=[1], features=[point_feature("Fire Station 1", -80.01, 35.01)])

    result = run_nearest_facility(
        "793 bartram ave",
        target_type="nearest_fire_station",
        layer_catalog=proximity_catalog(),
        client=client,
        persist=False,
        allow_route_draft=True,
        resolve_property=False,
    )

    output_folder = tmp_path / "outputs" / "proximity" / "test_road_route"
    assert (output_folder / "route_line.geojson").exists()
    assert (output_folder / "straight_line.geojson").exists()
    assert result["route_mode"] == "road_network"
    assert result["nearest_facility_method"] == "road_distance"
    assert result["line_geojson_path"] == result["route_line_geojson_path"]
    assert result["route_geojson_path"] == result["route_line_geojson_path"]
    assert result["straight_line_visible_default"] is False
    route_overlay = next(overlay for overlay in result["derived_overlays"] if overlay["role"] == "route_line")
    assert route_overlay["id"] == "road_following_route_draft"
    assert route_overlay["symbol_key"] == "route_road_following"
    assert route_overlay["kind"] == "generated_graphic"
    assert route_overlay["layer_type"] == "route_overlay"
    assert route_overlay["geojson"]["features"][0]["geometry"]["type"] == "LineString"


def test_nearest_facility_can_be_selected_by_road_distance(monkeypatch, tmp_path):
    monkeypatch.setattr("app.proximity_engine.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.local_output_server.repo_root", lambda: tmp_path)
    monkeypatch.setattr("app.proximity_engine._safe_output_folder", lambda prompt: Path("outputs/proximity/test_road_selection"))
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "matched",
            "origin_type": "address",
            "property_match_status": "not_resolved",
            "origin_feature": point_feature("Origin", -80, 35),
            "warnings": [],
        },
    )

    near_straight = point_feature("Fire Station Straight Near", -80.01, 35.0)
    better_road = point_feature("Fire Station Road Near", -80.04, 35.0)

    def fake_road_route(origin, target, **kwargs):
        target_name = target["properties"]["Name"]
        route_distance = 8.0 if "Straight" in target_name else 1.25
        return RouteDraftResult(
            route_mode="road_network",
            route_label="Road-following draft route",
            route_warning="Draft route based on public road centerlines. Not official navigation.",
            route_geojson={
                "type": "FeatureCollection",
                "features": [
                    line_feature(target_name, [[-80.0, 35.0], target["geometry"]["coordinates"]])
                    | {"properties": {"automap_line_type": "road_following_draft", "route_mode": "road_network"}}
                ],
            },
            straight_line_geojson={"type": "FeatureCollection", "features": []},
            route_distance_miles=route_distance,
            road_feature_count=4,
        )

    monkeypatch.setattr("app.proximity_engine.build_road_following_draft", fake_road_route)
    client = MockSpatialClient(counts=[2], features=[near_straight, better_road])

    result = run_nearest_facility(
        "793 bartram ave",
        target_type="nearest_fire_station",
        layer_catalog=proximity_catalog(),
        client=client,
        persist=False,
        allow_route_draft=True,
        resolve_property=False,
    )

    assert result["target_name"] == "Fire Station Road Near"
    assert result["route_mode"] == "road_network"
    assert result["nearest_facility_method"] == "road_distance"
    assert result["distance_value"] == 1.25
    assert result["route_distance_miles"] == 1.25
    assert result["straight_line_distance_miles"] > 1.25


def test_fast_proximity_cache_prefers_saved_road_following_result(monkeypatch):
    prompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"
    cache_key = (prompt.lower(), False, False)
    road_result = {
        "status": "ok",
        "raw_prompt": prompt,
        "route_mode": "road_following_draft",
        "route_label": "Road-following draft route",
        "route_line_geojson_path": "outputs/proximity/test/route_line.geojson",
        "line_geojson_path": "outputs/proximity/test/route_line.geojson",
        "warnings": [],
    }

    _PROXIMITY_CACHE.clear()
    _PROXIMITY_CACHE[cache_key] = {
        "status": "ok",
        "raw_prompt": prompt,
        "route_mode": "straight_line_reference",
        "line_geojson_path": "outputs/proximity/test/straight_line.geojson",
        "warnings": [],
    }
    monkeypatch.setattr(
        "app.proximity_engine._cached_successful_result_for_prompt",
        lambda prompt_value, schema_name="automap": dict(road_result),
    )

    try:
        result = run_proximity_request(prompt, persist=True, allow_route_draft=False, resolve_property=False)
        assert result["route_mode"] == "road_network"
        assert result["route_geojson_path"] == road_result["route_line_geojson_path"]
        assert result["straight_line_visible_default"] is False
        assert result["route_refinement_status"] == "succeeded"
        assert _PROXIMITY_CACHE[cache_key]["route_mode"] == "road_network"
    finally:
        _PROXIMITY_CACHE.clear()


def test_road_following_draft_succeeds_on_mocked_centerline_graph():
    origin = point_feature("Origin", -80.0, 35.0)
    target = point_feature("Fire Station 1", -80.03, 35.0)
    roads = [
      line_feature("Main", [[-80.0, 35.0], [-80.01, 35.0], [-80.02, 35.0]]),
      line_feature("Second", [[-80.02, 35.0], [-80.03, 35.0]]),
    ]
    client = MockSpatialClient(counts=[len(roads)], features=roads)

    result = build_road_following_draft(
        origin,
        target,
        target_type="nearest_fire_station",
        target_layer_key="fire_stations",
        layer_catalog=proximity_catalog(),
        client=client,
    )

    assert result.route_mode == "road_network"
    assert result.route_geojson["features"][0]["properties"]["automap_line_type"] == "road_following_draft"
    assert result.route_geojson["features"][0]["properties"]["route_mode"] == "road_network"
    assert result.road_feature_count == 2
    assert client.count_queries[0]["layer_url"] == "https://example.test/Streets/0"


def test_road_following_draft_falls_back_when_no_centerline_layer():
    origin = point_feature("Origin", -80.0, 35.0)
    target = point_feature("Fire Station 1", -80.03, 35.0)
    catalog_without_roads = [record for record in proximity_catalog() if record["layer_key"] != "streets_centerlines"]

    result = build_road_following_draft(
        origin,
        target,
        target_type="nearest_fire_station",
        target_layer_key="fire_stations",
        layer_catalog=catalog_without_roads,
        client=MockSpatialClient(counts=[]),
    )

    assert result.route_mode == "straight_line_fallback"
    assert result.route_geojson is None
    assert result.straight_line_geojson["features"][0]["properties"]["route_mode"] == "straight_line_fallback"


def test_address_point_to_parcel_spatial_lookup_is_bounded(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.resolve_address_point",
        lambda address_value, **kwargs: {
            "status": "matched",
            "origin_type": "address",
            "origin_feature": point_feature("793 Bartram Ave", -80.58, 35.36),
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "app.proximity_engine.create_parcel_set",
        lambda raw_input, **kwargs: {
            "parcel_set_id": "parcel_set_address",
            "input_type": "address",
            "matched_count": 0,
            "matched_parcels": [],
            "candidate_matches": [],
            "warnings": [],
        },
    )
    monkeypatch.setattr(
        "app.proximity_engine.find_tax_parcel_layer",
        lambda schema_name="automap": {
            "layer_key": "tax_parcels",
            "layer_url": "https://example.test/Parcels/0",
            "is_verified": True,
            "is_active": True,
            "geometry_type": "esriGeometryPolygon",
        },
    )
    monkeypatch.setattr(
        "app.proximity_engine.infer_parcel_id_fields",
        lambda layer, schema_name="automap": {"object_id": ["OBJECTID"], "pin14": ["PIN14"], "pin": [], "parcel_id": [], "address": ["SITEADDR"]},
    )
    parcel_feature = {
        "type": "Feature",
        "properties": {"OBJECTID": 7, "PIN14": "12345678901234", "SITEADDR": "793 BARTRAM AVE"},
        "geometry": {"type": "Polygon", "coordinates": [[[-80.581, 35.359], [-80.579, 35.359], [-80.579, 35.361], [-80.581, 35.361], [-80.581, 35.359]]]},
    }
    client = MockSpatialClient(counts=[1], features=[parcel_feature])

    result = resolve_origin("793 bartram ave", client=client)

    assert result["status"] == "matched"
    assert result["property_match_status"] == "matched"
    assert result["selected_parcel_feature"]["geometry"]["type"] == "Polygon"
    assert client.count_queries[-1]["geometry_type"] == "esriGeometryPoint"
    assert client.count_queries[-1]["spatial_rel"] == "esriSpatialRelIntersects"
    assert client.feature_queries[-2]["return_geometry"] is False
    assert client.feature_queries[-1]["return_geometry"] is True


def test_fire_station_prompt_does_not_silently_label_ems_only(monkeypatch):
    monkeypatch.setattr(
        "app.proximity_engine.resolve_origin",
        lambda origin_input, **kwargs: {
            "status": "matched",
            "origin_type": "address",
            "origin_feature": point_feature("Origin", -80, 35),
            "warnings": [],
        },
    )
    monkeypatch.setattr("app.proximity_engine._write_line_output", lambda result, output_folder, line_geojson: result)
    client = MockSpatialClient(counts=[1], features=[point_feature("EMS 2", -80.01, 35.01)])

    result = run_nearest_facility(
        "793 bartram ave",
        target_type="nearest_fire_station",
        layer_catalog=proximity_catalog(),
        client=client,
        persist=False,
    )

    assert result["target_type"] == "nearest_fire_ems_station"
    assert result["requested_target_type"] == "nearest_fire_station"
    assert result["target_classification"] == "mixed_fire_ems"
    assert "could not confirm a fire-only filter" in " ".join(result["warnings"])


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
    monkeypatch.setattr(
        "app.proximity_engine.build_road_following_draft",
        lambda *args, **kwargs: RouteDraftResult(
            route_mode="straight_line_fallback",
            route_label="Straight-line fallback",
            route_warning="Road route unavailable; showing straight-line reference only.",
            straight_line_geojson={"type": "FeatureCollection", "features": []},
            warnings=["Road route unavailable; showing straight-line reference only."],
        ),
    )

    result = run_route_draft("65 Church St S", "123 Main St", persist=False)

    assert result["status"] == "ok"
    assert result["route_status"] == "straight_line_fallback"
    assert result["route_mode"] == "straight_line_fallback"
    assert "Road route unavailable" in " ".join(result["warnings"])
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
