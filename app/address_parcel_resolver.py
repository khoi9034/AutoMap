"""Address-to-parcel origin resolution using verified AutoMap catalog fields."""

from __future__ import annotations

import re
from typing import Any

from app.address_field_mapper import build_verified_address_field_map
from app.address_normalizer import (
    looks_like_street_address,
    normalize_address_text,
    normalize_for_compare,
    parse_address,
)
from app.parcel_input_parser import parse_parcel_input
from app.parcel_matcher import (
    find_tax_parcel_layer,
    infer_parcel_id_fields,
    match_parcels_by_address,
    match_parcels_by_identifier,
)
from app.spatial_query_client import SpatialQueryClient, SpatialQueryError


ADDRESS_NOT_MATCHED_WARNING = (
    "Address not found in Cabarrus County records. AutoMap's live address lookup currently supports "
    "Cabarrus County, NC only. Try a Cabarrus County address, parcel/PIN, or planning request."
)

SUPPORTED_AREA = "Cabarrus County, NC"
ADDRESS_UNSUPPORTED_AREA_WARNING = ADDRESS_NOT_MATCHED_WARNING

PARCEL_ORIGIN_NOT_MATCHED_WARNING = (
    "Parcel not matched. AutoMap cannot zoom to or map this parcel until a valid parcel/PIN/address is provided."
)

MAX_ADDRESS_CANDIDATES = 20
STRONG_ATTEMPTS = {"exact_normalized_full_address", "house_number_street_core", "full_address_contains"}
SUPPORTED_CABARRUS_PLACE_TERMS = {
    "cabarrus",
    "cabarrus county",
    "concord",
    "harrisburg",
    "kannapolis",
    "locust",
    "midland",
    "mount pleasant",
    "mt pleasant",
}
OUT_OF_SCOPE_COUNTY_TERMS = {
    "mecklenburg county",
    "rowan county",
    "stanly county",
    "union county",
    "gaston county",
    "wake county",
    "iredell county",
    "davidson county",
}
NON_NC_STATE_TOKENS = {
    "al",
    "az",
    "ar",
    "ca",
    "co",
    "ct",
    "de",
    "fl",
    "ga",
    "il",
    "in",
    "ky",
    "md",
    "mi",
    "nj",
    "ny",
    "oh",
    "pa",
    "sc",
    "tn",
    "tx",
    "va",
    "wa",
}


def normalize_address(value: str) -> str:
    """Return a conservative normalized address label for matching/display."""
    parsed = parse_address(value)
    return str(parsed.get("normalized") or normalize_address_text(value)).upper()


def looks_like_address(value: str) -> bool:
    """Return true when text contains a street-address-like token."""
    return looks_like_street_address(value)


def parse_address_parts(value: str) -> dict[str, Any]:
    """Parse lightweight address parts for display and matching diagnostics."""
    parsed = parse_address(value)
    return {
        "house_number": parsed.get("house_number"),
        "street_name_core": parsed.get("street_name_core"),
        "street_name": parsed.get("street_name_core"),
        "suffix": parsed.get("suffix"),
        "street_suffix": parsed.get("suffix"),
        "direction": parsed.get("direction"),
        "city": parsed.get("city"),
        "zip": parsed.get("zip"),
        "address_like": parsed.get("address_like"),
    }


def _city_without_state_or_zip(value: str | None) -> str:
    clean = normalize_address_text(value or "")
    clean = clean.replace("north carolina", "nc")
    clean = re.sub(r"\b\d{5}(?:-\d{4})?\b", " ", clean)
    clean = re.sub(r"\bnc\b", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def _looks_outside_supported_area(value: str, parsed: dict[str, Any]) -> bool:
    """Return true only for obvious out-of-Cabarrus address context."""
    text = f" {normalize_address_text(value)} "
    if any(f" {term} " in text for term in OUT_OF_SCOPE_COUNTY_TERMS):
        return True
    raw_city = value.split(",", 1)[1] if "," in value else ""
    raw_city_clean = _city_without_state_or_zip(raw_city)
    if raw_city_clean and not any(term in raw_city_clean for term in SUPPORTED_CABARRUS_PLACE_TERMS):
        return True
    city = _city_without_state_or_zip(str(parsed.get("city") or ""))
    if city and not any(term in city for term in SUPPORTED_CABARRUS_PLACE_TERMS):
        return True
    city_raw = normalize_address_text(str(parsed.get("city") or ""))
    if city_raw and any(re.search(rf"\b{state}\b", city_raw) for state in NON_NC_STATE_TOKENS):
        return True
    return False


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        clean = str(value or "").strip()
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            output.append(clean)
    return output


def _sql_literal(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _normalized_field_expression(field: str) -> str:
    return f"REPLACE(REPLACE(REPLACE(UPPER({field}), ' ', ''), '.', ''), ',', '')"


def _features_from_query_result(result: dict[str, Any]) -> list[dict[str, Any]]:
    features = result.get("features") or []
    rows: list[dict[str, Any]] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        properties = feature.get("properties") or feature.get("attributes") or {}
        rows.append({"properties": properties, "geometry": feature.get("geometry"), "raw_feature": feature})
    return rows


def _fields(fields_by_role: dict[str, list[str]], roles: list[str]) -> list[str]:
    return _dedupe([field for role in roles for field in (fields_by_role.get(role) or [])])


def _address_text_fields(fields_by_role: dict[str, list[str]]) -> list[str]:
    return _fields(fields_by_role, ["full_address", "site_address", "situs_address", "address"])


def _house_fields(fields_by_role: dict[str, list[str]]) -> list[str]:
    return _fields(fields_by_role, ["house_number", "street_number"])


def _street_fields(fields_by_role: dict[str, list[str]]) -> list[str]:
    return _fields(fields_by_role, ["street_name"])


def _relation_fields(fields_by_role: dict[str, list[str]]) -> list[str]:
    return _fields(fields_by_role, ["pin14", "pin", "parcel_id"])


def _out_fields(fields_by_role: dict[str, list[str]], *, include_geometry_roles: bool = False) -> str:
    roles = [
        "object_id",
        "full_address",
        "site_address",
        "situs_address",
        "address",
        "house_number",
        "street_number",
        "street_name",
        "street_suffix",
        "street_type",
        "street_direction",
        "unit",
        "city",
        "zip",
        "pin14",
        "pin",
        "parcel_id",
    ]
    if include_geometry_roles:
        roles.append("geometry")
    fields = _fields(fields_by_role, roles)
    return ",".join(fields) if fields else "*"


def _first_value(properties: dict[str, Any], fields: list[str]) -> Any:
    for field in fields:
        value = properties.get(field)
        if value not in {None, ""}:
            return value
    return None


def _candidate_from_feature(
    feature: dict[str, Any],
    *,
    fields_by_role: dict[str, list[str]],
    source_layer_key: str | None,
    source_layer_name: str | None,
    source_type: str,
    attempt: str,
    count: int,
) -> dict[str, Any]:
    properties = feature.get("properties") or {}
    house = _first_value(properties, _house_fields(fields_by_role))
    street = _first_value(properties, _street_fields(fields_by_role))
    suffix = _first_value(properties, _fields(fields_by_role, ["street_suffix", "street_type"]))
    direction = _first_value(properties, _fields(fields_by_role, ["street_direction"]))
    display_address = (
        _first_value(properties, _address_text_fields(fields_by_role))
        or " ".join(str(part) for part in [house, direction, street, suffix] if part not in {None, ""})
        or None
    )
    candidate = {
        "display_address": display_address,
        "address": display_address,
        "city": _first_value(properties, _fields(fields_by_role, ["city"])),
        "zip": _first_value(properties, _fields(fields_by_role, ["zip"])),
        "pin": _first_value(properties, _fields(fields_by_role, ["pin"])),
        "pin14": _first_value(properties, _fields(fields_by_role, ["pin14"])),
        "parcel_id": _first_value(properties, _fields(fields_by_role, ["parcel_id"])),
        "object_id": _first_value(properties, _fields(fields_by_role, ["object_id"])),
        "attributes": properties,
        "source_layer_key": source_layer_key,
        "source_layer_name": source_layer_name,
        "candidate_type": source_type,
        "match_attempt": attempt,
        "count": count,
        "needs_review": count != 1 or attempt not in STRONG_ATTEMPTS,
    }
    return {key: value for key, value in candidate.items() if value is not None and value != ""}


def _related_identifiers(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    identifiers: list[dict[str, Any]] = []
    for candidate in candidates:
        for role in ["pin14", "pin", "parcel_id"]:
            value = candidate.get(role)
            if value in {None, ""}:
                continue
            identifiers.append(
                {
                    "identifier_type": role,
                    "value": str(value),
                    "normalized_value": str(value).upper(),
                    "source_text": str(candidate.get("display_address") or candidate.get("address") or ""),
                    "confidence": 0.78,
                    "needs_review": True,
                    "notes": ["Matched through verified public address/parcel relation field."],
                }
            )
            break
    return identifiers


def _exact_full_address_where(parsed: dict[str, Any], fields: list[str]) -> str | None:
    variants = _dedupe([*(parsed.get("normalized_variants") or []), str(parsed.get("normalized") or "")])
    if not fields or not variants:
        return None
    clauses: list[str] = []
    for field in fields:
        clauses.extend(f"UPPER({field}) = {_sql_literal(variant.upper())}" for variant in variants)
        comparison_keys = _dedupe([normalize_for_compare(variant) for variant in variants])
        clauses.extend(f"{_normalized_field_expression(field)} = {_sql_literal(key)}" for key in comparison_keys if key)
    return " OR ".join(clauses) if clauses else None


def _house_street_where(parsed: dict[str, Any], fields_by_role: dict[str, list[str]]) -> str | None:
    house = str(parsed.get("house_number") or "").strip()
    street_core = str(parsed.get("street_name_core") or "").strip().upper()
    house_fields = _house_fields(fields_by_role)
    street_fields = _street_fields(fields_by_role)
    if not house or not street_core or not house_fields or not street_fields:
        return None
    house_clause = " OR ".join(f"UPPER({field}) = {_sql_literal(house.upper())}" for field in house_fields)
    street_clause = " OR ".join(f"UPPER({field}) LIKE {_sql_literal('%' + street_core + '%')}" for field in street_fields)
    return f"({house_clause}) AND ({street_clause})"


def _full_address_contains_where(parsed: dict[str, Any], fields: list[str]) -> str | None:
    house = str(parsed.get("house_number") or "").strip()
    street_core = str(parsed.get("street_name_core") or "").strip().upper()
    if not house or not street_core or not fields:
        return None
    clauses = [
        f"(UPPER({field}) LIKE {_sql_literal('%' + house.upper() + '%')} AND UPPER({field}) LIKE {_sql_literal('%' + street_core + '%')})"
        for field in fields
    ]
    return " OR ".join(clauses)


def _street_only_where(parsed: dict[str, Any], fields_by_role: dict[str, list[str]]) -> str | None:
    street_core = str(parsed.get("street_name_core") or "").strip().upper()
    if not street_core:
        return None
    fields = _street_fields(fields_by_role) or _address_text_fields(fields_by_role)
    if not fields:
        return None
    return " OR ".join(f"UPPER({field}) LIKE {_sql_literal('%' + street_core + '%')}" for field in fields)


def _address_attempts(parsed: dict[str, Any], fields_by_role: dict[str, list[str]], *, source: str) -> list[dict[str, Any]]:
    text_fields = _address_text_fields(fields_by_role)
    attempts = [
        {
            "attempt": "exact_normalized_full_address",
            "where": _exact_full_address_where(parsed, text_fields),
            "match_strength": "strong",
            "source": source,
        },
        {
            "attempt": "house_number_street_core",
            "where": _house_street_where(parsed, fields_by_role),
            "match_strength": "strong",
            "source": source,
        },
        {
            "attempt": "full_address_contains",
            "where": _full_address_contains_where(parsed, text_fields),
            "match_strength": "strong",
            "source": source,
        },
        {
            "attempt": "street_only_candidates",
            "where": _street_only_where(parsed, fields_by_role),
            "match_strength": "candidate",
            "source": source,
        },
    ]
    return [attempt for attempt in attempts if attempt.get("where")]


def _run_match_attempt(
    *,
    attempt: dict[str, Any],
    layer_url: str,
    layer_key: str | None,
    layer_name: str | None,
    fields_by_role: dict[str, list[str]],
    client: SpatialQueryClient,
    fetch_geometry: bool,
    max_candidates: int,
) -> dict[str, Any]:
    where = str(attempt["where"])
    diagnostics: dict[str, Any] = {
        "source": attempt.get("source"),
        "attempt": attempt.get("attempt"),
        "where": where,
        "returnGeometry_first": False,
        "count": None,
        "returned_candidates": 0,
        "geometry_fetched": False,
    }
    try:
        count_result = client.query_count(layer_url, where=where)
        count = int(count_result.get("count") or 0)
        diagnostics["count"] = count
    except Exception as exc:
        diagnostics["error"] = str(exc)
        return {"status": "query_failed", "diagnostics": diagnostics, "warnings": [f"Address query attempt {attempt.get('attempt')} failed safely: {exc}"]}

    if count == 0:
        return {"status": "no_match", "diagnostics": diagnostics, "warnings": []}
    if count > max_candidates:
        return {
            "status": "ambiguous",
            "diagnostics": diagnostics,
            "candidate_matches": [],
            "warnings": [
                f"Address query attempt {attempt.get('attempt')} matched {count} records; add city, ZIP, or directional suffix to narrow it."
            ],
        }

    strong_single = count == 1 and attempt.get("match_strength") == "strong"
    return_geometry = bool(fetch_geometry and strong_single)
    try:
        query = client.query_features(
            layer_url,
            where=where,
            out_fields=_out_fields(fields_by_role),
            return_geometry=return_geometry,
            result_record_count=max(count, 1),
        )
    except SpatialQueryError as exc:
        diagnostics["error"] = str(exc)
        return {"status": "query_failed", "diagnostics": diagnostics, "warnings": [f"Address candidate query failed safely: {exc}"]}

    rows = _features_from_query_result(query)
    diagnostics["returned_candidates"] = len(rows)
    diagnostics["geometry_fetched"] = return_geometry
    candidates = [
        _candidate_from_feature(
            row,
            fields_by_role=fields_by_role,
            source_layer_key=layer_key,
            source_layer_name=layer_name,
            source_type=str(attempt.get("source") or "address"),
            attempt=str(attempt.get("attempt") or ""),
            count=count,
        )
        for row in rows
    ]
    if strong_single and rows:
        raw_feature = rows[0].get("raw_feature") or {}
        return {
            "status": "matched",
            "diagnostics": diagnostics,
            "candidate_matches": candidates,
            "matched_feature": raw_feature if return_geometry else None,
            "matched_attributes": rows[0].get("properties") or {},
            "warnings": [],
        }
    return {
        "status": "ambiguous",
        "diagnostics": diagnostics,
        "candidate_matches": candidates,
        "warnings": [f"Address matched {count} candidates; choose one before creating a focused map."],
    }


def _address_layer_match(
    address: str,
    *,
    client: SpatialQueryClient,
    schema_name: str,
    fetch_geometry: bool,
    max_candidates: int,
) -> dict[str, Any]:
    field_map = build_verified_address_field_map(schema_name=schema_name)
    layer_url = field_map.get("layer_url")
    fields_by_role = field_map.get("fields_by_role") or {}
    parsed = parse_address(address)
    diagnostics: list[dict[str, Any]] = []
    warnings = list(field_map.get("warnings") or [])
    if not layer_url:
        return {
            "status": "not_available",
            "candidate_matches": [],
            "query_attempts": diagnostics,
            "warnings": [*warnings, "No verified Addresses layer URL is available."],
            "field_map": field_map,
        }
    attempts = _address_attempts(parsed, fields_by_role, source="addresses_layer")
    if not attempts:
        return {
            "status": "not_available",
            "candidate_matches": [],
            "query_attempts": diagnostics,
            "warnings": [*warnings, "No verified public address fields were mapped for progressive address matching."],
            "field_map": field_map,
        }

    for attempt in attempts:
        result = _run_match_attempt(
            attempt=attempt,
            layer_url=str(layer_url),
            layer_key=field_map.get("layer_key"),
            layer_name=field_map.get("layer_name"),
            fields_by_role=fields_by_role,
            client=client,
            fetch_geometry=fetch_geometry,
            max_candidates=max_candidates,
        )
        diagnostics.append(result["diagnostics"])
        warnings.extend(result.get("warnings") or [])
        if result["status"] in {"matched", "ambiguous"} and (result.get("candidate_matches") or result["status"] == "matched"):
            return {**result, "query_attempts": diagnostics, "warnings": warnings, "field_map": field_map}
    return {"status": "unmatched", "candidate_matches": [], "query_attempts": diagnostics, "warnings": warnings, "field_map": field_map}


def _parcel_address_fields(field_map: dict[str, list[str]]) -> dict[str, list[str]]:
    return {
        "object_id": field_map.get("object_id") or [],
        "full_address": field_map.get("address") or [],
        "address": field_map.get("address") or [],
        "pin": field_map.get("pin") or [],
        "pin14": field_map.get("pin14") or [],
        "parcel_id": field_map.get("parcel_id") or [],
    }


def _parcel_address_match(
    address: str,
    *,
    layer_catalog: list[dict[str, Any]] | None,
    client: SpatialQueryClient,
    schema_name: str,
    fetch_geometry: bool,
    max_candidates: int,
) -> dict[str, Any]:
    layer = find_tax_parcel_layer(layer_catalog, schema_name=schema_name)
    diagnostics: list[dict[str, Any]] = []
    if not layer:
        return {
            "status": "not_available",
            "candidate_matches": [],
            "query_attempts": diagnostics,
            "warnings": ["No verified Tax Parcels layer is available for parcel-address fallback matching."],
            "field_map": {},
        }
    layer_url = layer.get("layer_url") or layer.get("rest_url")
    if not layer_url:
        return {
            "status": "not_available",
            "candidate_matches": [],
            "query_attempts": diagnostics,
            "warnings": ["Verified Tax Parcels layer has no REST layer URL for parcel-address fallback matching."],
            "field_map": {},
        }
    raw_field_map = infer_parcel_id_fields(layer, schema_name=schema_name)
    fields_by_role = _parcel_address_fields(raw_field_map)
    parsed = parse_address(address)
    attempts = _address_attempts(parsed, fields_by_role, source="tax_parcels_address_fields")
    if not attempts:
        return {
            "status": "not_available",
            "candidate_matches": [],
            "query_attempts": diagnostics,
            "warnings": ["No verified Tax Parcels address fields were mapped for fallback matching."],
            "field_map": fields_by_role,
        }
    for attempt in attempts:
        result = _run_match_attempt(
            attempt=attempt,
            layer_url=str(layer_url),
            layer_key=layer.get("layer_key"),
            layer_name=layer.get("layer_name"),
            fields_by_role=fields_by_role,
            client=client,
            fetch_geometry=fetch_geometry,
            max_candidates=max_candidates,
        )
        diagnostics.append(result["diagnostics"])
        if result["status"] in {"matched", "ambiguous"} and (result.get("candidate_matches") or result["status"] == "matched"):
            return {**result, "query_attempts": diagnostics, "warnings": result.get("warnings") or [], "field_map": fields_by_role}
    return {"status": "unmatched", "candidate_matches": [], "query_attempts": diagnostics, "warnings": [], "field_map": fields_by_role}


def resolve_verified_address(
    address: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    client: SpatialQueryClient | None = None,
    schema_name: str = "automap",
    fetch_geometry: bool = True,
    max_candidates: int = MAX_ADDRESS_CANDIDATES,
    scope_input: str | None = None,
) -> dict[str, Any]:
    """Resolve an address through verified address and parcel address fields.

    All attempts run count-only first. Geometry is requested only for an exact
    safely narrowed match. Owner/name fields are never searched.
    """
    query_client = client or SpatialQueryClient(max_features=max_candidates, timeout=6)
    parsed = parse_address(address)
    normalized_variants = parsed.get("normalized_variants") or []
    query_attempts: list[dict[str, Any]] = []
    warnings: list[str] = []

    if _looks_outside_supported_area(scope_input or address, parsed):
        return {
            "status": "unsupported_area",
            "match_status": "unsupported_area",
            "origin_type": "address",
            "normalized_address": normalize_address(address),
            "normalized_variants": normalized_variants,
            "parsed_address_parts": parse_address_parts(address),
            "origin_feature": None,
            "matched_address_candidates": [],
            "matched_parcel_candidates": [],
            "candidate_matches": [],
            "related_identifiers": [],
            "related_pin": None,
            "related_pin14": None,
            "related_parcel_number": None,
            "query_attempts": query_attempts,
            "address_fields_used": [],
            "parcel_address_fields_used": [],
            "warnings": [ADDRESS_UNSUPPORTED_AREA_WARNING],
            "can_preview": False,
            "downloaded_geometry": False,
            "owner_lookup_used": False,
            "supported_area": SUPPORTED_AREA,
        }

    address_result = _address_layer_match(
        address,
        client=query_client,
        schema_name=schema_name,
        fetch_geometry=fetch_geometry,
        max_candidates=max_candidates,
    )
    query_attempts.extend(address_result.get("query_attempts") or [])
    warnings.extend(address_result.get("warnings") or [])
    if address_result.get("status") in {"matched", "ambiguous"}:
        candidates = address_result.get("candidate_matches") or []
        status = "matched" if address_result["status"] == "matched" else "ambiguous"
        return {
            "status": status,
            "match_status": status,
            "origin_type": "address",
            "normalized_address": normalize_address(address),
            "normalized_variants": normalized_variants,
            "parsed_address_parts": parse_address_parts(address),
            "origin_feature": address_result.get("matched_feature"),
            "matched_address_candidates": candidates,
            "matched_parcel_candidates": [],
            "candidate_matches": [] if status == "matched" else candidates,
            "related_identifiers": _related_identifiers(candidates),
            "related_pin": _first_related(candidates, "pin"),
            "related_pin14": _first_related(candidates, "pin14"),
            "related_parcel_number": _first_related(candidates, "parcel_id"),
            "source_layer_key": (candidates[0].get("source_layer_key") if candidates else None),
            "source_layer_name": (candidates[0].get("source_layer_name") if candidates else None),
            "query_attempts": query_attempts,
            "address_fields_used": _address_text_fields((address_result.get("field_map") or {}).get("fields_by_role") or {}),
            "parcel_address_fields_used": [],
            "warnings": _dedupe_warnings(warnings if status == "matched" else [*warnings, "Multiple possible address matches were found; choose a candidate before preview."]),
            "can_preview": status == "matched" and bool(address_result.get("matched_feature") or not fetch_geometry),
            "downloaded_geometry": bool(address_result.get("matched_feature")),
            "owner_lookup_used": False,
            "supported_area": SUPPORTED_AREA,
        }

    parcel_result = _parcel_address_match(
        address,
        layer_catalog=layer_catalog,
        client=query_client,
        schema_name=schema_name,
        fetch_geometry=fetch_geometry,
        max_candidates=max_candidates,
    )
    query_attempts.extend(parcel_result.get("query_attempts") or [])
    warnings.extend(parcel_result.get("warnings") or [])
    if parcel_result.get("status") in {"matched", "ambiguous"}:
        candidates = parcel_result.get("candidate_matches") or []
        status = "matched" if parcel_result["status"] == "matched" else "ambiguous"
        return {
            "status": status,
            "match_status": status,
            "origin_type": "address",
            "normalized_address": normalize_address(address),
            "normalized_variants": normalized_variants,
            "parsed_address_parts": parse_address_parts(address),
            "origin_feature": parcel_result.get("matched_feature"),
            "matched_address_candidates": [],
            "matched_parcel_candidates": candidates if status == "matched" else [],
            "candidate_matches": [] if status == "matched" else candidates,
            "related_identifiers": _related_identifiers(candidates),
            "related_pin": _first_related(candidates, "pin"),
            "related_pin14": _first_related(candidates, "pin14"),
            "related_parcel_number": _first_related(candidates, "parcel_id"),
            "source_layer_key": (candidates[0].get("source_layer_key") if candidates else None),
            "source_layer_name": (candidates[0].get("source_layer_name") if candidates else None),
            "query_attempts": query_attempts,
            "address_fields_used": [],
            "parcel_address_fields_used": _address_text_fields(parcel_result.get("field_map") or {}),
            "warnings": _dedupe_warnings(warnings if status == "matched" else [*warnings, "Multiple possible parcel-address matches were found; choose a candidate before preview."]),
            "can_preview": status == "matched" and bool(parcel_result.get("matched_feature") or not fetch_geometry),
            "downloaded_geometry": bool(parcel_result.get("matched_feature")),
            "owner_lookup_used": False,
            "supported_area": SUPPORTED_AREA,
        }

    return {
        "status": "unmatched",
        "match_status": "unmatched",
        "origin_type": "address",
        "normalized_address": normalize_address(address),
        "normalized_variants": normalized_variants,
        "parsed_address_parts": parse_address_parts(address),
        "origin_feature": None,
        "matched_address_candidates": [],
        "matched_parcel_candidates": [],
        "candidate_matches": [],
        "related_identifiers": [],
        "related_pin": None,
        "related_pin14": None,
        "related_parcel_number": None,
        "query_attempts": query_attempts,
        "address_fields_used": _address_text_fields((address_result.get("field_map") or {}).get("fields_by_role") or {}),
        "parcel_address_fields_used": _address_text_fields(parcel_result.get("field_map") or {}),
        "warnings": _dedupe_warnings([*warnings, ADDRESS_NOT_MATCHED_WARNING]),
        "can_preview": False,
        "downloaded_geometry": False,
        "owner_lookup_used": False,
        "supported_area": SUPPORTED_AREA,
    }


def _first_related(candidates: list[dict[str, Any]], key: str) -> Any:
    for candidate in candidates:
        value = candidate.get(key)
        if value not in {None, ""}:
            return value
    return None


def _dedupe_warnings(warnings: list[str]) -> list[str]:
    return _dedupe([str(warning) for warning in warnings if warning])


def _origin_type(parsed: dict[str, Any]) -> str:
    if parsed.get("address_candidates") and not parsed.get("parsed_identifiers"):
        return "address"
    input_type = str(parsed.get("input_type") or "unknown")
    if input_type in {"address", "pin", "pin14", "parcel_id"}:
        return input_type
    identifiers = parsed.get("parsed_identifiers") or []
    if identifiers:
        return str(identifiers[0].get("identifier_type") or "parcel")
    return "address" if parsed.get("address_candidates") else "unknown"


def resolve_address_or_parcel_origin(
    raw_input: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    client: SpatialQueryClient | None = None,
    schema_name: str = "automap",
    match: bool = True,
) -> dict[str, Any]:
    """Resolve a user-supplied origin as address, parcel, PIN, PIN14, or unknown."""
    parsed = parse_parcel_input(raw_input)
    origin_type = _origin_type(parsed)
    identifiers = list(parsed.get("parsed_identifiers") or [])
    addresses = list(parsed.get("address_candidates") or [])
    warnings = list(parsed.get("warnings") or [])
    normalized_address = normalize_address(addresses[0]["value"]) if addresses else None

    result: dict[str, Any] = {
        "raw_input": raw_input,
        "origin_type": origin_type,
        "normalized_address": normalized_address,
        "parsed_address_parts": parse_address_parts(addresses[0]["value"] if addresses else raw_input),
        "parsed_identifiers": identifiers,
        "address_candidates": addresses,
        "matched_address_candidates": [],
        "matched_parcel_candidates": [],
        "related_pin": None,
        "related_pin14": None,
        "related_parcel_number": None,
        "match_status": "needs_review" if parsed.get("parcel_intent") else "unknown",
        "warnings": warnings,
        "downloaded_geometry": False,
        "owner_lookup_used": False,
    }
    if not match:
        return result

    if origin_type == "address":
        address_value = addresses[0]["value"] if addresses else raw_input
        address_result = resolve_verified_address(
            address_value,
            layer_catalog=layer_catalog,
            client=client,
            schema_name=schema_name,
            fetch_geometry=True,
            scope_input=raw_input,
        )
        result.update(
            {
                "matched_address_candidates": address_result.get("matched_address_candidates") or [],
                "matched_parcel_candidates": address_result.get("matched_parcel_candidates") or [],
                "candidate_matches": address_result.get("candidate_matches") or [],
                "unmatched_identifiers": [] if address_result.get("match_status") == "matched" else addresses,
                "match_status": address_result.get("match_status") or address_result.get("status"),
                "warnings": _dedupe_warnings([*warnings, *(address_result.get("warnings") or [])]),
                "source_layer_key": address_result.get("source_layer_key"),
                "related_pin": address_result.get("related_pin"),
                "related_pin14": address_result.get("related_pin14"),
                "related_parcel_number": address_result.get("related_parcel_number"),
                "normalized_address": address_result.get("normalized_address"),
                "normalized_variants": address_result.get("normalized_variants") or [],
                "query_attempts": address_result.get("query_attempts") or [],
                "address_fields_used": address_result.get("address_fields_used") or [],
                "parcel_address_fields_used": address_result.get("parcel_address_fields_used") or [],
                "downloaded_geometry": bool(address_result.get("downloaded_geometry")),
                "can_preview": bool(address_result.get("can_preview")),
                "supported_area": address_result.get("supported_area"),
            }
        )
        return result

    if identifiers:
        match_result = match_parcels_by_identifier(
            identifiers,
            layer_catalog=layer_catalog,
            client=client,
            schema_name=schema_name,
        )
        matched_parcels = match_result.get("matched_parcels") or []
        result.update(
            {
                "matched_parcel_candidates": matched_parcels,
                "candidate_matches": match_result.get("candidate_matches") or [],
                "unmatched_identifiers": match_result.get("unmatched_identifiers") or [],
                "match_status": match_result.get("match_status") or ("matched" if matched_parcels else "unmatched"),
                "warnings": _dedupe_warnings([*warnings, *(match_result.get("warnings") or [])]),
                "source_layer_key": match_result.get("source_layer_key"),
            }
        )
        result["related_pin"] = _first_related(matched_parcels, "pin")
        result["related_pin14"] = _first_related(matched_parcels, "pin14")
        result["related_parcel_number"] = _first_related(matched_parcels, "parcel_id")
        if not matched_parcels:
            result["warnings"] = _dedupe_warnings([*result["warnings"], PARCEL_ORIGIN_NOT_MATCHED_WARNING])
        return result

    result["match_status"] = "unknown"
    result["warnings"] = _dedupe_warnings([*warnings, "No address, parcel ID, PIN, or PIN14 was parsed from the origin input."])
    return result


def debug_address_match(
    address: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    client: SpatialQueryClient | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Return verbose diagnostics for one address matching request."""
    parsed = parse_address(address)
    result = resolve_verified_address(
        address,
        layer_catalog=layer_catalog,
        client=client,
        schema_name=schema_name,
        fetch_geometry=True,
    )
    return {
        "input": address,
        "normalized_address": normalize_address(address),
        "normalized_variants": parsed.get("normalized_variants") or [],
        "parsed_address_parts": parse_address_parts(address),
        "address_fields_used": result.get("address_fields_used") or [],
        "parcel_address_fields_used": result.get("parcel_address_fields_used") or [],
        "query_attempts": result.get("query_attempts") or [],
        "candidate_matches": result.get("candidate_matches") or result.get("matched_address_candidates") or result.get("matched_parcel_candidates") or [],
        "matched_address_candidates": result.get("matched_address_candidates") or [],
        "matched_parcel_candidates": result.get("matched_parcel_candidates") or [],
        "related_pin": result.get("related_pin"),
        "related_pin14": result.get("related_pin14"),
        "related_parcel_number": result.get("related_parcel_number"),
        "match_status": result.get("match_status") or result.get("status"),
        "geometry_fetched": bool(result.get("downloaded_geometry")),
        "warnings": result.get("warnings") or [],
        "owner_lookup_used": False,
    }
