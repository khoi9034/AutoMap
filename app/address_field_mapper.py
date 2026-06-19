"""Verified field-role mapping for AutoMap address lookup workflows."""

from __future__ import annotations

import re
from typing import Any

from app.field_profiler import load_field_profiles, profile_layer_fields
from app.layer_catalog_store import load_catalog_records
from app.parcel_field_mapper import ensure_parcel_field_map_table, _store_field_map


ADDRESS_FIELD_ROLES = (
    "full_address",
    "site_address",
    "situs_address",
    "house_number",
    "street_number",
    "street_name",
    "street_suffix",
    "street_type",
    "street_direction",
    "unit",
    "city",
    "zip",
    "pin",
    "pin14",
    "parcel_id",
    "object_id",
    "geometry",
)


def _text_blob(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).lower()


def _compact(*values: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _text_blob(*values))


def _field_name(profile: dict[str, Any]) -> str:
    return str(profile.get("field_name") or profile.get("name") or "")


def _field_alias(profile: dict[str, Any]) -> str:
    return str(profile.get("field_alias") or profile.get("alias") or "")


def _role_row(profile: dict[str, Any], role: str, score: float, notes: str) -> dict[str, Any]:
    return {
        "layer_key": profile.get("layer_key"),
        "field_role": role,
        "field_name": _field_name(profile),
        "field_alias": _field_alias(profile),
        "confidence_score": score,
        "notes": notes,
    }


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: float(item.get("confidence_score") or 0), reverse=True):
        key = (str(row.get("field_role") or ""), str(row.get("field_name") or "").lower())
        if key in seen or not key[1]:
            continue
        seen.add(key)
        output.append(row)
    return output


def _find_address_layer() -> dict[str, Any] | None:
    candidates: list[dict[str, Any]] = []
    for record in load_catalog_records():
        blob = _text_blob(record.get("layer_name"), record.get("service_name"), record.get("aliases"), record.get("canonical_topic"))
        if (
            record.get("is_verified")
            and record.get("is_active", True)
            and not record.get("is_group_layer")
            and not record.get("is_historical")
            and (record.get("category") == "address" or "address" in blob)
        ):
            candidates.append(record)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (int(item.get("source_priority") or 999), str(item.get("layer_name") or "")))[0]


def _profiles_for_layer(layer_record: dict[str, Any], schema_name: str) -> list[dict[str, Any]]:
    layer_key = layer_record.get("layer_key")
    profiles: list[dict[str, Any]] = []
    if layer_key:
        profiles = load_field_profiles([layer_key], schema_name=schema_name).get(layer_key, [])
    if not profiles and layer_key:
        try:
            profiles = profile_layer_fields(layer_record).get("field_profiles") or []
        except Exception:
            profiles = []
    return [profile for profile in profiles if _field_name(profile)]


def profile_address_fields(schema_name: str = "automap") -> dict[str, Any]:
    """Return verified field profiles for the trusted Addresses layer."""
    layer = _find_address_layer()
    if not layer:
        return {"layer": None, "profiles": [], "warnings": ["No verified Addresses layer is available."]}
    return {"layer": layer, "profiles": _profiles_for_layer(layer, schema_name), "warnings": []}


def identify_address_fields(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Identify address-related field roles from verified profiles."""
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        name = _field_name(profile)
        alias = _field_alias(profile)
        compact = _compact(name, alias)
        if profile.get("is_object_id") or compact in {"objectid", "objectid1", "fid", "oid"}:
            rows.append(_role_row(profile, "object_id", 0.99, "Object ID field identified from ArcGIS field type/profile."))
        if profile.get("is_geometry_field") or compact in {"shape", "geometry"}:
            rows.append(_role_row(profile, "geometry", 0.99, "Geometry field identified from ArcGIS field type/profile."))
        if "pin14" in compact:
            rows.append(_role_row(profile, "pin14", 0.9, "Address field appears to carry PIN14."))
        elif compact == "pin" or re.search(r"\bpin\b", _text_blob(name, alias)):
            rows.append(_role_row(profile, "pin", 0.88, "Address field appears to carry PIN."))
        if any(term in compact for term in ["parcelid", "parcelnum", "propertyrealid", "parcelnumber"]):
            rows.append(_role_row(profile, "parcel_id", 0.82, "Address field appears to carry parcel relation."))
        if (
            any(term in compact for term in ["fulladdress", "wholeaddress", "siteaddress", "situsaddress", "completeaddress", "concat", "concatfull"])
            or compact in {"address", "addr"}
        ):
            rows.append(_role_row(profile, "full_address", 0.9, "Field appears to contain address text."))
        if any(term in compact for term in ["siteaddress", "propertyaddress", "locationaddress", "locaddress"]):
            rows.append(_role_row(profile, "site_address", 0.86, "Field appears to contain site/location address text."))
        if any(term in compact for term in ["situsaddress", "situsaddr", "premiseaddress"]):
            rows.append(_role_row(profile, "situs_address", 0.86, "Field appears to contain situs address text."))
        if any(term in compact for term in ["housenum", "addrnum", "addressnum", "streetnumber"]):
            rows.append(_role_row(profile, "house_number", 0.78, "Field appears to contain address number."))
        if any(term in compact for term in ["streetnum", "stnum", "strnum"]):
            rows.append(_role_row(profile, "street_number", 0.76, "Field appears to contain street number."))
        if any(term in compact for term in ["streetname", "stname", "plainst", "roadname"]):
            rows.append(_role_row(profile, "street_name", 0.78, "Field appears to contain street name."))
        if any(term in compact for term in ["streetsuffix", "stsuffix", "streettype", "sttype", "roadtype"]):
            rows.append(_role_row(profile, "street_suffix", 0.74, "Field appears to contain street suffix/type."))
            rows.append(_role_row(profile, "street_type", 0.72, "Field appears to contain street type."))
        if any(term in compact for term in ["streetdirection", "stdirection", "predir", "postdir", "prefixdirection", "suffixdirection"]):
            rows.append(_role_row(profile, "street_direction", 0.72, "Field appears to contain street direction."))
        if any(term in compact for term in ["unit", "apartment", "suite", "apt", "ste"]):
            rows.append(_role_row(profile, "unit", 0.68, "Field appears to contain unit/suite text."))
        if any(term in compact for term in ["city", "municipality", "town"]):
            rows.append(_role_row(profile, "city", 0.7, "Field appears to contain locality."))
        if compact in {"zip", "zipcode", "postalcode", "zip5"} or any(term in compact for term in ["zip", "postal"]):
            rows.append(_role_row(profile, "zip", 0.7, "Field appears to contain ZIP/postal code."))
    return _dedupe(rows)


def build_verified_address_field_map(schema_name: str = "automap") -> dict[str, Any]:
    """Build and store role mappings for the verified Addresses layer."""
    ensure_parcel_field_map_table(schema_name)
    profile = profile_address_fields(schema_name)
    layer = profile.get("layer")
    profiles = profile.get("profiles") or []
    if not layer:
        return {
            "layer_key": None,
            "fields_by_role": {role: [] for role in ADDRESS_FIELD_ROLES},
            "role_rows": [],
            "geometry_supported": False,
            "warnings": profile.get("warnings") or [],
            "stored_rows": 0,
        }
    role_rows = identify_address_fields(profiles)
    for row in role_rows:
        row["layer_key"] = layer.get("layer_key")
    stored = _store_field_map(role_rows, schema_name)
    fields_by_role: dict[str, list[str]] = {role: [] for role in ADDRESS_FIELD_ROLES}
    for row in role_rows:
        fields_by_role.setdefault(row["field_role"], []).append(row["field_name"])
    return {
        "layer_key": layer.get("layer_key"),
        "layer_name": layer.get("layer_name"),
        "layer_url": layer.get("layer_url") or layer.get("rest_url"),
        "fields_by_role": fields_by_role,
        "role_rows": role_rows,
        "geometry_supported": bool(layer.get("geometry_type") or fields_by_role.get("geometry")),
        "warnings": profile.get("warnings") or [],
        "stored_rows": stored,
    }
