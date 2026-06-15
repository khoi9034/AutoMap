"""Small GeoJSON/Shapely utilities for bounded AutoMap analysis."""

from __future__ import annotations

from copy import deepcopy
import json
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
