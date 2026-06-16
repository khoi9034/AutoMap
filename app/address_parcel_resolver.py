"""Address-to-parcel origin resolution using verified AutoMap catalog fields."""

from __future__ import annotations

import re
from typing import Any

from app.parcel_input_parser import ADDRESS_RE, parse_parcel_input
from app.parcel_matcher import match_parcels_by_address, match_parcels_by_identifier
from app.spatial_query_client import SpatialQueryClient


ADDRESS_NOT_MATCHED_WARNING = (
    "Address not matched. AutoMap cannot zoom to or map this address until a valid public "
    "address record or related parcel/PIN is matched."
)

PARCEL_ORIGIN_NOT_MATCHED_WARNING = (
    "Parcel not matched. AutoMap cannot zoom to or map this parcel until a valid parcel/PIN/address is provided."
)


def normalize_address(value: str) -> str:
    """Return a conservative normalized address label for matching/display."""
    cleaned = re.sub(r"\s+", " ", str(value or "").strip())
    cleaned = cleaned.strip(" .,;")
    return cleaned.upper()


def looks_like_address(value: str) -> bool:
    """Return true when text contains a street-address-like token."""
    return bool(ADDRESS_RE.search(value or ""))


def parse_address_parts(value: str) -> dict[str, str | None]:
    """Parse lightweight address parts for display only."""
    match = ADDRESS_RE.search(value or "")
    if not match:
        return {"house_number": None, "street_name": None, "street_suffix": None}
    address = match.group(0).strip()
    parts = address.split()
    if len(parts) < 3:
        return {"house_number": parts[0] if parts else None, "street_name": None, "street_suffix": None}
    return {
        "house_number": parts[0],
        "street_name": " ".join(parts[1:-1]),
        "street_suffix": parts[-1],
    }


def _first_value(rows: list[dict[str, Any]], keys: list[str]) -> Any:
    for row in rows:
        attributes = row.get("attributes") if isinstance(row.get("attributes"), dict) else {}
        for key in keys:
            value = row.get(key) or attributes.get(key)
            if value not in {None, ""}:
                return value
    return None


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


def _candidate_summary(match: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        *(match.get("candidate_matches") or []),
        *(match.get("address_candidates") or []),
    ]


def resolve_address_or_parcel_origin(
    raw_input: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    client: SpatialQueryClient | None = None,
    schema_name: str = "automap",
    match: bool = True,
) -> dict[str, Any]:
    """Resolve a user-supplied origin as address, parcel, PIN, PIN14, or unknown.

    The resolver uses only verified public address/parcel fields exposed through the
    existing parcel matcher. It does not search owner/name fields and never
    downloads countywide parcels.
    """
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
        if not addresses:
            result["match_status"] = "unmatched"
            result["warnings"] = [*warnings, ADDRESS_NOT_MATCHED_WARNING]
            return result
        match_result = match_parcels_by_address(
            addresses,
            layer_catalog=layer_catalog,
            client=client,
            schema_name=schema_name,
        )
        matched_parcels = match_result.get("matched_parcels") or []
        candidates = _candidate_summary(match_result)
        result.update(
            {
                "matched_address_candidates": match_result.get("address_candidates") or candidates,
                "matched_parcel_candidates": matched_parcels,
                "candidate_matches": candidates,
                "unmatched_identifiers": match_result.get("unmatched_identifiers") or [],
                "match_status": match_result.get("match_status") or ("matched" if matched_parcels else "unmatched"),
                "warnings": [*warnings, *(match_result.get("warnings") or [])],
                "source_layer_key": match_result.get("source_layer_key"),
            }
        )
        result["related_pin"] = _first_value(matched_parcels or candidates, ["pin", "PIN"])
        result["related_pin14"] = _first_value(matched_parcels or candidates, ["pin14", "PIN14"])
        result["related_parcel_number"] = _first_value(
            matched_parcels or candidates,
            ["parcel_id", "parcel_number", "PARCEL_ID", "PARCELNUM"],
        )
        if not matched_parcels:
            result["match_status"] = "needs_review" if candidates else "unmatched"
            result["warnings"] = [*result["warnings"], ADDRESS_NOT_MATCHED_WARNING]
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
                "warnings": [*warnings, *(match_result.get("warnings") or [])],
                "source_layer_key": match_result.get("source_layer_key"),
            }
        )
        result["related_pin"] = _first_value(matched_parcels, ["pin", "PIN"])
        result["related_pin14"] = _first_value(matched_parcels, ["pin14", "PIN14"])
        result["related_parcel_number"] = _first_value(matched_parcels, ["parcel_id", "PARCEL_ID"])
        if not matched_parcels:
            result["warnings"] = [*result["warnings"], PARCEL_ORIGIN_NOT_MATCHED_WARNING]
        return result

    result["match_status"] = "unknown"
    result["warnings"] = [*warnings, "No address, parcel ID, PIN, or PIN14 was parsed from the origin input."]
    return result
