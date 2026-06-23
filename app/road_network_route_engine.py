"""Bounded road-following draft routes from verified street centerlines."""

from __future__ import annotations

import heapq
import math
from typing import Any

from app.geometry_utils import build_straight_line_geojson, compute_origin_point
from app.layer_catalog_store import load_catalog_records
from app.route_models import (
    HARD_MAX_ROAD_FEATURES,
    MAX_ROAD_FEATURES,
    MAX_ROUTE_EXTENT_HEIGHT_DEGREES,
    MAX_ROUTE_EXTENT_WIDTH_DEGREES,
    ROAD_FOLLOWING_DRAFT_WARNING,
    STRAIGHT_LINE_FALLBACK_WARNING,
    RouteDraftResult,
)
from app.spatial_query_client import SpatialQueryClient


class RouteDraftError(RuntimeError):
    """Raised when a bounded road-following draft cannot be created."""


def _point_coordinates(feature: dict[str, Any]) -> tuple[float, float]:
    point = compute_origin_point(feature)
    coordinates = point.get("coordinates") or []
    if len(coordinates) < 2:
        raise RouteDraftError("Origin or target point coordinates are unavailable.")
    return float(coordinates[0]), float(coordinates[1])


def _haversine_miles(first: tuple[float, float], second: tuple[float, float]) -> float:
    lon1, lat1 = first
    lon2, lat2 = second
    radius_miles = 3958.7613
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    return radius_miles * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _route_extent(origin: tuple[float, float], target: tuple[float, float]) -> dict[str, Any]:
    xmin, xmax = sorted([origin[0], target[0]])
    ymin, ymax = sorted([origin[1], target[1]])
    width = max(xmax - xmin, 0.01)
    height = max(ymax - ymin, 0.01)
    buffer_x = max(width * 0.5, 0.015)
    buffer_y = max(height * 0.5, 0.015)
    envelope = {
        "xmin": xmin - buffer_x,
        "ymin": ymin - buffer_y,
        "xmax": xmax + buffer_x,
        "ymax": ymax + buffer_y,
        "spatialReference": {"wkid": 4326},
    }
    if envelope["xmax"] - envelope["xmin"] > MAX_ROUTE_EXTENT_WIDTH_DEGREES:
        raise RouteDraftError("Route search corridor is too wide for a bounded road-following draft.")
    if envelope["ymax"] - envelope["ymin"] > MAX_ROUTE_EXTENT_HEIGHT_DEGREES:
        raise RouteDraftError("Route search corridor is too tall for a bounded road-following draft.")
    return envelope


def _text_blob(record: dict[str, Any]) -> str:
    return " ".join(
        str(value).lower()
        for value in [
            record.get("layer_key"),
            record.get("layer_name"),
            record.get("service_name"),
            record.get("category"),
            record.get("canonical_topic"),
            record.get("aliases"),
            record.get("planning_use_cases"),
        ]
        if value
    )


def find_street_centerline_layer(
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    schema_name: str = "automap",
) -> dict[str, Any] | None:
    """Return the best verified streets/centerline layer for bounded routing."""
    records = layer_catalog if layer_catalog is not None else load_catalog_records(schema_name)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for record in records:
        if not record.get("is_verified") or record.get("is_group_layer") or not record.get("is_active", True):
            continue
        blob = _text_blob(record)
        geometry_type = str(record.get("geometry_type") or "").lower()
        if "line" not in geometry_type and "polyline" not in geometry_type:
            continue
        score = 0
        for term in ["street", "streets", "road", "roads", "centerline", "centerlines"]:
            if term in blob:
                score += 10
        if "transportation" in blob:
            score += 4
        if record.get("source_status") == "active":
            score += 2
        if score > 0:
            candidates.append((score, record))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item[0], int(item[1].get("source_priority") or 99)))[0][1]


def _line_paths(feature: dict[str, Any]) -> list[list[tuple[float, float]]]:
    geometry = feature.get("geometry") or {}
    coordinates = geometry.get("coordinates") or []
    if geometry.get("type") == "LineString" and isinstance(coordinates, list):
        return [[(float(x), float(y)) for x, y, *_ in coordinates if x is not None and y is not None]]
    if geometry.get("type") == "MultiLineString" and isinstance(coordinates, list):
        paths: list[list[tuple[float, float]]] = []
        for path in coordinates:
            if isinstance(path, list):
                paths.append([(float(x), float(y)) for x, y, *_ in path if x is not None and y is not None])
        return paths
    return []


def _node_key(point: tuple[float, float]) -> tuple[float, float]:
    return (round(point[0], 6), round(point[1], 6))


def _nearest_node(point: tuple[float, float], nodes: dict[tuple[float, float], tuple[float, float]]) -> tuple[float, float]:
    if not nodes:
        raise RouteDraftError("No road graph nodes were available.")
    return min(nodes, key=lambda node: _haversine_miles(point, nodes[node]))


def _build_graph(features: list[dict[str, Any]]) -> tuple[dict[tuple[float, float], tuple[float, float]], dict[tuple[float, float], list[tuple[tuple[float, float], float]]]]:
    nodes: dict[tuple[float, float], tuple[float, float]] = {}
    graph: dict[tuple[float, float], list[tuple[tuple[float, float], float]]] = {}
    for feature in features:
        for path in _line_paths(feature):
            if len(path) < 2:
                continue
            for first, second in zip(path, path[1:]):
                first_key = _node_key(first)
                second_key = _node_key(second)
                nodes[first_key] = first
                nodes[second_key] = second
                weight = _haversine_miles(first, second)
                graph.setdefault(first_key, []).append((second_key, weight))
                graph.setdefault(second_key, []).append((first_key, weight))
    if not graph:
        raise RouteDraftError("No usable street centerline graph was built from bounded road features.")
    return nodes, graph


def _shortest_path(
    graph: dict[tuple[float, float], list[tuple[tuple[float, float], float]]],
    start: tuple[float, float],
    end: tuple[float, float],
) -> tuple[list[tuple[float, float]], float]:
    queue: list[tuple[float, tuple[float, float], list[tuple[float, float]]]] = [(0.0, start, [start])]
    visited: set[tuple[float, float]] = set()
    while queue:
        distance, node, path = heapq.heappop(queue)
        if node in visited:
            continue
        if node == end:
            return path, distance
        visited.add(node)
        for neighbor, weight in graph.get(node, []):
            if neighbor not in visited:
                heapq.heappush(queue, (distance + weight, neighbor, [*path, neighbor]))
    raise RouteDraftError("Road graph did not connect the origin and target within the bounded corridor.")


def _route_feature(
    coordinates: list[tuple[float, float]],
    *,
    distance_miles: float,
    target_type: str,
    target_layer_key: str | None,
) -> dict[str, Any]:
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[lon, lat] for lon, lat in coordinates]},
        "properties": {
            "automap_line_type": "road_following_draft",
            "route_mode": "road_network",
            "target_type": target_type,
            "target_layer_key": target_layer_key,
            "distance_miles": round(distance_miles, 3),
            "label": "Road-following draft route",
            "not_official_directions": True,
        },
    }


def build_road_following_draft(
    origin_feature: dict[str, Any],
    target_feature: dict[str, Any],
    *,
    target_type: str,
    target_layer_key: str | None = None,
    client: SpatialQueryClient | None = None,
    layer_catalog: list[dict[str, Any]] | None = None,
    schema_name: str = "automap",
    max_road_features: int = MAX_ROAD_FEATURES,
) -> RouteDraftResult:
    """Try to build a bounded road-following draft from street centerlines."""
    straight_line = build_straight_line_geojson(
        origin_feature,
        target_feature,
        properties={
            "target_type": target_type,
            "target_layer_key": target_layer_key,
            "label": "Straight-line fallback",
            "route_mode": "straight_line_fallback",
        },
    )
    try:
        origin = _point_coordinates(origin_feature)
        target = _point_coordinates(target_feature)
        envelope = _route_extent(origin, target)
        street_layer = find_street_centerline_layer(layer_catalog=layer_catalog, schema_name=schema_name)
        if not street_layer:
            raise RouteDraftError("No verified Streets/Centerlines layer is available for a road-following draft.")
        layer_url = street_layer.get("layer_url") or street_layer.get("rest_url")
        if not layer_url:
            raise RouteDraftError("Verified Streets/Centerlines layer has no REST layer URL.")
        query_client = client or SpatialQueryClient(max_features=max_road_features, hard_max_features=HARD_MAX_ROAD_FEATURES)
        count_result = query_client.query_count(
            layer_url,
            geometry=envelope,
            geometry_type="esriGeometryEnvelope",
            spatial_rel="esriSpatialRelIntersects",
        )
        count = int(count_result.get("count") or 0)
        if count <= 0:
            raise RouteDraftError("No street centerline features were found in the bounded route corridor.")
        if count > max_road_features:
            raise RouteDraftError(f"Bounded route corridor returned {count} road features, above max {max_road_features}.")
        features_result = query_client.query_features(
            layer_url,
            geometry=envelope,
            geometry_type="esriGeometryEnvelope",
            spatial_rel="esriSpatialRelIntersects",
            out_fields="*",
            return_geometry=True,
            result_record_count=count,
        )
        features = features_result.get("features") or []
        nodes, graph = _build_graph(features)
        start_node = _nearest_node(origin, nodes)
        end_node = _nearest_node(target, nodes)
        path_nodes, road_distance = _shortest_path(graph, start_node, end_node)
        path_coordinates = [origin, *[nodes[node] for node in path_nodes], target]
        route = _route_feature(
            path_coordinates,
            distance_miles=road_distance + _haversine_miles(origin, nodes[start_node]) + _haversine_miles(nodes[end_node], target),
            target_type=target_type,
            target_layer_key=target_layer_key,
        )
        return RouteDraftResult(
            route_mode="road_network",
            route_label="Road-following draft route",
            route_warning=ROAD_FOLLOWING_DRAFT_WARNING,
            route_geojson={"type": "FeatureCollection", "features": [route]},
            straight_line_geojson={"type": "FeatureCollection", "features": [straight_line]},
            route_distance_miles=route["properties"]["distance_miles"],
            road_feature_count=count,
            target_layer_key=street_layer.get("layer_key"),
            warnings=[ROAD_FOLLOWING_DRAFT_WARNING],
            metadata={
                "street_layer_key": street_layer.get("layer_key"),
                "route_search_extent": envelope,
                "road_feature_limit": max_road_features,
            },
        )
    except Exception as exc:
        warning = f"{STRAIGHT_LINE_FALLBACK_WARNING} Road-following draft unavailable: {exc}"
        return RouteDraftResult(
            route_mode="straight_line_fallback",
            route_label="Straight-line fallback",
            route_warning=warning,
            straight_line_geojson={"type": "FeatureCollection", "features": [straight_line]},
            warnings=[warning],
            metadata={"fallback_reason": str(exc)},
        )
