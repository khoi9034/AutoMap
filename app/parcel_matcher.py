"""Safe parcel matching against the verified AutoMap Tax Parcels catalog layer."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import re
from typing import Any

from app.address_field_mapper import build_verified_address_field_map
from app.field_profiler import infer_field_roles, load_field_profiles
from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import slugify
from app.ui_models import repo_root
from app.spatial_query_client import SpatialQueryClient, SpatialQueryError


PARCEL_MATCH_LIMIT = 100
MAX_PARCEL_MATCHES_FOR_GEOMETRY = 100
HARD_MAX_PARCEL_MATCHES_FOR_GEOMETRY = 250
PARCEL_CONTEXT_OUTPUT_ROOT = Path("outputs/parcel_context")
FIELD_ROLE_KEYS = ("pin14", "pin", "parcel_id", "address")


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _text_blob(*values: Any) -> str:
    parts: list[str] = []
    for value in values:
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts).lower()


def _field_name(profile: dict[str, Any]) -> str:
    return str(profile.get("field_name") or profile.get("name") or "")


def _field_alias(profile: dict[str, Any]) -> str:
    return str(profile.get("field_alias") or profile.get("alias") or "")


def _dedupe_fields(fields: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for field in fields:
        clean = str(field or "").strip()
        if clean and clean.lower() not in seen:
            rows.append(clean)
            seen.add(clean.lower())
    return rows


def _sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _normalized_identifier_value(value: str) -> str:
    return re.sub(r"[\s\-]", "", str(value or "").upper())


def _normalized_field_expression(field: str) -> str:
    return f"REPLACE(REPLACE(UPPER({field}), '-', ''), ' ', '')"


def find_tax_parcel_layer(
    layer_catalog: list[dict[str, Any]] | None = None,
    *,
    schema_name: str = "automap",
) -> dict[str, Any] | None:
    """Return the best active verified Tax Parcels layer from the trusted catalog."""
    records = layer_catalog if layer_catalog is not None else load_catalog_records(schema_name)
    candidates = [
        record
        for record in records
        if record.get("is_active", True)
        and record.get("is_verified", False)
        and not record.get("is_historical")
        and not record.get("is_group_layer")
        and (
            record.get("category") == "parcel"
            or "tax parcel" in _text_blob(record.get("layer_name"), record.get("aliases"), record.get("service_name"))
            or "parcel" in _text_blob(record.get("layer_name"), record.get("canonical_topic"))
        )
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            int(item.get("source_priority") or 999),
            0 if str(item.get("source_status") or "") == "active" else 1,
            str(item.get("layer_name") or ""),
        ),
    )[0]


def _raw_field_profiles(layer_record: dict[str, Any]) -> list[dict[str, Any]]:
    fields = layer_record.get("fields") or []
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except json.JSONDecodeError:
            fields = []
    if not isinstance(fields, list):
        return []
    return infer_field_roles([field for field in fields if isinstance(field, dict)])


def infer_parcel_id_fields(
    layer_record: dict[str, Any],
    *,
    schema_name: str = "automap",
) -> dict[str, list[str]]:
    """Infer usable public parcel identifier fields from catalog metadata and profiles."""
    field_map: dict[str, list[str]] = {key: [] for key in FIELD_ROLE_KEYS}
    profiles: list[dict[str, Any]] = []
    try:
        profiles.extend(load_field_profiles([layer_record["layer_key"]], schema_name).get(layer_record["layer_key"], []))
    except Exception:
        profiles = []
    profiles.extend(_raw_field_profiles(layer_record))

    for profile in profiles:
        name = _field_name(profile)
        if not name:
            continue
        blob = _text_blob(name, _field_alias(profile))
        compact = re.sub(r"[^a-z0-9]", "", blob)
        if "pin14" in compact or "parcelidentificationnumber14" in compact:
            field_map["pin14"].append(name)
        if re.search(r"\bpin\b", blob) or "parcelidentificationnumber" in compact:
            field_map["pin"].append(name)
        if profile.get("is_parcel_candidate") or any(term in compact for term in ["parcelid", "parcelnumber", "parcelnum", "account"]):
            field_map["parcel_id"].append(name)
        if profile.get("is_address_candidate") or any(term in compact for term in ["address", "siteaddress", "situs", "street"]):
            field_map["address"].append(name)
        # Owner fields are intentionally not mapped for default parcel lookup.

    object_id = layer_record.get("object_id_field")
    if object_id:
        field_map.setdefault("object_id", []).append(str(object_id))
    for profile in profiles:
        name = _field_name(profile)
        if profile.get("is_object_id") and name:
            field_map.setdefault("object_id", []).append(name)
        if profile.get("is_geometry_field") and name:
            field_map.setdefault("geometry", []).append(name)
    return {key: _dedupe_fields(value) for key, value in field_map.items()}


def build_parcel_where_clause(
    identifiers: list[dict[str, Any]],
    field_map: dict[str, list[str]],
) -> tuple[str | None, list[str]]:
    """Build a conservative ArcGIS where clause using only inferred real fields."""
    clauses: list[str] = []
    warnings: list[str] = []
    for identifier in identifiers:
        identifier_type = str(identifier.get("identifier_type") or "").lower()
        value = str(identifier.get("normalized_value") or identifier.get("value") or "").strip()
        raw_value = str(identifier.get("value") or value).strip()
        if not value:
            continue
        if identifier_type == "owner":
            warnings.append("Owner lookup was requested but is not queried by default; public owner-field review is required first.")
            continue
        candidate_fields = field_map.get(identifier_type) or []
        if identifier_type == "pin14" and not candidate_fields:
            candidate_fields = field_map.get("pin") or field_map.get("parcel_id") or []
        if identifier_type == "pin" and not candidate_fields:
            candidate_fields = field_map.get("pin14") or field_map.get("parcel_id") or []
        if identifier_type == "address":
            candidate_fields = field_map.get("address") or []
        if not candidate_fields:
            warnings.append(f"No verified field was inferred for {identifier_type}: {value}.")
            continue
        field_clauses: list[str] = []
        for field in candidate_fields:
            for candidate in _dedupe_fields([raw_value, value, value.upper()]):
                field_clauses.append(f"UPPER({field}) = {_sql_literal(candidate.upper())}")
            if identifier_type in {"pin", "pin14", "parcel_id"}:
                normalized = _normalized_identifier_value(value)
                if normalized:
                    field_clauses.append(f"{_normalized_field_expression(field)} = {_sql_literal(normalized)}")
        if identifier_type == "address":
            field_clauses.extend(f"UPPER({field}) LIKE {_sql_literal('%' + value.upper() + '%')}" for field in candidate_fields)
        clauses.append("(" + " OR ".join(field_clauses) + ")")
    if not clauses:
        return None, warnings
    return " OR ".join(clauses), warnings


def estimate_parcel_match_count(
    where_clause: str,
    layer_record: dict[str, Any],
    *,
    client: SpatialQueryClient | None = None,
) -> dict[str, Any]:
    """Run a count-only parcel match query."""
    layer_url = layer_record.get("layer_url") or layer_record.get("rest_url")
    if not layer_url:
        raise ValueError("Tax Parcels layer does not have a layer_url.")
    query_client = client or SpatialQueryClient(max_features=PARCEL_MATCH_LIMIT)
    return query_client.query_count(layer_url, where=where_clause)


def _features_from_query_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    features = result.get("features") or []
    rows: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties") or feature.get("attributes") or {}
        rows.append({"properties": properties, "geometry": feature.get("geometry")})
    return rows


def _out_fields(field_map: dict[str, list[str]], object_id_field: str | None) -> str:
    fields = _dedupe_fields([
        *(field_map.get("object_id") or []),
        *(_as_list(object_id_field)),
        *(field_map.get("pin14") or []),
        *(field_map.get("pin") or []),
        *(field_map.get("parcel_id") or []),
        *(field_map.get("address") or []),
    ])
    return ",".join(fields) if fields else "*"


def _summarize_feature(feature: dict[str, Any], field_map: dict[str, list[str]]) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    summary: dict[str, Any] = {"attributes": properties}
    for role in ["object_id", "pin14", "pin", "parcel_id", "address"]:
        for field in field_map.get(role) or []:
            if field in properties and properties.get(field) not in {None, ""}:
                summary[role] = properties.get(field)
                break
    return summary


def _candidate_match_rows(rows: list[dict[str, Any]], identifier: dict[str, Any], count: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for row in rows:
        candidates.append(
            {
                "identifier": identifier,
                "count": count,
                "pin14": row.get("pin14"),
                "pin": row.get("pin"),
                "parcel_id": row.get("parcel_id"),
                "address": row.get("address"),
                "object_id": row.get("object_id"),
                "source_layer_key": row.get("source_layer_key"),
                "needs_review": count > 1,
            }
        )
    return candidates


def validate_parcel_matches(match_result: dict[str, Any]) -> dict[str, Any]:
    """Assign a review status to parcel matching output."""
    matched_count = int(match_result.get("matched_count") or 0)
    unmatched = match_result.get("unmatched_identifiers") or []
    multiple = bool(match_result.get("multiple_match_identifiers"))
    if matched_count == 0:
        status = "unmatched"
    elif unmatched or multiple:
        status = "needs_review" if multiple else "partial"
    else:
        status = "matched"
    match_result["match_status"] = status
    if multiple:
        match_result.setdefault("warnings", []).append("One or more identifiers matched multiple parcel records and need review.")
    return match_result


def match_parcels_by_identifier(
    identifiers: list[dict[str, Any]],
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    client: SpatialQueryClient | None = None,
    max_matches: int = PARCEL_MATCH_LIMIT,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Match parsed parcel identifiers without downloading parcel geometry."""
    layer = find_tax_parcel_layer(layer_catalog, schema_name=schema_name)
    if not layer:
        return validate_parcel_matches(
            {
                "source_layer_key": None,
                "matched_count": 0,
                "matched_parcels": [],
                "unmatched_identifiers": identifiers,
                "multiple_match_identifiers": [],
                "warnings": ["No verified Tax Parcels layer is available in the AutoMap catalog."],
                "downloaded_geometry": False,
            }
        )
    field_map = infer_parcel_id_fields(layer, schema_name=schema_name)
    query_client = client or SpatialQueryClient(max_features=max_matches)
    matched: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []
    multiple: list[dict[str, Any]] = []
    candidate_matches: list[dict[str, Any]] = []
    warnings: list[str] = []
    layer_url = layer.get("layer_url") or layer.get("rest_url")

    for identifier in identifiers:
        where_clause, where_warnings = build_parcel_where_clause([identifier], field_map)
        warnings.extend(where_warnings)
        if not where_clause:
            unmatched.append(identifier)
            continue
        try:
            count_result = estimate_parcel_match_count(where_clause, layer, client=query_client)
            count = int(count_result.get("count") or 0)
        except (SpatialQueryError, ValueError) as exc:
            warnings.append(f"Parcel count query failed for {identifier.get('value')}: {exc}")
            unmatched.append(identifier)
            continue
        if count == 0:
            unmatched.append(identifier)
            continue
        if count > max_matches:
            warnings.append(
                f"Parcel match for {identifier.get('value')} returned {count} records; refine the identifier before geometry use."
            )
            multiple.append({"identifier": identifier, "count": count, "where": where_clause})
            continue
        try:
            query = query_client.query_features(
                layer_url,
                where=where_clause,
                out_fields=_out_fields(field_map, layer.get("object_id_field")),
                return_geometry=False,
                result_record_count=max_matches,
            )
        except SpatialQueryError as exc:
            warnings.append(f"Parcel attribute query failed for {identifier.get('value')}: {exc}")
            unmatched.append(identifier)
            continue
        rows = [_summarize_feature(feature, field_map) for feature in _features_from_query_result(query)]
        for row in rows:
            row["input_identifier"] = identifier
            row["source_layer_key"] = layer.get("layer_key")
        matched.extend(rows)
        if count > 1:
            multiple.append({"identifier": identifier, "count": count, "where": where_clause})
            candidate_matches.extend(_candidate_match_rows(rows, identifier, count))

    return validate_parcel_matches(
        {
            "source_layer_key": layer.get("layer_key"),
            "source_layer_name": layer.get("layer_name"),
            "field_map": field_map,
            "matched_count": len(matched),
            "matched_parcels": matched,
            "unmatched_identifiers": unmatched,
            "multiple_match_identifiers": multiple,
            "candidate_matches": candidate_matches,
            "warnings": warnings,
            "downloaded_geometry": False,
        }
    )


def match_parcels_by_address(
    addresses: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    """Match address candidates through verified address/parcel fields only."""
    normalized_addresses = [
        {
            **address,
            "identifier_type": "address",
            "normalized_value": str(address.get("normalized_value") or address.get("value") or "").upper(),
        }
        for address in addresses
    ]
    address_layer_result = _match_addresses_on_address_layer(normalized_addresses, **kwargs)
    parcel_result = match_parcels_by_identifier(normalized_addresses, **kwargs)
    parcel_result["address_candidates"] = address_layer_result.get("candidate_matches") or []
    parcel_result["warnings"] = [
        *(parcel_result.get("warnings") or []),
        *(address_layer_result.get("warnings") or []),
    ]
    if address_layer_result.get("matched_parcel_identifiers"):
        relation_result = match_parcels_by_identifier(address_layer_result["matched_parcel_identifiers"], **kwargs)
        parcel_result["matched_parcels"] = [
            *(parcel_result.get("matched_parcels") or []),
            *(relation_result.get("matched_parcels") or []),
        ]
        parcel_result["candidate_matches"] = [
            *(parcel_result.get("candidate_matches") or []),
            *(relation_result.get("candidate_matches") or []),
        ]
        parcel_result["unmatched_identifiers"] = relation_result.get("unmatched_identifiers") or parcel_result.get("unmatched_identifiers") or []
        parcel_result["matched_count"] = len(parcel_result.get("matched_parcels") or [])
        validate_parcel_matches(parcel_result)
    return parcel_result


def _match_addresses_on_address_layer(
    addresses: list[dict[str, Any]],
    *,
    client: SpatialQueryClient | None = None,
    max_matches: int = PARCEL_MATCH_LIMIT,
    schema_name: str = "automap",
    **_: Any,
) -> dict[str, Any]:
    """Return address-layer candidates and parcel relation identifiers when verified fields exist."""
    field_map = build_verified_address_field_map(schema_name)
    layer_url = field_map.get("layer_url")
    fields_by_role = field_map.get("fields_by_role") or {}
    address_fields = fields_by_role.get("full_address") or []
    warnings = list(field_map.get("warnings") or [])
    if not layer_url or not address_fields:
        return {"candidate_matches": [], "matched_parcel_identifiers": [], "warnings": warnings}
    query_client = client or SpatialQueryClient(max_features=max_matches)
    candidate_matches: list[dict[str, Any]] = []
    related_identifiers: list[dict[str, Any]] = []
    relation_fields = [
        *(fields_by_role.get("pin14") or []),
        *(fields_by_role.get("pin") or []),
        *(fields_by_role.get("parcel_id") or []),
    ]
    out_fields = _dedupe_fields([*(fields_by_role.get("object_id") or []), *address_fields, *relation_fields])
    for address in addresses:
        value = str(address.get("normalized_value") or address.get("value") or "").upper()
        where = " OR ".join(f"UPPER({field}) LIKE {_sql_literal('%' + value + '%')}" for field in address_fields)
        if not where:
            continue
        try:
            query = query_client.query_features(
                layer_url,
                where=where,
                out_fields=",".join(out_fields) if out_fields else "*",
                return_geometry=False,
                result_record_count=max_matches,
            )
        except SpatialQueryError as exc:
            warnings.append(f"Address candidate query failed for {address.get('value')}: {exc}")
            continue
        for feature in _features_from_query_result(query):
            properties = feature.get("properties") or {}
            candidate = {
                "identifier": address,
                "attributes": properties,
                "source_layer_key": field_map.get("layer_key"),
                "needs_review": True,
            }
            for role in ["pin14", "pin", "parcel_id", "full_address"]:
                for field in fields_by_role.get(role) or []:
                    if properties.get(field) not in {None, ""}:
                        candidate[role if role != "full_address" else "address"] = properties.get(field)
                        if role in {"pin14", "pin", "parcel_id"}:
                            related_identifiers.append(
                                {
                                    "identifier_type": role,
                                    "value": str(properties.get(field)),
                                    "normalized_value": str(properties.get(field)).upper(),
                                    "source_text": str(address.get("value") or ""),
                                    "confidence": 0.72,
                                    "needs_review": True,
                                    "notes": ["Matched through verified Addresses layer relation field."],
                                }
                            )
                        break
            candidate_matches.append(candidate)
    return {
        "candidate_matches": candidate_matches,
        "matched_parcel_identifiers": related_identifiers,
        "warnings": warnings,
    }


def _output_root() -> Path:
    root = PARCEL_CONTEXT_OUTPUT_ROOT
    return root if root.is_absolute() else repo_root() / root


def _repo_relative_or_absolute(path: Path) -> str:
    try:
        return path.relative_to(repo_root()).as_posix()
    except ValueError:
        return path.as_posix()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _layer_by_key(layer_key: str | None, layer_catalog: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    records = layer_catalog if layer_catalog is not None else load_catalog_records()
    for record in records:
        if record.get("layer_key") == layer_key:
            return record
    return None


def _matched_object_ids(parcel_set: dict[str, Any], object_id_fields: list[str]) -> list[Any]:
    ids: list[Any] = []
    for parcel in parcel_set.get("matched_parcels") or []:
        for key in ["object_id", *object_id_fields]:
            attributes = parcel.get("attributes") if isinstance(parcel.get("attributes"), dict) else {}
            value = parcel.get(key) or attributes.get(key)
            if value not in {None, ""}:
                ids.append(value)
                break
    seen: set[str] = set()
    deduped: list[Any] = []
    for value in ids:
        key = str(value)
        if key not in seen:
            seen.add(key)
            deduped.append(value)
    return deduped


def fetch_selected_parcel_geometry(
    parcel_set: dict[str, Any],
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    client: SpatialQueryClient | None = None,
    max_parcel_matches_for_geometry: int = MAX_PARCEL_MATCHES_FOR_GEOMETRY,
    hard_max: int = HARD_MAX_PARCEL_MATCHES_FOR_GEOMETRY,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Fetch only safely matched parcel geometries and write local GeoJSON output."""
    matched_count = int(parcel_set.get("matched_count") or len(parcel_set.get("matched_parcels") or []))
    warnings: list[str] = []
    if matched_count < 1:
        return {
            "status": "blocked",
            "geometry_output_path": None,
            "warnings": ["No matched parcels are available for selected-parcel geometry retrieval."],
            "downloaded_geometry": False,
        }
    if matched_count > hard_max:
        return {
            "status": "blocked",
            "geometry_output_path": None,
            "warnings": [f"Matched parcel count {matched_count} exceeds hard geometry limit {hard_max}; split the parcel set."],
            "downloaded_geometry": False,
        }
    if matched_count > max_parcel_matches_for_geometry:
        return {
            "status": "blocked",
            "geometry_output_path": None,
            "warnings": [
                f"Matched parcel count {matched_count} exceeds selected parcel geometry limit {max_parcel_matches_for_geometry}; split the parcel set."
            ],
            "downloaded_geometry": False,
        }

    layer = _layer_by_key(parcel_set.get("source_layer_key"), layer_catalog) or find_tax_parcel_layer(layer_catalog, schema_name=schema_name)
    if not layer:
        return {
            "status": "blocked",
            "geometry_output_path": None,
            "warnings": ["Verified Tax Parcels layer is unavailable."],
            "downloaded_geometry": False,
        }
    field_map = infer_parcel_id_fields(layer, schema_name=schema_name)
    object_id_fields = field_map.get("object_id") or []
    layer_url = layer.get("layer_url") or layer.get("rest_url")
    if not layer_url:
        return {
            "status": "blocked",
            "geometry_output_path": None,
            "warnings": ["Tax Parcels layer does not have a REST layer URL."],
            "downloaded_geometry": False,
        }
    object_ids = _matched_object_ids(parcel_set, object_id_fields)
    query_client = client or SpatialQueryClient(max_features=max_parcel_matches_for_geometry, hard_max_features=hard_max)
    out_fields = _out_fields(field_map, (object_id_fields or [layer.get("object_id_field")])[0])
    query_metadata: dict[str, Any]
    if object_ids and len(object_ids) == matched_count:
        query = query_client.query_features_by_object_ids(
            layer_url,
            object_ids=object_ids,
            out_fields=out_fields,
            return_geometry=True,
            result_record_count=max_parcel_matches_for_geometry,
        )
        query_metadata = query.get("query_metadata") or {}
    else:
        where_clause, where_warnings = build_parcel_where_clause(parcel_set.get("parsed_identifiers") or [], field_map)
        warnings.extend(where_warnings)
        if not where_clause:
            return {
                "status": "blocked",
                "geometry_output_path": None,
                "warnings": [*warnings, "No safe parcel where clause could be rebuilt for geometry retrieval."],
                "downloaded_geometry": False,
            }
        query = query_client.query_features(
            layer_url,
            where=where_clause,
            out_fields=out_fields,
            return_geometry=True,
            result_record_count=max_parcel_matches_for_geometry,
        )
        query_metadata = query.get("query_metadata") or {}
    if query.get("status") == "blocked":
        return {
            "status": "blocked",
            "geometry_output_path": None,
            "warnings": [*warnings, query.get("blocked_reason") or "Selected parcel geometry query was blocked by safety limits."],
            "downloaded_geometry": False,
            "receipt": {"query_metadata": query_metadata, "matched_count": matched_count},
        }
    feature_collection = query.get("feature_collection") or {"type": "FeatureCollection", "features": query.get("features") or []}
    folder = _output_root() / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{slugify(str(parcel_set.get('parcel_set_id') or 'selected_parcels'))}"
    folder.mkdir(parents=True, exist_ok=True)
    geojson_path = folder / "selected_parcels.geojson"
    receipt_path = folder / "parcel_match_receipt.json"
    summary_path = folder / "parcel_context_summary.md"
    _write_json(geojson_path, feature_collection)
    receipt = {
        "parcel_set_id": parcel_set.get("parcel_set_id"),
        "source_layer_key": layer.get("layer_key"),
        "source_layer_url": layer_url,
        "matched_count": matched_count,
        "object_id_count": len(object_ids),
        "features_downloaded": len(feature_collection.get("features") or []),
        "max_parcel_matches_for_geometry": max_parcel_matches_for_geometry,
        "hard_max": hard_max,
        "downloaded_geometry": True,
        "query_metadata": query_metadata,
        "warnings": warnings,
        "cfs_untouched_statement": "CFS repo and database were not accessed or modified by this AutoMap parcel workflow.",
        "no_publish_statement": "No ArcGIS item was created, uploaded, shared, overwritten, or deleted.",
    }
    _write_json(receipt_path, receipt)
    summary_path.write_text(
        "\n".join(
            [
                "# Selected Parcel Context Summary",
                "",
                f"- Parcel set: {parcel_set.get('parcel_set_id')}",
                f"- Matched parcels: {matched_count}",
                f"- Features downloaded: {receipt['features_downloaded']}",
                f"- GeoJSON: {_repo_relative_or_absolute(geojson_path)}",
                "- Draft-only: selected parcel output is local review data.",
                "- Publishing: no ArcGIS item was created.",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "status": "ok",
        "geometry_output_path": _repo_relative_or_absolute(geojson_path),
        "receipt_path": _repo_relative_or_absolute(receipt_path),
        "summary_path": _repo_relative_or_absolute(summary_path),
        "output_folder": _repo_relative_or_absolute(folder),
        "feature_count": receipt["features_downloaded"],
        "warnings": warnings,
        "receipt": receipt,
        "downloaded_geometry": True,
    }
