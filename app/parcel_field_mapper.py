"""Verified field-role mapping for AutoMap parcel lookup workflows."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import text

from app.db import _quote_identifier, get_engine
from app.field_profiler import load_field_profiles, profile_layer_fields
from app.layer_catalog_store import load_catalog_records


PARCEL_FIELD_ROLES = ("pin", "pin14", "parcel_id", "address", "object_id", "geometry")


def _qualified_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.parcel_field_map"


def ensure_parcel_field_map_table(schema_name: str = "automap") -> None:
    """Create the AutoMap field-role map table without dropping anything."""
    table = _qualified_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY,
                    layer_key text,
                    field_role text,
                    field_name text,
                    field_alias text,
                    confidence_score numeric,
                    notes text,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "layer_key": "text",
            "field_role": "text",
            "field_name": "text",
            "field_alias": "text",
            "confidence_score": "numeric",
            "notes": "text",
            "created_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS parcel_field_map_layer_role_field_uidx
                ON {table} (layer_key, field_role, field_name);
                """
            )
        )


def _text_blob(*values: Any) -> str:
    return " ".join(str(value or "") for value in values).lower()


def _compact(*values: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", _text_blob(*values))


def _field_name(profile: dict[str, Any]) -> str:
    return str(profile.get("field_name") or profile.get("name") or "")


def _field_alias(profile: dict[str, Any]) -> str:
    return str(profile.get("field_alias") or profile.get("alias") or "")


def _dedupe_role_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for row in sorted(rows, key=lambda item: float(item.get("confidence_score") or 0), reverse=True):
        key = (str(row.get("field_role") or ""), str(row.get("field_name") or "").lower())
        if key in seen or not key[1]:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def _best_active_layer(categories: set[str], terms: list[str]) -> dict[str, Any] | None:
    terms_lower = [term.lower() for term in terms]
    candidates: list[dict[str, Any]] = []
    for record in load_catalog_records():
        blob = _text_blob(record.get("layer_name"), record.get("service_name"), record.get("aliases"), record.get("canonical_topic"))
        if (
            record.get("is_verified")
            and record.get("is_active", True)
            and not record.get("is_group_layer")
            and not record.get("is_historical")
            and (record.get("category") in categories or record.get("canonical_topic") in categories or any(term in blob for term in terms_lower))
        ):
            candidates.append(record)
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


def find_tax_parcel_layer() -> dict[str, Any] | None:
    """Find the trusted current Tax Parcels layer from AutoMap's verified catalog."""
    candidates: list[dict[str, Any]] = []
    for record in load_catalog_records():
        blob = _text_blob(record.get("layer_name"), record.get("service_name"), record.get("aliases"), record.get("canonical_topic"))
        if not (
            record.get("is_verified")
            and record.get("is_active", True)
            and not record.get("is_group_layer")
            and not record.get("is_historical")
        ):
            continue
        if record.get("category") == "parcel" or "tax parcel" in blob or "tax_parcels" in blob:
            candidates.append(record)
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda item: (
            0 if item.get("category") == "parcel" else 1,
            int(item.get("source_priority") or 999),
            0 if "tax" in _text_blob(item.get("layer_name"), item.get("service_name")) else 1,
            str(item.get("layer_name") or ""),
        ),
    )[0]


def _profiles_from_catalog_fields(layer_record: dict[str, Any]) -> list[dict[str, Any]]:
    fields = layer_record.get("fields") or []
    if isinstance(fields, str):
        try:
            fields = json.loads(fields)
        except json.JSONDecodeError:
            fields = []
    if not isinstance(fields, list):
        return []
    profiles: list[dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        name = field.get("name")
        alias = field.get("alias")
        field_type = field.get("type")
        lower_name = str(name or "").lower()
        profiles.append(
            {
                "layer_key": layer_record.get("layer_key"),
                "layer_url": layer_record.get("layer_url") or layer_record.get("rest_url"),
                "field_name": name,
                "field_alias": alias,
                "field_type": field_type,
                "is_object_id": field_type == "esriFieldTypeOID" or lower_name in {"objectid", "objectid_1", "fid", "oid"},
                "is_geometry_field": field_type == "esriFieldTypeGeometry" or lower_name in {"shape", "geometry"},
                "is_address_candidate": any(term in _compact(name, alias) for term in ["address", "addr", "situs", "street", "siteaddress"]),
                "is_parcel_candidate": any(term in _compact(name, alias) for term in ["parcel", "pin", "pin14", "propertyrealid", "account"]),
            }
        )
    return profiles


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
    if not profiles:
        profiles = _profiles_from_catalog_fields(layer_record)
    return [profile for profile in profiles if _field_name(profile)]


def profile_tax_parcel_fields(schema_name: str = "automap") -> dict[str, Any]:
    """Return verified field profiles for the trusted Tax Parcels layer."""
    layer = find_tax_parcel_layer()
    if not layer:
        return {"layer": None, "profiles": [], "warnings": ["No verified Tax Parcels layer is available."]}
    return {"layer": layer, "profiles": _profiles_for_layer(layer, schema_name), "warnings": []}


def _role_row(profile: dict[str, Any], role: str, score: float, notes: str) -> dict[str, Any]:
    return {
        "layer_key": profile.get("layer_key"),
        "field_role": role,
        "field_name": _field_name(profile),
        "field_alias": _field_alias(profile),
        "confidence_score": score,
        "notes": notes,
    }


def identify_pin14_fields(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        compact = _compact(_field_name(profile), _field_alias(profile))
        if "pin14" in compact:
            rows.append(_role_row(profile, "pin14", 0.98, "Field name or alias explicitly references PIN14."))
    return _dedupe_role_rows(rows)


def identify_pin_fields(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        name = _field_name(profile)
        alias = _field_alias(profile)
        compact = _compact(name, alias)
        blob = _text_blob(name, alias)
        if compact == "pin" or re.search(r"\bpin\b", blob):
            rows.append(_role_row(profile, "pin", 0.96, "Field name or alias explicitly references PIN."))
        elif "parcelidentificationnumber" in compact:
            rows.append(_role_row(profile, "pin", 0.9, "Field appears to reference parcel identification number."))
    return _dedupe_role_rows(rows)


def identify_parcel_id_fields(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        compact = _compact(_field_name(profile), _field_alias(profile))
        if profile.get("is_parcel_candidate") or any(term in compact for term in ["parcelid", "parcelnum", "parcelnumber", "propertyrealid", "account"]):
            rows.append(_role_row(profile, "parcel_id", 0.82, "Field was profiled as a parcel identifier candidate."))
    return _dedupe_role_rows(rows)


def identify_address_fields(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        compact = _compact(_field_name(profile), _field_alias(profile))
        if profile.get("is_address_candidate") or any(term in compact for term in ["address", "siteaddress", "situs", "streetaddr", "mailaddr"]):
            rows.append(_role_row(profile, "address", 0.76, "Field was profiled as an address candidate."))
    return _dedupe_role_rows(rows)


def identify_object_id_field(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        compact = _compact(_field_name(profile), _field_alias(profile))
        if profile.get("is_object_id") or compact in {"objectid", "objectid1", "fid", "oid"}:
            rows.append(_role_row(profile, "object_id", 0.99, "Object ID field identified from ArcGIS field type/profile."))
    return _dedupe_role_rows(rows)


def identify_geometry_support(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        compact = _compact(_field_name(profile), _field_alias(profile))
        if profile.get("is_geometry_field") or compact in {"shape", "geometry"}:
            rows.append(_role_row(profile, "geometry", 0.99, "Geometry field identified from ArcGIS field type/profile."))
    return _dedupe_role_rows(rows)


def _store_field_map(rows: list[dict[str, Any]], schema_name: str) -> int:
    ensure_parcel_field_map_table(schema_name)
    if not rows:
        return 0
    table = _qualified_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        for row in rows:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {table} (layer_key, field_role, field_name, field_alias, confidence_score, notes)
                    VALUES (:layer_key, :field_role, :field_name, :field_alias, :confidence_score, :notes)
                    ON CONFLICT (layer_key, field_role, field_name) DO UPDATE SET
                        field_alias = EXCLUDED.field_alias,
                        confidence_score = EXCLUDED.confidence_score,
                        notes = EXCLUDED.notes;
                    """
                ),
                row,
            )
    return len(rows)


def build_verified_parcel_field_map(schema_name: str = "automap") -> dict[str, Any]:
    """Build and store role mappings for the verified Tax Parcels layer."""
    profile = profile_tax_parcel_fields(schema_name)
    layer = profile.get("layer")
    profiles = profile.get("profiles") or []
    if not layer:
        return {
            "layer_key": None,
            "fields_by_role": {role: [] for role in PARCEL_FIELD_ROLES},
            "role_rows": [],
            "geometry_supported": False,
            "warnings": profile.get("warnings") or [],
            "stored_rows": 0,
        }

    role_rows = _dedupe_role_rows(
        [
            *identify_pin14_fields(profiles),
            *identify_pin_fields(profiles),
            *identify_parcel_id_fields(profiles),
            *identify_address_fields(profiles),
            *identify_object_id_field(profiles),
            *identify_geometry_support(profiles),
        ]
    )
    for row in role_rows:
        row["layer_key"] = layer.get("layer_key")
    stored = _store_field_map(role_rows, schema_name)
    fields_by_role: dict[str, list[str]] = {role: [] for role in PARCEL_FIELD_ROLES}
    for row in role_rows:
        fields_by_role.setdefault(row["field_role"], []).append(row["field_name"])
    return {
        "layer_key": layer.get("layer_key"),
        "layer_name": layer.get("layer_name"),
        "layer_url": layer.get("layer_url") or layer.get("rest_url"),
        "object_id_field": (fields_by_role.get("object_id") or [layer.get("object_id_field")])[0],
        "fields_by_role": fields_by_role,
        "role_rows": role_rows,
        "geometry_supported": bool(layer.get("geometry_type") or fields_by_role.get("geometry")),
        "warnings": profile.get("warnings") or [],
        "stored_rows": stored,
    }
