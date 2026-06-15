"""Bounded ArcGIS REST feature queries for local AutoMap analysis."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.analysis_models import DEFAULT_MAX_FEATURES, HARD_MAX_FEATURES
from app.arcgis_rest_inspector import fetch_json


class SpatialQueryError(RuntimeError):
    """Raised when a bounded spatial query cannot be completed safely."""


GET_URL_LENGTH_LIMIT = 1800


def _bounded_limit(value: int | None, *, hard_max: int = HARD_MAX_FEATURES) -> int:
    if value is None:
        return DEFAULT_MAX_FEATURES
    try:
        selected = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("result_record_count must be an integer.") from exc
    if selected < 1:
        raise ValueError("result_record_count must be positive.")
    if selected > hard_max:
        raise ValueError(f"result_record_count exceeds hard max of {hard_max}.")
    return selected


def _layer_query_url(layer_url: str, params: dict[str, Any]) -> str:
    clean_params = {
        key: json.dumps(value) if isinstance(value, (dict, list)) else value
        for key, value in params.items()
        if value is not None
    }
    return f"{layer_url.rstrip('/')}/query?{urlencode(clean_params)}"


def _encoded_params(params: dict[str, Any]) -> str:
    clean_params = {
        key: json.dumps(value) if isinstance(value, (dict, list)) else value
        for key, value in params.items()
        if value is not None
    }
    return urlencode(clean_params)


def _fetch_json_or_geojson(
    url: str,
    *,
    data: bytes | None = None,
    timeout: int = 30,
) -> dict[str, Any]:
    headers = {"User-Agent": "AutoMap Spatial Query Client"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    request = Request(url, data=data, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
    except HTTPError as exc:
        raise SpatialQueryError(f"HTTP {exc.code} for bounded ArcGIS query.") from exc
    except URLError as exc:
        raise SpatialQueryError(f"Unable to run bounded ArcGIS query: {exc.reason}") from exc
    except TimeoutError as exc:
        raise SpatialQueryError("Timed out running bounded ArcGIS query.") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SpatialQueryError("ArcGIS query did not return valid JSON.") from exc
    if not isinstance(data, dict):
        raise SpatialQueryError("ArcGIS query returned non-object JSON.")
    if "error" in data:
        error = data["error"]
        message = error.get("message", "ArcGIS REST query error") if isinstance(error, dict) else str(error)
        details = error.get("details") if isinstance(error, dict) else None
        raise SpatialQueryError(f"{message}: {details or 'no details'}")
    return data


def _fetch_layer_query(
    layer_url: str,
    params: dict[str, Any],
    *,
    prefer_post: bool = False,
    timeout: int = 30,
) -> tuple[dict[str, Any], dict[str, Any]]:
    encoded = _encoded_params(params)
    query_endpoint = f"{layer_url.rstrip('/')}/query"
    get_url = f"{query_endpoint}?{encoded}"
    use_post = prefer_post or len(get_url) > GET_URL_LENGTH_LIMIT
    if use_post:
        data = _fetch_json_or_geojson(query_endpoint, data=encoded.encode("utf-8"), timeout=timeout)
        return data, {"request_method": "POST", "url_length": len(query_endpoint), "payload_length": len(encoded)}
    try:
        data = _fetch_json_or_geojson(get_url, timeout=timeout)
    except TypeError:
        # Some unit tests monkeypatch the low-level fetch with a one-argument stub.
        data = _fetch_json_or_geojson(get_url)  # type: ignore[call-arg]
    return data, {"request_method": "GET", "url_length": len(get_url), "payload_length": len(encoded)}


def _arcgis_geometry_to_geojson(geometry: dict[str, Any] | None, geometry_type: str | None) -> dict[str, Any] | None:
    """Convert the small subset of ArcGIS JSON geometries AutoMap needs into GeoJSON."""
    if not isinstance(geometry, dict):
        return None
    if "x" in geometry and "y" in geometry:
        return {"type": "Point", "coordinates": [geometry["x"], geometry["y"]]}
    if "paths" in geometry:
        paths = geometry.get("paths") or []
        if len(paths) == 1:
            return {"type": "LineString", "coordinates": paths[0]}
        return {"type": "MultiLineString", "coordinates": paths}
    if "rings" in geometry:
        rings = geometry.get("rings") or []
        if not rings:
            return None
        return {"type": "Polygon", "coordinates": rings}
    if geometry_type == "esriGeometryEnvelope" and {"xmin", "ymin", "xmax", "ymax"}.issubset(geometry):
        xmin, ymin, xmax, ymax = geometry["xmin"], geometry["ymin"], geometry["xmax"], geometry["ymax"]
        return {
            "type": "Polygon",
            "coordinates": [[[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax], [xmin, ymin]]],
        }
    return None


def _geojson_geometry_to_arcgis(geometry: dict[str, Any] | None) -> tuple[dict[str, Any] | None, str | None]:
    """Convert GeoJSON geometry into ArcGIS REST geometry JSON."""
    if not isinstance(geometry, dict):
        return geometry, None
    if {"xmin", "ymin", "xmax", "ymax"}.issubset(geometry):
        return geometry, "esriGeometryEnvelope"
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point" and isinstance(coordinates, list):
        return {"x": coordinates[0], "y": coordinates[1], "spatialReference": {"wkid": 4326}}, "esriGeometryPoint"
    if geometry_type == "LineString" and isinstance(coordinates, list):
        return {"paths": [coordinates], "spatialReference": {"wkid": 4326}}, "esriGeometryPolyline"
    if geometry_type == "MultiLineString" and isinstance(coordinates, list):
        return {"paths": coordinates, "spatialReference": {"wkid": 4326}}, "esriGeometryPolyline"
    if geometry_type == "Polygon" and isinstance(coordinates, list):
        return {"rings": coordinates, "spatialReference": {"wkid": 4326}}, "esriGeometryPolygon"
    if geometry_type == "MultiPolygon" and isinstance(coordinates, list):
        rings: list[Any] = []
        for polygon in coordinates:
            if isinstance(polygon, list):
                rings.extend(polygon)
        return {"rings": rings, "spatialReference": {"wkid": 4326}}, "esriGeometryPolygon"
    return geometry, None


def _normalize_geometry(
    geometry: dict[str, Any] | None,
    geometry_type: str | None,
) -> tuple[dict[str, Any] | None, str | None]:
    if not geometry:
        return None, geometry_type
    if geometry.get("type") == "Feature":
        geometry = geometry.get("geometry")
    converted, inferred_type = _geojson_geometry_to_arcgis(geometry)
    return converted, geometry_type or inferred_type


def _arcgis_response_to_feature_collection(data: dict[str, Any]) -> dict[str, Any]:
    """Convert ArcGIS feature JSON into a GeoJSON FeatureCollection."""
    if data.get("type") == "FeatureCollection":
        features = data.get("features") if isinstance(data.get("features"), list) else []
        return {"type": "FeatureCollection", "features": features}
    geometry_type = data.get("geometryType")
    features: list[dict[str, Any]] = []
    for feature in data.get("features") or []:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("attributes") if isinstance(feature.get("attributes"), dict) else feature.get("properties") or {}
        geometry = _arcgis_geometry_to_geojson(feature.get("geometry"), geometry_type)
        features.append({"type": "Feature", "geometry": geometry, "properties": properties})
    return {"type": "FeatureCollection", "features": features}


def _chunked(values: list[Any], size: int) -> list[list[Any]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


class SpatialQueryClient:
    """Small bounded client for ArcGIS REST analysis queries."""

    def __init__(self, *, max_features: int = DEFAULT_MAX_FEATURES, hard_max_features: int = HARD_MAX_FEATURES) -> None:
        self.max_features = _bounded_limit(max_features, hard_max=hard_max_features)
        self.hard_max_features = hard_max_features

    def get_layer_metadata(self, layer_url: str) -> dict[str, Any]:
        """Return layer metadata without feature geometry."""
        return fetch_json(layer_url)

    def query_count(
        self,
        layer_url: str,
        *,
        where: str | None = None,
        geometry: dict[str, Any] | None = None,
        geometry_type: str | None = None,
        spatial_rel: str | None = None,
    ) -> dict[str, Any]:
        """Run a count-only query with returnGeometry=false."""
        geometry, geometry_type = _normalize_geometry(geometry, geometry_type)
        params = {
            "f": "pjson",
            "where": where or "1=1",
            "returnCountOnly": "true",
            "returnGeometry": "false",
            "geometry": geometry,
            "geometryType": geometry_type,
            "inSR": 4326 if geometry else None,
            "spatialRel": spatial_rel,
        }
        data, request_metadata = _fetch_layer_query(layer_url, params, timeout=60)
        count = data.get("count")
        if not isinstance(count, int):
            raise SpatialQueryError("Count query response did not include an integer count.")
        return {
            "count": count,
            "where": where or "1=1",
            "geometry_used": bool(geometry),
            "return_geometry": False,
            **request_metadata,
        }

    def query_object_ids(
        self,
        layer_url: str,
        *,
        where: str | None = None,
        geometry: dict[str, Any] | None = None,
        geometry_type: str | None = None,
        spatial_rel: str | None = None,
    ) -> dict[str, Any]:
        """Return object IDs for a bounded query without feature geometry."""
        geometry, geometry_type = _normalize_geometry(geometry, geometry_type)
        params = {
            "f": "pjson",
            "where": where or "1=1",
            "returnIdsOnly": "true",
            "returnGeometry": "false",
            "geometry": geometry,
            "geometryType": geometry_type,
            "inSR": 4326 if geometry else None,
            "spatialRel": spatial_rel,
        }
        data, request_metadata = _fetch_layer_query(layer_url, params, timeout=60)
        object_ids = data.get("objectIds") or []
        if not isinstance(object_ids, list):
            raise SpatialQueryError("Object ID query response did not include objectIds.")
        return {
            "object_id_field": data.get("objectIdFieldName"),
            "object_ids": object_ids,
            "object_id_count": len(object_ids),
            "where": where or "1=1",
            "geometry_used": bool(geometry),
            "return_geometry": False,
            **request_metadata,
        }

    def query_features_by_object_ids(
        self,
        layer_url: str,
        *,
        object_ids: list[Any],
        out_fields: str,
        return_geometry: bool,
        batch_size: int = 100,
        result_record_count: int | None = None,
    ) -> dict[str, Any]:
        """Fetch bounded features by explicit object IDs."""
        limit = _bounded_limit(result_record_count or self.max_features, hard_max=self.hard_max_features)
        if len(object_ids) > limit:
            return {
                "status": "blocked",
                "features": [],
                "feature_collection": {"type": "FeatureCollection", "features": []},
                "count": len(object_ids),
                "limit": limit,
                "blocked_reason": f"Object ID count {len(object_ids)} exceeds max feature limit {limit}.",
                "query_metadata": {
                    "request_method": "not_sent",
                    "object_id_count": len(object_ids),
                    "return_geometry": return_geometry,
                },
            }
        all_features: list[dict[str, Any]] = []
        geometry_type: str | None = None
        methods: list[str] = []
        for batch in _chunked(object_ids, batch_size):
            params = {
                "f": "pjson",
                "objectIds": ",".join(str(value) for value in batch),
                "outFields": out_fields,
                "returnGeometry": "true" if return_geometry else "false",
                "outSR": 4326 if return_geometry else None,
            }
            data, metadata = _fetch_layer_query(layer_url, params, timeout=60)
            methods.append(metadata["request_method"])
            geometry_type = geometry_type or data.get("geometryType")
            all_features.extend(data.get("features") or [])
        collection = _arcgis_response_to_feature_collection({"geometryType": geometry_type, "features": all_features})
        return {
            "status": "ok",
            "geometryType": geometry_type,
            "features": collection["features"],
            "feature_collection": collection,
            "count": len(object_ids),
            "limit": limit,
            "query_metadata": {
                "request_methods": sorted(set(methods)),
                "object_id_count": len(object_ids),
                "batch_count": len(_chunked(object_ids, batch_size)),
                "return_geometry": return_geometry,
                "format": "pjson_object_id_batches",
            },
        }

    def query_features(
        self,
        layer_url: str,
        *,
        where: str | None = None,
        geometry: dict[str, Any] | None = None,
        geometry_type: str | None = None,
        spatial_rel: str | None = None,
        out_fields: str = "*",
        return_geometry: bool = True,
        result_record_count: int | None = None,
    ) -> dict[str, Any]:
        """Query bounded feature results, preferring ArcGIS GeoJSON output."""
        limit = _bounded_limit(result_record_count or self.max_features, hard_max=self.hard_max_features)
        geometry, geometry_type = _normalize_geometry(geometry, geometry_type)
        count_result = self.query_count(
            layer_url,
            where=where,
            geometry=geometry,
            geometry_type=geometry_type,
            spatial_rel=spatial_rel,
        )
        count = int(count_result["count"])
        if count > limit:
            return {
                "status": "blocked",
                "features": [],
                "feature_collection": {"type": "FeatureCollection", "features": []},
                "count": count,
                "limit": limit,
                "blocked_reason": f"Query count {count} exceeds max feature limit {limit}.",
                "query_metadata": {
                    "where": where or "1=1",
                    "return_geometry": return_geometry,
                    "geometry_used": bool(geometry),
                    "spatial_rel": spatial_rel,
                },
            }

        params = {
            "f": "geojson" if return_geometry else "pjson",
            "where": where or "1=1",
            "outFields": out_fields,
            "returnGeometry": "true" if return_geometry else "false",
            "geometry": geometry,
            "geometryType": geometry_type,
            "inSR": 4326 if geometry else None,
            "outSR": 4326 if return_geometry else None,
            "spatialRel": spatial_rel,
            "resultRecordCount": limit,
        }
        format_used = params["f"]
        fallback_warning = None
        request_metadata: dict[str, Any]
        try:
            data, request_metadata = _fetch_layer_query(layer_url, params, timeout=60)
        except SpatialQueryError as exc:
            fallback_warning = str(exc)
            id_result = self.query_object_ids(
                layer_url,
                where=where,
                geometry=geometry,
                geometry_type=geometry_type,
                spatial_rel=spatial_rel,
            )
            object_id_result = self.query_features_by_object_ids(
                layer_url,
                object_ids=id_result["object_ids"],
                out_fields=out_fields,
                return_geometry=return_geometry,
                result_record_count=limit,
            )
            data = {
                "type": "FeatureCollection",
                "features": object_id_result.get("features") or [],
            }
            format_used = "pjson_object_id_batches"
            request_metadata = {
                "request_method": "GET/POST",
                "object_id_request_method": id_result.get("request_method"),
                "feature_request_methods": (object_id_result.get("query_metadata") or {}).get("request_methods"),
            }
        collection = _arcgis_response_to_feature_collection(data)
        features = collection["features"]
        return {
            "status": "ok",
            "features": features,
            "feature_collection": collection,
            "count": count,
            "limit": limit,
            "query_metadata": {
                "where": where or "1=1",
                "out_fields": out_fields,
                "return_geometry": return_geometry,
                "geometry_used": bool(geometry),
                "spatial_rel": spatial_rel,
                "format": format_used,
                "fallback_warning": fallback_warning,
                **request_metadata,
            },
        }

    def query_distinct_values(self, layer_url: str, field_name: str) -> dict[str, Any]:
        """Return distinct values for one field without geometry."""
        params = {
            "f": "pjson",
            "where": "1=1",
            "outFields": field_name,
            "returnDistinctValues": "true",
            "returnGeometry": "false",
            "orderByFields": field_name,
            "resultRecordCount": min(self.max_features, 500),
        }
        data, request_metadata = _fetch_layer_query(layer_url, params)
        values = []
        for feature in data.get("features") or []:
            attributes = feature.get("attributes") or {}
            if field_name in attributes:
                values.append(attributes[field_name])
        return {"field_name": field_name, "values": values, "count": len(values), **request_metadata}

    def query_grouped_statistics(
        self,
        layer_url: str,
        field_name: str,
        *,
        where: str | None = None,
        max_groups: int = 50,
    ) -> dict[str, Any]:
        """Return grouped count statistics without feature geometry."""
        statistic_field = "*"
        params = {
            "f": "pjson",
            "where": where or "1=1",
            "outStatistics": [
                {
                    "statisticType": "count",
                    "onStatisticField": statistic_field,
                    "outStatisticFieldName": "feature_count",
                }
            ],
            "groupByFieldsForStatistics": field_name,
            "orderByFields": "feature_count DESC",
            "returnGeometry": "false",
            "resultRecordCount": min(max_groups, 200),
        }
        data, request_metadata = _fetch_layer_query(layer_url, params, timeout=60)
        rows: list[dict[str, Any]] = []
        for feature in data.get("features") or []:
            attributes = feature.get("attributes") or {}
            rows.append(
                {
                    "group_value": attributes.get(field_name),
                    "feature_count": attributes.get("feature_count"),
                }
            )
        return {
            "field_name": field_name,
            "where": where or "1=1",
            "return_geometry": False,
            "rows": rows,
            "group_count": len(rows),
            **request_metadata,
        }

    def get_extent(self, layer_url: str) -> dict[str, Any] | None:
        """Return layer extent metadata."""
        metadata = self.get_layer_metadata(layer_url)
        extent = metadata.get("extent")
        return extent if isinstance(extent, dict) else None
