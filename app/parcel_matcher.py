"""Safe parcel matching against the verified AutoMap Tax Parcels catalog layer."""

from __future__ import annotations

import json
import re
from typing import Any

from app.field_profiler import infer_field_roles, load_field_profiles
from app.layer_catalog_store import load_catalog_records
from app.spatial_query_client import SpatialQueryClient, SpatialQueryError


PARCEL_MATCH_LIMIT = 100
FIELD_ROLE_KEYS = ("pin14", "pin", "parcel_id", "address", "owner")


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
        if "owner" in compact:
            field_map["owner"].append(name)

    object_id = layer_record.get("object_id_field")
    if object_id:
        field_map.setdefault("object_id", []).append(str(object_id))
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
        if not value:
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
        field_clauses = [f"{field} = {_sql_literal(value)}" for field in candidate_fields]
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

    return validate_parcel_matches(
        {
            "source_layer_key": layer.get("layer_key"),
            "source_layer_name": layer.get("layer_name"),
            "field_map": field_map,
            "matched_count": len(matched),
            "matched_parcels": matched,
            "unmatched_identifiers": unmatched,
            "multiple_match_identifiers": multiple,
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
    return match_parcels_by_identifier(normalized_addresses, **kwargs)
