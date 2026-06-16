"""Safe proximity and nearest-facility workflows for AutoMap."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.address_field_mapper import build_verified_address_field_map
from app.address_parcel_resolver import ADDRESS_NOT_MATCHED_WARNING, looks_like_address
from app.db import _quote_identifier, get_engine
from app.geometry_utils import (
    GeometrySafetyError,
    build_proximity_result_geojson,
    build_straight_line_geojson,
    compute_nearest_feature,
    compute_origin_point,
    load_geojson_features,
)
from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import slugify
from app.parcel_context_engine import create_parcel_set, fetch_selected_parcels, get_parcel_set
from app.parcel_input_parser import parse_parcel_input
from app.proximity_models import (
    DEFAULT_MAX_ORIGIN_FEATURES,
    DISTANCE_RINGS_MILES,
    HARD_MAX_TARGET_CANDIDATES,
    MAX_TARGET_CANDIDATES,
    PROXIMITY_OUTPUT_ROOT,
    ROUTE_WARNING,
    ProximityRequest,
)
from app.proximity_reporter import write_proximity_report
from app.spatial_query_client import SpatialQueryClient, SpatialQueryError
from app.ui_models import output_file_url, repo_root


def _requests_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.proximity_requests"


def _results_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.proximity_results"


def init_proximity_tables(schema_name: str = "automap") -> None:
    """Create additive proximity tables in the AutoMap schema only."""
    requests_table = _requests_table(schema_name)
    results_table = _results_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {requests_table} (
                    id serial PRIMARY KEY,
                    proximity_request_id text UNIQUE,
                    raw_prompt text,
                    origin_input text,
                    origin_type text,
                    target_type text,
                    target_layer_key text,
                    destination_input text,
                    request_json jsonb DEFAULT '{{}}'::jsonb,
                    status text,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {results_table} (
                    id serial PRIMARY KEY,
                    proximity_result_id text UNIQUE,
                    proximity_request_id text,
                    origin_feature jsonb DEFAULT '{{}}'::jsonb,
                    target_feature jsonb DEFAULT '{{}}'::jsonb,
                    distance_value numeric,
                    distance_unit text,
                    line_geojson_path text,
                    result_json jsonb DEFAULT '{{}}'::jsonb,
                    warnings jsonb DEFAULT '[]'::jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _text_blob(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, dict):
            parts.extend(str(item) for item in value.values())
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def _record_request(request: ProximityRequest, schema_name: str = "automap") -> dict[str, Any]:
    init_proximity_tables(schema_name)
    table = _requests_table(schema_name)
    data = request.to_dict()
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    proximity_request_id, raw_prompt, origin_input, origin_type,
                    target_type, target_layer_key, destination_input, request_json, status
                )
                VALUES (
                    :proximity_request_id, :raw_prompt, :origin_input, :origin_type,
                    :target_type, :target_layer_key, :destination_input,
                    CAST(:request_json AS jsonb), :status
                )
                ON CONFLICT (proximity_request_id) DO UPDATE SET
                    request_json = EXCLUDED.request_json,
                    status = EXCLUDED.status;
                """
            ),
            {
                **data,
                "request_json": _json_dumps(data.get("request_json") or {}),
            },
        )
    return data


def _record_result(result: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    init_proximity_tables(schema_name)
    table = _results_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    proximity_result_id, proximity_request_id, origin_feature,
                    target_feature, distance_value, distance_unit, line_geojson_path,
                    result_json, warnings
                )
                VALUES (
                    :proximity_result_id, :proximity_request_id,
                    CAST(:origin_feature AS jsonb), CAST(:target_feature AS jsonb),
                    :distance_value, :distance_unit, :line_geojson_path,
                    CAST(:result_json AS jsonb), CAST(:warnings AS jsonb)
                )
                ON CONFLICT (proximity_result_id) DO UPDATE SET
                    result_json = EXCLUDED.result_json,
                    warnings = EXCLUDED.warnings;
                """
            ),
            {
                "proximity_result_id": result["proximity_result_id"],
                "proximity_request_id": result["proximity_request_id"],
                "origin_feature": _json_dumps(result.get("origin_feature") or {}),
                "target_feature": _json_dumps(result.get("target_feature") or {}),
                "distance_value": result.get("distance_value"),
                "distance_unit": result.get("distance_unit"),
                "line_geojson_path": result.get("line_geojson_path"),
                "result_json": _json_dumps(result),
                "warnings": _json_dumps(result.get("warnings") or []),
            },
        )
    return result


def _row_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    for field in ["origin_feature", "target_feature", "result_json", "warnings", "request_json"]:
        if isinstance(data.get(field), str):
            try:
                data[field] = json.loads(data[field])
            except json.JSONDecodeError:
                pass
    return data


def list_proximity_results(schema_name: str = "automap", limit: int = 50) -> list[dict[str, Any]]:
    """List recent proximity result rows."""
    init_proximity_tables(schema_name)
    table = _results_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT :limit;"),
            {"limit": limit},
        ).mappings()
    return [_row_dict(row) for row in rows]


def get_proximity_result(proximity_result_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one proximity result."""
    init_proximity_tables(schema_name)
    table = _results_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(f"SELECT * FROM {table} WHERE proximity_result_id = :result_id;"),
            {"result_id": proximity_result_id},
        ).mappings().first()
    if row is None:
        raise ValueError(f"Proximity result not found: {proximity_result_id}")
    return _row_dict(row)


def validate_proximity_result(proximity_result_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Validate a proximity result record and local output metadata."""
    result = get_proximity_result(proximity_result_id, schema_name)
    result_json = result.get("result_json") or {}
    warnings: list[str] = []
    line_path = result.get("line_geojson_path") or result_json.get("line_geojson_path")
    if line_path:
        full_path = repo_root() / line_path
        if not full_path.exists():
            warnings.append(f"Line GeoJSON does not exist: {line_path}")
        else:
            text_value = full_path.read_text(encoding="utf-8").lower()
            for marker in ["database_url", "arcgis_password", "secret", "cfs_dev"]:
                if marker in text_value:
                    warnings.append(f"Protected marker found in line output: {marker}")
    if "cfs_dev" in json.dumps(result_json, default=str).lower():
        warnings.append("Protected CFS database marker found in proximity result.")
    return {"proximity_result_id": proximity_result_id, "is_valid": not warnings, "warnings": warnings}


def classify_proximity_request(prompt: str, target: str | None = None) -> dict[str, Any]:
    """Classify a prompt into a deterministic proximity request type."""
    lowered = prompt.lower()
    target_text = (target or "").lower()
    combined = f"{lowered} {target_text}"
    route_mode = any(phrase in combined for phrase in ["route", "drive", "driving"])
    if route_mode and " to " in lowered:
        request_type = "route_to_address"
    elif "fire district" in combined:
        request_type = "containing_fire_district" if "station" not in combined else "nearest_fire_station"
    elif "school district" in combined:
        request_type = "containing_school_district"
    elif "elementary" in combined:
        request_type = "nearest_elementary_school"
    elif "middle" in combined and "school" in combined:
        request_type = "nearest_middle_school"
    elif "high school" in combined:
        request_type = "nearest_high_school"
    elif "school" in combined:
        request_type = "nearest_school"
    elif "ems" in combined:
        request_type = "nearest_ems_station"
    elif "fire" in combined:
        request_type = "nearest_fire_station"
    elif "library" in combined:
        request_type = "nearest_library"
    elif "polling" in combined or "poll" in combined:
        request_type = "nearest_polling_place"
    elif "facility" in combined or "facilities" in combined:
        request_type = "nearest_county_facility"
    elif route_mode:
        request_type = "route_to_address"
    else:
        request_type = "unsupported_proximity_request"

    return {
        "target_type": request_type,
        "route_mode": "road_route_draft" if route_mode else "straight_line_nearest",
        "straight_line_supported": True,
        "road_route_supported": False,
    }


def normalize_target_type(target_type: str | None) -> str:
    """Normalize CLI/UI target aliases to proximity target types."""
    value = (target_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "schools": "nearest_school",
        "school": "nearest_school",
        "nearest_schools": "nearest_school",
        "elementary": "nearest_elementary_school",
        "elementary_school": "nearest_elementary_school",
        "middle": "nearest_middle_school",
        "middle_school": "nearest_middle_school",
        "high": "nearest_high_school",
        "high_school": "nearest_high_school",
        "fire": "nearest_fire_station",
        "fire_station": "nearest_fire_station",
        "fire_stations": "nearest_fire_station",
        "ems": "nearest_ems_station",
        "ems_station": "nearest_ems_station",
        "library": "nearest_library",
        "libraries": "nearest_library",
        "county_facility": "nearest_county_facility",
        "facilities": "nearest_county_facility",
        "polling": "nearest_polling_place",
        "polling_place": "nearest_polling_place",
        "fire_district": "containing_fire_district",
        "school_district": "containing_school_district",
    }
    return aliases.get(value, value or "unsupported_proximity_request")


def extract_origin_and_destination(prompt: str, *, origin_input: str | None = None, destination_input: str | None = None) -> dict[str, str | None]:
    """Extract origin/destination text with conservative route parsing."""
    if origin_input or destination_input:
        return {"origin_input": origin_input or prompt, "destination_input": destination_input}
    match = re.search(r"\bfrom\s+(.+?)\s+\bto\s+(.+)$", prompt, flags=re.IGNORECASE)
    if match:
        return {"origin_input": match.group(1).strip(" ."), "destination_input": match.group(2).strip(" .")}
    parcel_match = re.search(r"\bparcel\s+([0-9A-Za-z]+(?:[-\s][0-9A-Za-z]+){1,4})", prompt, flags=re.IGNORECASE)
    if parcel_match:
        origin = re.split(r"\b(?:from|to|and|with|near|nearest|closest)\b", parcel_match.group(1), flags=re.IGNORECASE)[0]
        return {"origin_input": origin.strip(" ."), "destination_input": None}
    parsed = parse_parcel_input(prompt)
    if parsed.get("address_candidates"):
        return {"origin_input": parsed["address_candidates"][0]["value"], "destination_input": None}
    address_match = re.search(r"\bfrom\s+(.+)$", prompt, flags=re.IGNORECASE)
    if address_match:
        return {"origin_input": address_match.group(1).strip(" ."), "destination_input": None}
    return {"origin_input": prompt, "destination_input": None}


def _feature_from_properties(properties: dict[str, Any], geometry: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def _load_first_geojson_feature(path: str) -> dict[str, Any] | None:
    try:
        features = load_geojson_features(repo_root() / path)
    except Exception:
        return None
    return features[0] if features else None


def resolve_origin(
    origin_input: str,
    *,
    schema_name: str = "automap",
    client: SpatialQueryClient | None = None,
    max_origins: int = DEFAULT_MAX_ORIGIN_FEATURES,
) -> dict[str, Any]:
    """Resolve an origin parcel/address with returnGeometry=false before geometry fetch."""
    warnings: list[str] = []
    parsed_origin = parse_parcel_input(origin_input)
    address_candidates = parsed_origin.get("address_candidates") or []
    identifiers = parsed_origin.get("parsed_identifiers") or []
    prefer_address = bool(address_candidates) and (
        not identifiers
        or looks_like_address(origin_input)
        or re.search(r"\b(my\s+address|my\s+home|address|home)\b", origin_input, re.IGNORECASE)
    )

    if prefer_address:
        address_value = address_candidates[0]["value"]
        address_result = resolve_address_point(address_value, client=client, schema_name=schema_name)
        if address_result.get("status") == "matched":
            return address_result

        parcel_set = create_parcel_set(address_value, schema_name=schema_name)
        matched_count = int(parcel_set.get("matched_count") or len(parcel_set.get("matched_parcels") or []))
        if matched_count == 1:
            geometry_result = fetch_selected_parcels(parcel_set["parcel_set_id"], schema_name=schema_name)
            if geometry_result.get("status") == "ok" and geometry_result.get("geometry_output_path"):
                feature = _load_first_geojson_feature(geometry_result["geometry_output_path"])
                if feature:
                    return {
                        "status": "matched",
                        "origin_type": "address",
                        "origin_feature": feature,
                        "parcel_set": get_parcel_set(parcel_set["parcel_set_id"], schema_name),
                        "warnings": [
                            "Address matched through verified parcel/address fields; selected parcel geometry was fetched only after a safe match count.",
                            *(geometry_result.get("warnings") or []),
                        ],
                    }
        if matched_count > max_origins:
            return {
                "status": "blocked",
                "origin_type": "address",
                "origin_feature": None,
                "parcel_set": parcel_set,
                "candidate_matches": parcel_set.get("candidate_matches") or [],
                "warnings": [
                    *warnings,
                    *(address_result.get("warnings") or []),
                    f"Address matched {matched_count} parcel candidates, above max {max_origins}. Choose a single candidate.",
                ],
            }
        return {
            "status": "needs_review",
            "origin_type": "address",
            "origin_feature": None,
            "parcel_set": parcel_set,
            "candidate_matches": [
                *(parcel_set.get("candidate_matches") or []),
                *(address_result.get("candidate_matches") or []),
            ],
            "warnings": [
                *(address_result.get("warnings") or []),
                *(parcel_set.get("warnings") or []),
                ADDRESS_NOT_MATCHED_WARNING,
            ],
        }

    parcel_set = create_parcel_set(origin_input, schema_name=schema_name)
    matched_count = int(parcel_set.get("matched_count") or len(parcel_set.get("matched_parcels") or []))
    if matched_count == 1:
        geometry_result = fetch_selected_parcels(parcel_set["parcel_set_id"], schema_name=schema_name)
        if geometry_result.get("status") == "ok" and geometry_result.get("geometry_output_path"):
            feature = _load_first_geojson_feature(geometry_result["geometry_output_path"])
            if feature:
                return {
                    "status": "matched",
                    "origin_type": "parcel",
                    "origin_feature": feature,
                    "parcel_set": get_parcel_set(parcel_set["parcel_set_id"], schema_name),
                    "warnings": warnings,
                }
        warnings.extend(geometry_result.get("warnings") or [])
    if matched_count > max_origins:
        return {
            "status": "blocked",
            "origin_type": "parcel_set",
            "origin_feature": None,
            "parcel_set": parcel_set,
            "warnings": [f"Origin matched {matched_count} parcels, above max {max_origins}. Split the parcel set."],
        }

    address_result = resolve_address_point(origin_input, client=client, schema_name=schema_name)
    if address_result.get("status") == "matched":
        return address_result
    return {
        "status": "needs_review",
        "origin_type": parcel_set.get("input_type") or "unknown",
        "origin_feature": None,
        "parcel_set": parcel_set,
        "candidate_matches": [
            *(parcel_set.get("candidate_matches") or []),
            *(address_result.get("candidate_matches") or []),
        ],
        "warnings": [
            *(parcel_set.get("warnings") or []),
            *(address_result.get("warnings") or []),
            "Origin could not be resolved to exactly one safe parcel or address point.",
        ],
    }


def _address_where(address: str, field_map: dict[str, Any]) -> tuple[str | None, list[str]]:
    fields = field_map.get("fields_by_role", {}).get("full_address") or []
    if not fields:
        return None, ["No verified full-address field is available."]
    clean = address.upper().replace("'", "''")
    return " OR ".join(f"UPPER({field}) LIKE '%{clean}%'" for field in fields), []


def resolve_address_point(
    address: str,
    *,
    client: SpatialQueryClient | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Resolve a supplied address against the verified Addresses layer."""
    parsed = parse_parcel_input(address)
    address_value = (
        (parsed.get("address_candidates") or [{}])[0].get("value")
        if parsed.get("address_candidates")
        else address
    )
    field_map = build_verified_address_field_map(schema_name=schema_name)
    layer_url = field_map.get("layer_url")
    where_clause, warnings = _address_where(str(address_value or address), field_map)
    if not layer_url or not where_clause:
        return {"status": "needs_review", "origin_type": "address", "origin_feature": None, "warnings": warnings}
    query_client = client or SpatialQueryClient(max_features=MAX_TARGET_CANDIDATES)
    try:
        count_result = query_client.query_count(layer_url, where=where_clause)
    except Exception as exc:
        return {"status": "needs_review", "origin_type": "address", "origin_feature": None, "warnings": [str(exc)]}
    count = int(count_result.get("count") or 0)
    if count == 0:
        return {"status": "unmatched", "origin_type": "address", "origin_feature": None, "warnings": [ADDRESS_NOT_MATCHED_WARNING]}
    if count > 1:
        candidates = query_client.query_features(
            layer_url,
            where=where_clause,
            out_fields="*",
            return_geometry=False,
            result_record_count=min(count, MAX_TARGET_CANDIDATES),
        )
        return {
            "status": "needs_review",
            "origin_type": "address",
            "origin_feature": None,
            "candidate_matches": candidates.get("features") or [],
            "warnings": [f"Address matched {count} candidates; choose one before proximity analysis."],
        }
    features = query_client.query_features(layer_url, where=where_clause, out_fields="*", return_geometry=True, result_record_count=1)
    rows = features.get("features") or []
    return {
        "status": "matched" if rows else "needs_review",
        "origin_type": "address",
        "origin_feature": rows[0] if rows else None,
        "warnings": warnings,
    }


def _layer_score(record: dict[str, Any], terms: list[str], *, prefer_points: bool = False, prefer_polygons: bool = False) -> int:
    blob = _text_blob(
        record.get("layer_key"),
        record.get("layer_name"),
        record.get("service_name"),
        record.get("category"),
        record.get("aliases"),
        record.get("canonical_topic"),
    )
    score = 0
    for term in terms:
        if term in blob:
            score += 10
    if record.get("is_verified"):
        score += 5
    if str(record.get("source_status") or "") == "active":
        score += 3
    if int(record.get("source_priority") or 99) == 1:
        score += 2
    geometry_type = str(record.get("geometry_type") or "").lower()
    if prefer_points and "point" in geometry_type:
        score += 8
    if prefer_polygons and "polygon" in geometry_type:
        score += 8
    if record.get("is_group_layer") or record.get("is_historical"):
        score -= 30
    return score


def find_target_layer(
    target_type: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    schema_name: str = "automap",
) -> dict[str, Any] | None:
    """Return the best verified catalog layer for a proximity target."""
    records = layer_catalog if layer_catalog is not None else load_catalog_records(schema_name)
    records = [
        record
        for record in records
        if record.get("is_verified") and record.get("is_active", True) and not record.get("is_group_layer")
    ]
    mapping: dict[str, tuple[list[str], bool, bool]] = {
        "nearest_school": (["schools", "school"], True, False),
        "nearest_elementary_school": (["schools", "school"], True, False),
        "nearest_middle_school": (["schools", "school"], True, False),
        "nearest_high_school": (["schools", "school"], True, False),
        "containing_school_district": (["school district", "school_districts", "schools"], False, True),
        "nearest_fire_station": (["fire and ems stations", "fire station", "ems station"], True, False),
        "nearest_ems_station": (["fire and ems stations", "ems station", "fire station"], True, False),
        "containing_fire_district": (["fire districts", "fire district"], False, True),
        "nearest_library": (["library", "libraries", "county facilities", "countyfacilities"], True, False),
        "nearest_county_facility": (["county facilities", "countyfacilities", "facilities"], True, False),
        "nearest_polling_place": (["polling place", "pollingplace"], True, False),
    }
    terms, prefer_points, prefer_polygons = mapping.get(target_type, ([], False, False))
    candidates = [(record, _layer_score(record, terms, prefer_points=prefer_points, prefer_polygons=prefer_polygons)) for record in records]
    candidates = [(record, score) for record, score in candidates if score > 0]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item[1], int(item[0].get("source_priority") or 99), str(item[0].get("layer_name") or "")))[0][0]


def _extent_around_point(point: dict[str, Any], miles: float) -> dict[str, Any]:
    lon, lat = point["coordinates"]
    lat_delta = miles / 69.0
    lon_delta = miles / max(1.0, 69.0 * 0.82)
    return {
        "xmin": lon - lon_delta,
        "ymin": lat - lat_delta,
        "xmax": lon + lon_delta,
        "ymax": lat + lat_delta,
        "spatialReference": {"wkid": 4326},
    }


def _target_name(feature: dict[str, Any] | None) -> str | None:
    if not feature:
        return None
    properties = feature.get("properties") or {}
    for key in ["NAME", "Name", "name", "FacilityName", "FACILITY", "SCHOOL", "DISTRICT", "DISTRICT_"]:
        value = properties.get(key)
        if value not in {None, ""}:
            return str(value)
    return None


def _query_target_candidates(
    origin_feature: dict[str, Any],
    target_layer: dict[str, Any],
    target_type: str,
    *,
    client: SpatialQueryClient,
) -> dict[str, Any]:
    layer_url = target_layer.get("layer_url") or target_layer.get("rest_url")
    if not layer_url:
        return {"status": "needs_review", "features": [], "warnings": ["Target layer has no layer URL."]}
    origin_point = compute_origin_point(origin_feature)
    geometry_type = str(target_layer.get("geometry_type") or "").lower()
    if target_type.startswith("containing_") or "polygon" in geometry_type and "district" in target_type:
        try:
            features = client.query_features(
                layer_url,
                geometry=origin_point,
                geometry_type="esriGeometryPoint",
                spatial_rel="esriSpatialRelIntersects",
                out_fields="*",
                return_geometry=True,
                result_record_count=MAX_TARGET_CANDIDATES,
            )
        except SpatialQueryError as exc:
            return {"status": "needs_review", "features": [], "warnings": [str(exc)]}
        return {"status": features.get("status"), "features": features.get("features") or [], "ring_miles": 0, "warnings": []}

    warnings: list[str] = []
    for ring in DISTANCE_RINGS_MILES:
        envelope = _extent_around_point(origin_point, ring)
        try:
            count_result = client.query_count(
                layer_url,
                geometry=envelope,
                geometry_type="esriGeometryEnvelope",
                spatial_rel="esriSpatialRelIntersects",
            )
        except SpatialQueryError as exc:
            warnings.append(str(exc))
            continue
        count = int(count_result.get("count") or 0)
        if count == 0:
            continue
        if count > HARD_MAX_TARGET_CANDIDATES:
            warnings.append(f"{count} candidate targets found within {ring} miles, above hard max {HARD_MAX_TARGET_CANDIDATES}.")
            continue
        if count > MAX_TARGET_CANDIDATES:
            warnings.append(f"{count} candidate targets found within {ring} miles, above review cap {MAX_TARGET_CANDIDATES}.")
            continue
        features = client.query_features(
            layer_url,
            geometry=envelope,
            geometry_type="esriGeometryEnvelope",
            spatial_rel="esriSpatialRelIntersects",
            out_fields="*",
            return_geometry=True,
            result_record_count=count,
        )
        return {
            "status": features.get("status"),
            "features": features.get("features") or [],
            "ring_miles": ring,
            "candidate_count": count,
            "warnings": warnings,
            "count_query": count_result,
        }
    return {"status": "needs_review", "features": [], "warnings": warnings or ["No target candidates found in bounded search rings."]}


def _safe_output_folder(prompt: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    return Path(PROXIMITY_OUTPUT_ROOT) / f"{timestamp}_{slugify(prompt)[:72]}"


def _write_line_output(result: dict[str, Any], output_folder: Path, line_geojson: dict[str, Any]) -> dict[str, Any]:
    output_path = repo_root() / output_folder
    output_path.mkdir(parents=True, exist_ok=True)
    line_path = output_path / "proximity_line.geojson"
    line_path.write_text(json.dumps(line_geojson, indent=2, default=str), encoding="utf-8")
    result["line_geojson_path"] = (output_folder / "proximity_line.geojson").as_posix()
    result["line_geojson_url"] = output_file_url(result["line_geojson_path"])
    result["output_folder"] = output_folder.as_posix()
    result["report_files"] = write_proximity_report(output_path, result)
    return result


def build_proximity_context(prompt: str, *, target: str | None = None) -> dict[str, Any]:
    """Return request-intelligence proximity metadata without executing queries."""
    classification = classify_proximity_request(prompt, target)
    questions: list[dict[str, Any]] = []
    lowered = f"{prompt} {target or ''}".lower()
    if "school" in lowered and not any(level in lowered for level in ["elementary", "middle", "high", "district"]):
        questions.append({"question": "Do you want nearest school point or school district?", "reason": "School point and district layers answer different questions."})
        questions.append({"question": "Which school level: elementary, middle, high, or any school?", "reason": "School level changes the target layer/context."})
    if "fire" in lowered and "station" not in lowered and "district" not in lowered:
        questions.append({"question": "Do you mean nearest fire station or fire district?", "reason": "Station proximity and district containment are different GIS operations."})
    if classification["route_mode"] == "road_route_draft":
        questions.append({"question": "For route, do you need a road-network driving route or is a straight-line reference acceptable?", "reason": ROUTE_WARNING})
    return {
        "proximity_detected": classification["target_type"] != "unsupported_proximity_request",
        "target_type": classification["target_type"],
        "distance_mode": "straight_line",
        "route_mode": classification["route_mode"],
        "straight_line_supported": True,
        "road_route_supported": False,
        "clarifying_questions": questions,
        "warnings": [] if classification["route_mode"] != "road_route_draft" else [ROUTE_WARNING],
    }


def run_nearest_facility(
    origin_input: str,
    *,
    target_type: str,
    raw_prompt: str | None = None,
    schema_name: str = "automap",
    client: SpatialQueryClient | None = None,
    layer_catalog: list[dict[str, Any]] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Execute a bounded nearest-facility or containment request."""
    target_type = normalize_target_type(target_type)
    prompt = raw_prompt or f"Nearest {target_type} from {origin_input}"
    query_client = client or SpatialQueryClient(max_features=MAX_TARGET_CANDIDATES)
    origin = resolve_origin(origin_input, schema_name=schema_name, client=query_client)
    request = ProximityRequest(
        proximity_request_id=f"prox_req_{uuid4().hex[:12]}",
        raw_prompt=prompt,
        origin_input=origin_input,
        origin_type=origin.get("origin_type") or "unknown",
        target_type=target_type,
        status="needs_review",
    )
    if persist:
        _record_request(request, schema_name)

    warnings = list(origin.get("warnings") or [])
    if origin.get("status") != "matched" or not origin.get("origin_feature"):
        result = {
            "proximity_result_id": f"prox_result_{uuid4().hex[:12]}",
            "proximity_request_id": request.proximity_request_id,
            "raw_prompt": prompt,
            "origin_input": origin_input,
            "target_type": target_type,
            "status": "needs_review",
            "origin_feature": None,
            "target_feature": None,
            "distance_value": None,
            "distance_unit": "miles",
            "candidate_matches": origin.get("candidate_matches") or [],
            "warnings": warnings,
            "downloaded_countywide": False,
            "published": False,
        }
        return _record_result(result, schema_name) if persist else result

    target_layer = find_target_layer(target_type, layer_catalog=layer_catalog, schema_name=schema_name)
    if not target_layer:
        result = {
            "proximity_result_id": f"prox_result_{uuid4().hex[:12]}",
            "proximity_request_id": request.proximity_request_id,
            "raw_prompt": prompt,
            "origin_input": origin_input,
            "target_type": target_type,
            "status": "needs_review",
            "origin_feature": origin["origin_feature"],
            "target_feature": None,
            "distance_value": None,
            "distance_unit": "miles",
            "warnings": [*warnings, f"No verified catalog layer is available for {target_type}."],
            "downloaded_countywide": False,
            "published": False,
        }
        return _record_result(result, schema_name) if persist else result

    candidates = _query_target_candidates(origin["origin_feature"], target_layer, target_type, client=query_client)
    features = candidates.get("features") or []
    warnings.extend(candidates.get("warnings") or [])
    if not features:
        result = {
            "proximity_result_id": f"prox_result_{uuid4().hex[:12]}",
            "proximity_request_id": request.proximity_request_id,
            "raw_prompt": prompt,
            "origin_input": origin_input,
            "target_type": target_type,
            "target_layer": target_layer,
            "target_layer_key": target_layer.get("layer_key"),
            "status": "needs_review",
            "origin_feature": origin["origin_feature"],
            "target_feature": None,
            "distance_value": None,
            "distance_unit": "miles",
            "bounded_rings_used": DISTANCE_RINGS_MILES,
            "warnings": warnings,
            "downloaded_countywide": False,
            "published": False,
        }
        return _record_result(result, schema_name) if persist else result

    if target_type.startswith("containing_"):
        nearest = {"feature": features[0], "distance": 0.0, "distance_unit": "miles"}
        line_type = "containment"
    else:
        nearest = compute_nearest_feature(origin["origin_feature"], features, unit="miles")
        line_type = "straight-line"
    if nearest is None:
        raise GeometrySafetyError("Unable to compute nearest feature from bounded candidates.")
    line_feature = build_straight_line_geojson(
        origin["origin_feature"],
        nearest["feature"],
        properties={
            "target_type": target_type,
            "target_layer_key": target_layer.get("layer_key"),
            "distance_miles": nearest["distance"],
            "label": "Straight-line distance",
        },
    )
    result_geojson = build_proximity_result_geojson(origin["origin_feature"], nearest["feature"], line_feature)
    output_folder = _safe_output_folder(prompt)
    output_path = repo_root() / output_folder
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "proximity_result.geojson").write_text(json.dumps(result_geojson, indent=2, default=str), encoding="utf-8")
    result = {
        "proximity_result_id": f"prox_result_{uuid4().hex[:12]}",
        "proximity_request_id": request.proximity_request_id,
        "raw_prompt": prompt,
        "origin_input": origin_input,
        "origin_type": origin.get("origin_type"),
        "target_type": target_type,
        "target_layer": target_layer,
        "target_layer_key": target_layer.get("layer_key"),
        "target_name": _target_name(nearest["feature"]),
        "target_feature": nearest["feature"],
        "origin_feature": origin["origin_feature"],
        "distance_value": nearest["distance"],
        "distance_unit": "miles",
        "line_type": line_type,
        "route_status": "straight_line_supported",
        "status": "ok",
        "bounded_search": {
            "rings_miles": DISTANCE_RINGS_MILES,
            "ring_used_miles": candidates.get("ring_miles"),
            "candidate_count": len(features),
            "target_candidate_cap": MAX_TARGET_CANDIDATES,
        },
        "derived_layer": {
            "layer_key": f"derived_proximity_line_{request.proximity_request_id}",
            "layer_name": "Straight-line distance",
            "layer_type": "GeoJSON",
            "derived_local_proximity_result": True,
            "not_published": True,
        },
        "warnings": warnings,
        "downloaded_countywide": False,
        "published": False,
        "cfs_untouched_statement": "CFS database cfs_dev was not touched.",
    }
    result = _write_line_output(result, output_folder, {"type": "FeatureCollection", "features": [line_feature]})
    return _record_result(result, schema_name) if persist else result


def run_proximity_request(
    prompt: str,
    *,
    schema_name: str = "automap",
    client: SpatialQueryClient | None = None,
    layer_catalog: list[dict[str, Any]] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Run a prompt-driven proximity request."""
    classification = classify_proximity_request(prompt)
    parts = extract_origin_and_destination(prompt)
    target_type = classification["target_type"]
    if target_type == "route_to_address":
        return run_route_draft(
            parts.get("origin_input") or prompt,
            parts.get("destination_input") or "",
            raw_prompt=prompt,
            schema_name=schema_name,
            client=client,
            persist=persist,
        )
    return run_nearest_facility(
        parts.get("origin_input") or prompt,
        target_type=target_type,
        raw_prompt=prompt,
        schema_name=schema_name,
        client=client,
        layer_catalog=layer_catalog,
        persist=persist,
    )


def run_route_draft(
    origin_input: str,
    destination_input: str,
    *,
    raw_prompt: str | None = None,
    schema_name: str = "automap",
    client: SpatialQueryClient | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Create a straight-line route draft when no network routing service exists."""
    prompt = raw_prompt or f"Route draft from {origin_input} to {destination_input}"
    query_client = client or SpatialQueryClient(max_features=MAX_TARGET_CANDIDATES)
    origin = resolve_origin(origin_input, schema_name=schema_name, client=query_client)
    destination = resolve_address_point(destination_input, schema_name=schema_name, client=query_client) if destination_input else {
        "status": "needs_review",
        "origin_type": "address",
        "origin_feature": None,
        "warnings": ["No destination address was parsed for route draft."],
    }
    request = ProximityRequest(
        proximity_request_id=f"prox_req_{uuid4().hex[:12]}",
        raw_prompt=prompt,
        origin_input=origin_input,
        origin_type=origin.get("origin_type") or "unknown",
        target_type="route_to_address",
        destination_input=destination_input,
        status="needs_review",
    )
    if persist:
        _record_request(request, schema_name)

    warnings = [ROUTE_WARNING, "Straight-line reference is not a driving route."]
    warnings.extend(origin.get("warnings") or [])
    warnings.extend(destination.get("warnings") or [])
    if origin.get("status") != "matched" or destination.get("status") != "matched":
        result = {
            "proximity_result_id": f"prox_result_{uuid4().hex[:12]}",
            "proximity_request_id": request.proximity_request_id,
            "raw_prompt": prompt,
            "origin_input": origin_input,
            "destination_input": destination_input,
            "target_type": "route_to_address",
            "status": "needs_review",
            "route_status": "network_route_not_available",
            "origin_feature": origin.get("origin_feature"),
            "target_feature": destination.get("origin_feature"),
            "candidate_matches": [
                *(origin.get("candidate_matches") or []),
                *(destination.get("candidate_matches") or []),
            ],
            "distance_value": None,
            "distance_unit": "miles",
            "warnings": warnings,
            "published": False,
        }
        return _record_result(result, schema_name) if persist else result

    distance = compute_nearest_feature(origin["origin_feature"], [destination["origin_feature"]], unit="miles")
    line_feature = build_straight_line_geojson(
        origin["origin_feature"],
        destination["origin_feature"],
        properties={
            "target_type": "route_to_address",
            "distance_miles": distance["distance"] if distance else None,
            "label": "Straight-line reference, not driving route",
        },
    )
    output_folder = _safe_output_folder(prompt)
    result = {
        "proximity_result_id": f"prox_result_{uuid4().hex[:12]}",
        "proximity_request_id": request.proximity_request_id,
        "raw_prompt": prompt,
        "origin_input": origin_input,
        "destination_input": destination_input,
        "target_type": "route_to_address",
        "status": "ok",
        "route_status": "network_route_not_available",
        "origin_feature": origin["origin_feature"],
        "target_feature": destination["origin_feature"],
        "distance_value": distance["distance"] if distance else None,
        "distance_unit": "miles",
        "line_type": "straight-line reference",
        "warnings": warnings,
        "published": False,
        "downloaded_countywide": False,
        "cfs_untouched_statement": "CFS database cfs_dev was not touched.",
    }
    result = _write_line_output(result, output_folder, {"type": "FeatureCollection", "features": [line_feature]})
    return _record_result(result, schema_name) if persist else result
