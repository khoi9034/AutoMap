"""Small GeoJSON/Shapely utilities for bounded AutoMap analysis."""

from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Any

from shapely.errors import GEOSException
from shapely.geometry import GeometryCollection, mapping, shape
from shapely.ops import transform, unary_union
from shapely.validation import make_valid

try:
    from pyproj import Transformer
except Exception:  # pragma: no cover - pyproj is expected in the local env.
    Transformer = None  # type: ignore[assignment]


class GeometrySafetyError(RuntimeError):
    """Raised when local geometry work would be unsafe or ambiguous."""


def load_geojson_features(source: str | Path | dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Load GeoJSON features from a path, FeatureCollection, feature, or list."""
    if isinstance(source, (str, Path)):
        data = json.loads(Path(source).read_text(encoding="utf-8"))
    else:
        data = source
    if isinstance(data, list):
        return [feature for feature in data if isinstance(feature, dict)]
    if isinstance(data, dict) and data.get("type") == "FeatureCollection":
        features = data.get("features")
        return [feature for feature in features if isinstance(feature, dict)] if isinstance(features, list) else []
    if isinstance(data, dict) and data.get("type") == "Feature":
        return [data]
    raise GeometrySafetyError("Expected GeoJSON FeatureCollection, Feature, feature list, or path.")


def _feature_geometry(feature: dict[str, Any]):
    geometry = feature.get("geometry")
    if not geometry:
        return None
    try:
        geom = shape(geometry)
    except Exception as exc:
        raise GeometrySafetyError("Feature geometry could not be parsed safely.") from exc
    if geom.is_empty:
        return None
    if not geom.is_valid:
        try:
            geom = make_valid(geom)
        except Exception as exc:
            raise GeometrySafetyError("Feature geometry is invalid and could not be repaired safely.") from exc
        if geom.is_empty:
            return None
    return geom


def _union(features: list[dict[str, Any]]):
    geometries = [_feature_geometry(feature) for feature in features]
    geometries = [geometry for geometry in geometries if geometry is not None]
    if not geometries:
        return GeometryCollection()
    try:
        return unary_union(geometries)
    except GEOSException as exc:
        raise GeometrySafetyError("Feature geometries could not be unioned safely for local analysis.") from exc


def _crs_name(feature_collection: dict[str, Any] | None) -> str | None:
    if not isinstance(feature_collection, dict):
        return None
    crs = feature_collection.get("crs")
    if isinstance(crs, dict):
        properties = crs.get("properties")
        if isinstance(properties, dict) and properties.get("name"):
            return str(properties["name"])
    return None


def reproject_if_needed(
    feature_collection: dict[str, Any],
    *,
    source_epsg: int | None = None,
    target_epsg: int = 4326,
) -> dict[str, Any]:
    """Reproject a FeatureCollection when an explicit source EPSG is supplied."""
    if not source_epsg or source_epsg == target_epsg:
        return feature_collection
    if Transformer is None:
        raise GeometrySafetyError("pyproj is unavailable; cannot safely reproject analysis geometries.")
    transformer = Transformer.from_crs(f"EPSG:{source_epsg}", f"EPSG:{target_epsg}", always_xy=True)
    transformed_features: list[dict[str, Any]] = []
    for feature in load_geojson_features(feature_collection):
        copied = deepcopy(feature)
        geom = _feature_geometry(feature)
        if geom is None:
            continue
        copied["geometry"] = mapping(transform(transformer.transform, geom))
        transformed_features.append(copied)
    return {"type": "FeatureCollection", "features": transformed_features}


def assert_compatible_geojson_crs(
    first: dict[str, Any] | None,
    second: dict[str, Any] | None,
) -> None:
    """Stop if two GeoJSON collections explicitly disagree about CRS."""
    first_crs = _crs_name(first)
    second_crs = _crs_name(second)
    if first_crs and second_crs and first_crs != second_crs:
        raise GeometrySafetyError(f"Incompatible GeoJSON CRS values: {first_crs} != {second_crs}.")


def filter_features_by_polygon(
    target_features: list[dict[str, Any]],
    polygon_features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return target features that intersect the union of polygon features."""
    boundary = _union(polygon_features)
    if boundary.is_empty:
        return []
    selected: list[dict[str, Any]] = []
    for feature in target_features:
        geometry = _feature_geometry(feature)
        try:
            intersects = geometry is not None and geometry.intersects(boundary)
        except GEOSException as exc:
            raise GeometrySafetyError("Feature intersection could not be evaluated safely.") from exc
        if intersects:
            selected.append(deepcopy(feature))
    return selected


def intersect_features(
    target_features: list[dict[str, Any]],
    overlay_features: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return target features whose geometry intersects overlay geometries."""
    overlay = _union(overlay_features)
    if overlay.is_empty:
        return []
    selected: list[dict[str, Any]] = []
    for feature in target_features:
        geometry = _feature_geometry(feature)
        try:
            intersects = geometry is not None and geometry.intersects(overlay)
        except GEOSException as exc:
            raise GeometrySafetyError("Feature intersection could not be evaluated safely.") from exc
        if not intersects:
            continue
        copied = deepcopy(feature)
        properties = copied.setdefault("properties", {})
        if isinstance(properties, dict):
            properties["automap_selected"] = True
            properties["automap_selection_reason"] = "intersects constraint layer"
        selected.append(copied)
    return selected


def feature_collection_to_geojson(features: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap features in a GeoJSON FeatureCollection."""
    return {"type": "FeatureCollection", "features": features}


def compute_basic_stats(features: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute small safe stats for a bounded feature list."""
    geometry_types: dict[str, int] = {}
    bounds: list[float] | None = None
    for feature in features:
        geometry = _feature_geometry(feature)
        if geometry is None:
            continue
        geometry_types[geometry.geom_type] = geometry_types.get(geometry.geom_type, 0) + 1
        geom_bounds = list(geometry.bounds)
        if bounds is None:
            bounds = geom_bounds
        else:
            bounds = [
                min(bounds[0], geom_bounds[0]),
                min(bounds[1], geom_bounds[1]),
                max(bounds[2], geom_bounds[2]),
                max(bounds[3], geom_bounds[3]),
            ]
    return {"feature_count": len(features), "geometry_types": geometry_types, "bounds": bounds}


def geojson_extent(source: str | Path | dict[str, Any] | list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return a WGS84 extent for a bounded local GeoJSON source."""
    features = load_geojson_features(source)
    bounds = compute_basic_stats(features).get("bounds")
    if not bounds or len(bounds) != 4:
        return None
    return {
        "xmin": float(bounds[0]),
        "ymin": float(bounds[1]),
        "xmax": float(bounds[2]),
        "ymax": float(bounds[3]),
        "spatialReference": {"wkid": 4326},
    }


def buffer_extent(
    extent: dict[str, Any] | None,
    *,
    ratio: float = 0.18,
    minimum: float = 0.001,
) -> dict[str, Any] | None:
    """Return a small buffered extent for parcel-focused preview maps."""
    if not isinstance(extent, dict):
        return None
    try:
        xmin = float(extent["xmin"])
        ymin = float(extent["ymin"])
        xmax = float(extent["xmax"])
        ymax = float(extent["ymax"])
    except (KeyError, TypeError, ValueError):
        return None
    width = max(abs(xmax - xmin), minimum)
    height = max(abs(ymax - ymin), minimum)
    buffer_x = max(width * ratio, minimum)
    buffer_y = max(height * ratio, minimum)
    buffered = {
        "xmin": xmin - buffer_x,
        "ymin": ymin - buffer_y,
        "xmax": xmax + buffer_x,
        "ymax": ymax + buffer_y,
    }
    spatial_reference = extent.get("spatialReference") or extent.get("spatial_reference") or {"wkid": 4326}
    if isinstance(spatial_reference, dict):
        buffered["spatialReference"] = spatial_reference
    return buffered


def make_safe_geojson_output(
    features: list[dict[str, Any]],
    *,
    max_features: int,
    name: str,
) -> dict[str, Any]:
    """Create a safe GeoJSON output with AutoMap metadata and feature cap checks."""
    if len(features) > max_features:
        raise GeometrySafetyError(f"Output feature count {len(features)} exceeds max {max_features}.")
    return {
        "type": "FeatureCollection",
        "name": name,
        "features": features,
        "automap": {
            "derived_local_analysis_result": True,
            "feature_count": len(features),
            "not_published": True,
        },
    }


def make_generalized_display_geojson(
    source: str | Path | dict[str, Any] | list[dict[str, Any]],
    *,
    max_features: int,
    name: str,
    display_mode: str,
    simplify_tolerance: float = 0,
) -> dict[str, Any]:
    """Dissolve dense polygon results for display while preserving analysis features elsewhere."""
    features = load_geojson_features(source)
    if len(features) > max_features:
        raise GeometrySafetyError(f"Display source feature count {len(features)} exceeds max {max_features}.")
    dissolved = _union(features)
    if dissolved.is_empty:
        return make_safe_geojson_output(features, max_features=max_features, name=name)
    if simplify_tolerance:
        try:
            dissolved = dissolved.simplify(float(simplify_tolerance), preserve_topology=True)
        except GEOSException as exc:
            raise GeometrySafetyError("Display geometry could not be simplified safely.") from exc
    return {
        "type": "FeatureCollection",
        "name": name,
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "automap_display_generalized": True,
                    "automap_display_mode": display_mode,
                    "automap_source_feature_count": len(features),
                },
                "geometry": mapping(dissolved),
            }
        ],
        "automap": {
            "derived_local_analysis_result": True,
            "display_generalized": True,
            "display_mode": display_mode,
            "source_feature_count": len(features),
            "display_feature_count": 1,
            "not_published": True,
        },
    }


def compute_origin_point(feature: dict[str, Any]) -> dict[str, Any]:
    """Return a GeoJSON point for a feature point or polygon centroid."""
    geometry = _feature_geometry(feature)
    if geometry is None:
        raise GeometrySafetyError("Origin feature does not have usable geometry.")
    point = geometry if geometry.geom_type == "Point" else geometry.centroid
    return {"type": "Point", "coordinates": [point.x, point.y]}


def _point_coordinates(feature: dict[str, Any]) -> tuple[float, float]:
    point = compute_origin_point(feature)
    coordinates = point.get("coordinates")
    if not isinstance(coordinates, list) or len(coordinates) < 2:
        raise GeometrySafetyError("Feature point coordinates are unavailable.")
    return float(coordinates[0]), float(coordinates[1])


def _haversine_miles(first: tuple[float, float], second: tuple[float, float]) -> float:
    """Return approximate WGS84 great-circle distance in miles."""
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


def compute_straight_line_distance(
    origin_feature: dict[str, Any],
    target_feature: dict[str, Any],
    *,
    unit: str = "miles",
) -> float:
    """Compute a straight-line distance between two GeoJSON features."""
    distance_miles = _haversine_miles(_point_coordinates(origin_feature), _point_coordinates(target_feature))
    if unit == "feet":
        return round(distance_miles * 5280, 2)
    if unit == "meters":
        return round(distance_miles * 1609.344, 2)
    return round(distance_miles, 3)


def compute_nearest_feature(
    origin_feature: dict[str, Any],
    target_features: list[dict[str, Any]],
    *,
    unit: str = "miles",
) -> dict[str, Any] | None:
    """Return the nearest target feature and distance metadata."""
    nearest: dict[str, Any] | None = None
    nearest_distance: float | None = None
    for feature in target_features:
        distance = compute_straight_line_distance(origin_feature, feature, unit=unit)
        if nearest_distance is None or distance < nearest_distance:
            nearest = feature
            nearest_distance = distance
    if nearest is None:
        return None
    return {"feature": nearest, "distance": nearest_distance, "distance_unit": unit}


def build_straight_line_geojson(
    origin_feature: dict[str, Any],
    target_feature: dict[str, Any],
    *,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a one-feature GeoJSON line between origin and target points."""
    origin = _point_coordinates(origin_feature)
    target = _point_coordinates(target_feature)
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[origin[0], origin[1]], [target[0], target[1]]]},
        "properties": {
            "automap_line_type": "straight_line_distance",
            "not_a_road_route": True,
            **(properties or {}),
        },
    }


def build_proximity_result_geojson(
    origin_feature: dict[str, Any],
    target_feature: dict[str, Any],
    line_feature: dict[str, Any],
) -> dict[str, Any]:
    """Build a FeatureCollection with origin, target, and straight-line result."""
    origin = deepcopy(origin_feature)
    target = deepcopy(target_feature)
    origin.setdefault("properties", {})["automap_role"] = "origin"
    target.setdefault("properties", {})["automap_role"] = "target"
    return {
        "type": "FeatureCollection",
        "features": [origin, target, line_feature],
        "automap": {
            "derived_local_proximity_result": True,
            "published": False,
            "line_type": "straight_line_distance",
        },
    }


def geojson_envelope(features: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return an Esri envelope JSON in WGS84 for REST spatial queries."""
    union_geometry = _union(features)
    if union_geometry.is_empty:
        return None
    xmin, ymin, xmax, ymax = union_geometry.bounds
    return {
        "xmin": xmin,
        "ymin": ymin,
        "xmax": xmax,
        "ymax": ymax,
        "spatialReference": {"wkid": 4326},
    }
