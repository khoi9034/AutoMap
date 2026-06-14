"""Field intelligence for verified AutoMap catalog layers."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from urllib.parse import urlencode

from sqlalchemy import bindparam, text

from app.arcgis_rest_inspector import ArcGISRestError, fetch_json, inspect_layer
from app.db import _quote_identifier, get_engine
from app.layer_catalog_store import load_catalog_records


FIELD_PROFILE_COLUMNS = {
    "layer_key": "text NOT NULL",
    "layer_url": "text NOT NULL",
    "field_name": "text NOT NULL",
    "field_type": "text",
    "field_alias": "text",
    "nullable": "boolean",
    "length": "integer",
    "domain": "jsonb",
    "is_object_id": "boolean DEFAULT false",
    "is_geometry_field": "boolean DEFAULT false",
    "is_date_candidate": "boolean DEFAULT false",
    "is_name_candidate": "boolean DEFAULT false",
    "is_category_candidate": "boolean DEFAULT false",
    "is_geography_candidate": "boolean DEFAULT false",
    "is_zoning_candidate": "boolean DEFAULT false",
    "is_permit_candidate": "boolean DEFAULT false",
    "is_status_candidate": "boolean DEFAULT false",
    "is_school_candidate": "boolean DEFAULT false",
    "is_address_candidate": "boolean DEFAULT false",
    "created_at": "timestamptz DEFAULT now()",
    "updated_at": "timestamptz DEFAULT now()",
}

VALUE_PROFILE_COLUMNS = {
    "layer_key": "text NOT NULL",
    "field_name": "text NOT NULL",
    "sample_values": "jsonb",
    "distinct_value_count": "integer",
    "sample_method": "text",
    "query_succeeded": "boolean DEFAULT false",
    "query_error": "text",
    "profiled_at": "timestamptz DEFAULT now()",
}

RECIPE_VALIDATION_COLUMNS = {
    "raw_prompt": "text",
    "map_title": "text",
    "recipe_json": "jsonb",
    "validation_json": "jsonb",
    "created_at": "timestamptz DEFAULT now()",
}

DATE_TERMS = {"date", "created", "updated", "issue", "permit", "activity", "year", "yr"}
NAME_TERMS = {"name", "label", "title", "description"}
GEOGRAPHY_TERMS = {"city", "municipality", "muni", "town", "jurisdiction", "district", "area", "name"}
ZONING_TERMS = {"zone", "zoning", "district", "code", "class"}
PARCEL_TERMS = {"parcel", "pin", "pin14", "account", "owner", "property"}
PERMIT_TERMS = {"permit", "case", "status", "type", "issue", "activity"}
STATUS_TERMS = {"status", "state", "phase", "active", "inactive"}
SCHOOL_TERMS = {"school", "elementary", "middle", "high", "district", "attendance"}
ADDRESS_TERMS = {"address", "addr", "street", "road", "site"}


def _qualified_table(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def ensure_field_intelligence_tables(schema_name: str = "automap") -> None:
    """Create or safely update v0.3 field intelligence tables."""
    schema = _quote_identifier(schema_name)
    field_table = _qualified_table(schema_name, "layer_field_profile")
    value_table = _qualified_table(schema_name, "layer_value_profile")
    validation_table = _qualified_table(schema_name, "recipe_validation_log")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {field_table} (
                    id serial PRIMARY KEY
                );
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {value_table} (
                    id serial PRIMARY KEY
                );
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {validation_table} (
                    id serial PRIMARY KEY
                );
                """
            )
        )
        for column, column_type in FIELD_PROFILE_COLUMNS.items():
            connection.execute(text(f"ALTER TABLE {field_table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        for column, column_type in VALUE_PROFILE_COLUMNS.items():
            connection.execute(text(f"ALTER TABLE {value_table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        for column, column_type in RECIPE_VALIDATION_COLUMNS.items():
            connection.execute(text(f"ALTER TABLE {validation_table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS layer_field_profile_layer_field_uidx
                ON {field_table} (layer_key, field_name);
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS layer_value_profile_layer_field_uidx
                ON {value_table} (layer_key, field_name);
                """
            )
        )


def _tokens(*values: Any) -> set[str]:
    text_value = " ".join(str(value or "") for value in values).lower()
    cleaned = "".join(char if char.isalnum() else " " for char in text_value)
    return {token for token in cleaned.split() if token}


def _has_any(tokens: set[str], terms: set[str]) -> bool:
    return bool(tokens.intersection(terms))


def infer_field_roles(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Infer candidate roles from ArcGIS field metadata."""
    profiles: list[dict[str, Any]] = []
    for field in fields:
        field_name = field.get("name") or ""
        field_type = field.get("type")
        field_alias = field.get("alias")
        tokens = _tokens(field_name, field_alias)
        lower_name = field_name.lower()
        is_object_id = field_type == "esriFieldTypeOID" or lower_name in {"objectid", "fid", "oid"}
        is_geometry = field_type == "esriFieldTypeGeometry" or lower_name in {"shape", "geometry"}
        is_date = field_type == "esriFieldTypeDate" or _has_any(tokens, DATE_TERMS)
        is_geography = _has_any(tokens, GEOGRAPHY_TERMS)
        is_zoning = _has_any(tokens, ZONING_TERMS)
        is_permit = _has_any(tokens, PERMIT_TERMS)
        is_school = _has_any(tokens, SCHOOL_TERMS)

        profiles.append(
            {
                "field_name": field_name,
                "field_type": field_type,
                "field_alias": field_alias,
                "nullable": field.get("nullable"),
                "length": field.get("length"),
                "domain": field.get("domain"),
                "is_object_id": is_object_id,
                "is_geometry_field": is_geometry,
                "is_date_candidate": is_date,
                "is_name_candidate": _has_any(tokens, NAME_TERMS),
                "is_category_candidate": _has_any(tokens, ZONING_TERMS | PERMIT_TERMS | SCHOOL_TERMS | STATUS_TERMS),
                "is_geography_candidate": is_geography,
                "is_zoning_candidate": is_zoning,
                "is_permit_candidate": is_permit,
                "is_status_candidate": _has_any(tokens, STATUS_TERMS),
                "is_school_candidate": is_school,
                "is_address_candidate": _has_any(tokens, ADDRESS_TERMS),
                "is_parcel_candidate": _has_any(tokens, PARCEL_TERMS),
            }
        )
    return profiles


def _fields_for_layer(layer_record: dict[str, Any]) -> list[dict[str, Any]]:
    fields = layer_record.get("fields") or []
    if isinstance(fields, list) and fields:
        return fields
    layer_url = layer_record.get("layer_url") or layer_record.get("rest_url")
    if not layer_url:
        return []
    try:
        inspected_fields = inspect_layer(layer_url).get("fields") or []
        return inspected_fields if isinstance(inspected_fields, list) else []
    except ArcGISRestError:
        return []


def _should_sample(profile: dict[str, Any]) -> bool:
    if profile["is_object_id"] or profile["is_geometry_field"]:
        return False
    return any(
        profile.get(flag)
        for flag in [
            "is_date_candidate",
            "is_name_candidate",
            "is_category_candidate",
            "is_geography_candidate",
            "is_zoning_candidate",
            "is_permit_candidate",
            "is_status_candidate",
            "is_school_candidate",
            "is_address_candidate",
            "is_parcel_candidate",
        ]
    )


def build_sample_query_url(
    layer_url: str,
    field_name: str,
    max_values: int = 50,
    distinct: bool = True,
) -> str:
    """Build a safe ArcGIS sample query URL with returnGeometry=false."""
    query = {
        "where": "1=1",
        "outFields": field_name,
        "returnGeometry": "false",
        "resultRecordCount": str(max_values),
        "f": "pjson",
    }
    if distinct:
        query["returnDistinctValues"] = "true"
        query["orderByFields"] = field_name
    return f"{layer_url.rstrip('/')}/query?{urlencode(query)}"


def _values_from_features(data: dict[str, Any], field_name: str, max_values: int) -> list[Any]:
    values: list[Any] = []
    seen: set[str] = set()
    for feature in data.get("features", []):
        attributes = feature.get("attributes", {}) if isinstance(feature, dict) else {}
        value = attributes.get(field_name)
        if value is None:
            continue
        key = json.dumps(value, sort_keys=True, default=str)
        if key in seen:
            continue
        seen.add(key)
        values.append(value)
        if len(values) >= max_values:
            break
    return values


def sample_candidate_field_values(layer_url: str, field_name: str, max_values: int = 50) -> dict[str, Any]:
    """Sample distinct field values without requesting feature geometry."""
    distinct_url = build_sample_query_url(layer_url, field_name, max_values, distinct=True)
    try:
        data = fetch_json(distinct_url)
        sample_values = _values_from_features(data, field_name, max_values)
        return {
            "field_name": field_name,
            "sample_values": sample_values,
            "distinct_value_count": len(sample_values),
            "sample_method": "returnDistinctValues",
            "query_succeeded": True,
            "query_error": None,
        }
    except ArcGISRestError as exc:
        first_error = str(exc)

    sample_url = build_sample_query_url(layer_url, field_name, max_values, distinct=False)
    try:
        data = fetch_json(sample_url)
        sample_values = _values_from_features(data, field_name, max_values)
        return {
            "field_name": field_name,
            "sample_values": sample_values,
            "distinct_value_count": len(sample_values),
            "sample_method": "small_sample",
            "query_succeeded": True,
            "query_error": None,
        }
    except ArcGISRestError as exc:
        return {
            "field_name": field_name,
            "sample_values": [],
            "distinct_value_count": None,
            "sample_method": "failed",
            "query_succeeded": False,
            "query_error": f"{first_error}; fallback failed: {exc}",
        }


def profile_layer_fields(layer_record: dict[str, Any]) -> dict[str, Any]:
    """Profile fields and candidate values for one layer catalog record."""
    layer_key = layer_record["layer_key"]
    layer_url = layer_record.get("layer_url") or layer_record.get("rest_url")
    fields = _fields_for_layer(layer_record)
    profiles = []
    for profile in infer_field_roles(fields):
        profile.update({"layer_key": layer_key, "layer_url": layer_url})
        profiles.append(profile)

    value_profiles = []
    for profile in profiles:
        if not layer_url or not _should_sample(profile):
            continue
        sample = sample_candidate_field_values(layer_url, profile["field_name"])
        sample.update({"layer_key": layer_key})
        value_profiles.append(sample)

    upsert_field_profiles(profiles)
    upsert_value_profiles(value_profiles)
    return {
        "layer_key": layer_key,
        "field_profiles": profiles,
        "value_profiles": value_profiles,
    }


def profile_catalog_fields(
    limit: int | None = None,
    categories: list[str] | None = None,
) -> dict[str, Any]:
    """Profile fields for active verified catalog layers."""
    records = [
        record
        for record in load_catalog_records()
        if record.get("is_verified") and record.get("is_active")
    ]
    if categories:
        category_set = set(categories)
        records = [record for record in records if record.get("category") in category_set]
    if limit is not None:
        records = records[:limit]

    layer_results = []
    for record in records:
        layer_results.append(profile_layer_fields(record))

    return {
        "layers_profiled": len(layer_results),
        "field_profiles": sum(len(result["field_profiles"]) for result in layer_results),
        "value_profiles": sum(len(result["value_profiles"]) for result in layer_results),
        "layer_keys": [result["layer_key"] for result in layer_results],
    }


def profile_selected_recipe_layers(recipe: dict[str, Any], catalog_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Profile fields for the layers selected in a recipe."""
    selected_keys = {layer["layer_key"] for layer in recipe.get("selected_layers", [])}
    if not selected_keys:
        return {"layers_profiled": 0, "field_profiles": 0, "value_profiles": 0, "layer_keys": []}
    records = catalog_records if catalog_records is not None else load_catalog_records()
    selected_records = [record for record in records if record.get("layer_key") in selected_keys]
    layer_results = [profile_layer_fields(record) for record in selected_records]
    return {
        "layers_profiled": len(layer_results),
        "field_profiles": sum(len(result["field_profiles"]) for result in layer_results),
        "value_profiles": sum(len(result["value_profiles"]) for result in layer_results),
        "layer_keys": [result["layer_key"] for result in layer_results],
    }


def upsert_field_profiles(profiles: list[dict[str, Any]], schema_name: str = "automap") -> int:
    """Upsert field role profiles into automap.layer_field_profile."""
    ensure_field_intelligence_tables(schema_name)
    if not profiles:
        return 0
    table = _qualified_table(schema_name, "layer_field_profile")
    columns = [column for column in FIELD_PROFILE_COLUMNS if column not in {"created_at", "updated_at"}]
    values = ", ".join("CAST(:domain AS jsonb)" if column == "domain" else f":{column}" for column in columns)
    updates = ", ".join(f"{column}=EXCLUDED.{column}" for column in columns if column not in {"layer_key", "field_name"})
    sql = text(
        f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({values})
        ON CONFLICT (layer_key, field_name) DO UPDATE SET
            {updates},
            updated_at = now();
        """
    )
    engine = get_engine()
    with engine.begin() as connection:
        for profile in profiles:
            params = {column: profile.get(column) for column in columns}
            params["domain"] = json.dumps(params.get("domain"))
            connection.execute(sql, params)
    return len(profiles)


def upsert_value_profiles(profiles: list[dict[str, Any]], schema_name: str = "automap") -> int:
    """Upsert sampled field values into automap.layer_value_profile."""
    ensure_field_intelligence_tables(schema_name)
    if not profiles:
        return 0
    table = _qualified_table(schema_name, "layer_value_profile")
    columns = [column for column in VALUE_PROFILE_COLUMNS if column != "profiled_at"]
    values = ", ".join("CAST(:sample_values AS jsonb)" if column == "sample_values" else f":{column}" for column in columns)
    updates = ", ".join(f"{column}=EXCLUDED.{column}" for column in columns if column not in {"layer_key", "field_name"})
    sql = text(
        f"""
        INSERT INTO {table} ({', '.join(columns)})
        VALUES ({values})
        ON CONFLICT (layer_key, field_name) DO UPDATE SET
            {updates},
            profiled_at = now();
        """
    )
    engine = get_engine()
    with engine.begin() as connection:
        for profile in profiles:
            params = {column: profile.get(column) for column in columns}
            params["sample_values"] = json.dumps(params.get("sample_values", []), default=str)
            connection.execute(sql, params)
    return len(profiles)


def load_field_profiles(layer_keys: list[str], schema_name: str = "automap") -> dict[str, list[dict[str, Any]]]:
    """Load field profiles grouped by layer_key."""
    ensure_field_intelligence_tables(schema_name)
    if not layer_keys:
        return {}
    table = _qualified_table(schema_name, "layer_field_profile")
    engine = get_engine()
    with engine.connect() as connection:
        sql = text(
                f"""
                SELECT *
                FROM {table}
                WHERE layer_key IN :layer_keys
                ORDER BY layer_key, field_name;
                """
            ).bindparams(bindparam("layer_keys", expanding=True))
        rows = connection.execute(
            sql,
            {"layer_keys": layer_keys},
        ).mappings()
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(row["layer_key"], []).append(dict(row))
        return grouped


def load_value_profiles(layer_keys: list[str], schema_name: str = "automap") -> dict[tuple[str, str], dict[str, Any]]:
    """Load sampled value profiles keyed by (layer_key, field_name)."""
    ensure_field_intelligence_tables(schema_name)
    if not layer_keys:
        return {}
    table = _qualified_table(schema_name, "layer_value_profile")
    engine = get_engine()
    with engine.connect() as connection:
        sql = text(
                f"""
                SELECT *
                FROM {table}
                WHERE layer_key IN :layer_keys;
                """
            ).bindparams(bindparam("layer_keys", expanding=True))
        rows = connection.execute(
            sql,
            {"layer_keys": layer_keys},
        ).mappings()
        return {(row["layer_key"], row["field_name"]): dict(row) for row in rows}


def log_recipe_validation(
    recipe: dict[str, Any],
    validation: dict[str, Any],
    schema_name: str = "automap",
) -> int:
    """Store a recipe validation snapshot for local review history."""
    ensure_field_intelligence_tables(schema_name)
    table = _qualified_table(schema_name, "recipe_validation_log")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (raw_prompt, map_title, recipe_json, validation_json, created_at)
                VALUES (:raw_prompt, :map_title, CAST(:recipe_json AS jsonb),
                        CAST(:validation_json AS jsonb), :created_at);
                """
            ),
            {
                "raw_prompt": recipe.get("user_intent"),
                "map_title": recipe.get("map_title"),
                "recipe_json": json.dumps(recipe, default=str),
                "validation_json": json.dumps(validation, default=str),
                "created_at": datetime.now(UTC),
            },
        )
    return 1
