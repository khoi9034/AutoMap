"""PostGIS storage for AutoMap's inspected layer catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.arcgis_rest_inspector import try_layer_count, verify_layer_exists
from app.db import _quote_identifier, get_engine
from app.layer_semantics import sort_layer_candidates


PRESERVED_COLUMNS = {
    "layer_key": "text",
    "layer_name": "text",
    "rest_url": "text",
    "category": "text",
    "aliases": "jsonb",
    "description": "text",
    "geometry_type": "text",
    "date_fields": "jsonb",
    "common_filters": "jsonb",
    "planning_use_cases": "jsonb",
    "recommended_symbology": "jsonb",
    "known_limitations": "text",
    "is_public": "boolean DEFAULT true",
    "is_active": "boolean DEFAULT true",
    "created_at": "timestamptz DEFAULT now()",
    "updated_at": "timestamptz DEFAULT now()",
}

REST_COLUMNS = {
    "source_key": "text",
    "source_priority": "integer",
    "source_status": "text",
    "service_name": "text",
    "service_url": "text",
    "layer_id": "integer",
    "layer_url": "text",
    "layer_type": "text",
    "parent_layer_id": "integer",
    "sublayer_ids": "jsonb",
    "is_group_layer": "boolean DEFAULT false",
    "is_feature_layer": "boolean DEFAULT false",
    "spatial_reference": "jsonb",
    "extent": "jsonb",
    "supported_query_formats": "jsonb",
    "capabilities": "jsonb",
    "max_record_count": "integer",
    "object_id_field": "text",
    "display_field": "text",
    "type_id_field": "text",
    "fields": "jsonb",
    "drawing_info": "jsonb",
    "service_item_id": "text",
    "record_count": "integer",
    "is_verified": "boolean DEFAULT false",
    "verification_status": "text",
    "verification_error": "text",
    "verified_at": "timestamptz",
    "is_historical": "boolean DEFAULT false",
    "historical_year": "integer",
    "canonical_topic": "text",
    "superseded_by_layer_key": "text",
    "source_notes": "text",
}

JSON_COLUMNS = {
    "aliases",
    "date_fields",
    "common_filters",
    "planning_use_cases",
    "recommended_symbology",
    "sublayer_ids",
    "spatial_reference",
    "extent",
    "supported_query_formats",
    "capabilities",
    "fields",
    "drawing_info",
}

INSERT_COLUMNS = [
    column
    for column in [*PRESERVED_COLUMNS.keys(), *REST_COLUMNS.keys()]
    if column not in {"created_at", "updated_at"}
]


def _json_value(value: Any) -> str:
    return json.dumps(value)


def _prepare_record(record: dict[str, Any]) -> dict[str, Any]:
    prepared: dict[str, Any] = {}
    for column in INSERT_COLUMNS:
        value = record.get(column)
        prepared[column] = _json_value(value) if column in JSON_COLUMNS else value
    return prepared


def _table_name(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.layer_catalog"


def ensure_layer_catalog_table(schema_name: str = "automap") -> None:
    """Create or safely alter automap.layer_catalog for REST metadata."""
    table_name = _table_name(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id serial PRIMARY KEY,
                    layer_key text NOT NULL,
                    layer_name text NOT NULL,
                    rest_url text,
                    category text,
                    aliases jsonb DEFAULT '[]'::jsonb,
                    description text,
                    geometry_type text,
                    date_fields jsonb DEFAULT '[]'::jsonb,
                    common_filters jsonb DEFAULT '[]'::jsonb,
                    planning_use_cases jsonb DEFAULT '[]'::jsonb,
                    recommended_symbology jsonb DEFAULT '{{}}'::jsonb,
                    known_limitations text,
                    is_public boolean DEFAULT true,
                    is_active boolean DEFAULT true,
                    created_at timestamptz DEFAULT now(),
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )

        for column, column_type in {**PRESERVED_COLUMNS, **REST_COLUMNS}.items():
            connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column} {column_type};"))

        connection.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS layer_catalog_layer_key_uidx
                ON {table_name} (layer_key);
                """
            )
        )


def upsert_layer_records(records: list[dict[str, Any]], schema_name: str = "automap") -> int:
    """Upsert inspected layer records by stable layer_key."""
    if not records:
        ensure_layer_catalog_table(schema_name)
        return 0

    ensure_layer_catalog_table(schema_name)
    table_name = _table_name(schema_name)
    columns_sql = ", ".join(INSERT_COLUMNS)
    values_sql_parts = []
    for column in INSERT_COLUMNS:
        if column in JSON_COLUMNS:
            values_sql_parts.append(f"CAST(:{column} AS jsonb)")
        else:
            values_sql_parts.append(f":{column}")
    values_sql = ", ".join(values_sql_parts)
    update_sql = ", ".join(
        f"{column} = EXCLUDED.{column}"
        for column in INSERT_COLUMNS
        if column != "layer_key"
    )

    sql = text(
        f"""
        INSERT INTO {table_name} ({columns_sql})
        VALUES ({values_sql})
        ON CONFLICT (layer_key) DO UPDATE SET
            {update_sql},
            updated_at = now();
        """
    )

    engine = get_engine()
    with engine.begin() as connection:
        for record in records:
            connection.execute(sql, _prepare_record(record))
    return len(records)


def list_layers(schema_name: str = "automap", limit: int = 500) -> list[dict[str, Any]]:
    """Return catalog layer rows for CLI display."""
    ensure_layer_catalog_table(schema_name)
    table_name = _table_name(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT layer_key, layer_name, category, source_status, source_priority,
                       layer_url, is_verified, is_historical
                FROM {table_name}
                ORDER BY source_priority NULLS LAST, source_status, service_name, layer_id
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return [dict(row) for row in rows]


def search_layers(query: str, schema_name: str = "automap", limit: int = 25) -> list[dict[str, Any]]:
    """Search catalog rows and prefer active verified new OpenData layers."""
    ensure_layer_catalog_table(schema_name)
    table_name = _table_name(schema_name)
    pattern = f"%{query}%"
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT layer_key, layer_name, service_name, category, aliases, description,
                       planning_use_cases, source_status, source_priority, layer_url,
                       is_verified, is_historical, record_count
                FROM {table_name}
                WHERE is_active = true
                  AND (
                    layer_name ILIKE :pattern
                    OR service_name ILIKE :pattern
                    OR category ILIKE :pattern
                    OR description ILIKE :pattern
                    OR CAST(aliases AS text) ILIKE :pattern
                    OR CAST(planning_use_cases AS text) ILIKE :pattern
                  )
                LIMIT 200;
                """
            ),
            {"pattern": pattern},
        ).mappings()
        records = [dict(row) for row in rows]
    return sort_layer_candidates(records)[:limit]


def verify_catalog_layers(schema_name: str = "automap") -> dict[str, Any]:
    """Re-check every catalog layer_url and update verification fields."""
    ensure_layer_catalog_table(schema_name)
    table_name = _table_name(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(text(f"SELECT layer_key, layer_url FROM {table_name};")).mappings()
        layer_urls = [dict(row) for row in rows]

    failed: list[dict[str, Any]] = []
    verified_count = 0
    with engine.begin() as connection:
        for row in layer_urls:
            verification = verify_layer_exists(row["layer_url"])
            count_result = try_layer_count(row["layer_url"])
            if verification["is_verified"]:
                verified_count += 1
            else:
                failed.append({"layer_key": row["layer_key"], "layer_url": row["layer_url"], "error": verification["verification_error"]})

            connection.execute(
                text(
                    f"""
                    UPDATE {table_name}
                    SET is_verified = :is_verified,
                        verification_status = :verification_status,
                        verification_error = :verification_error,
                        verified_at = :verified_at,
                        record_count = :record_count,
                        known_limitations = COALESCE(:count_error, known_limitations),
                        updated_at = now()
                    WHERE layer_key = :layer_key;
                    """
                ),
                {
                    "layer_key": row["layer_key"],
                    "is_verified": verification["is_verified"],
                    "verification_status": verification["verification_status"],
                    "verification_error": verification["verification_error"],
                    "verified_at": verification["verified_at"],
                    "record_count": count_result["record_count"],
                    "count_error": count_result["count_error"],
                },
            )

    return {"checked": len(layer_urls), "verified": verified_count, "failed": failed}


def export_layer_catalog_json(path: Path | str = "outputs/layer_catalog_export.json", schema_name: str = "automap") -> Path:
    """Export catalog metadata to JSON without secrets."""
    ensure_layer_catalog_table(schema_name)
    export_path = Path(path)
    export_path.parent.mkdir(parents=True, exist_ok=True)
    table_name = _table_name(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT layer_key, layer_name, category, aliases, description,
                       geometry_type, source_key, source_priority, source_status,
                       service_name, service_url, layer_id, layer_url, layer_type,
                       is_group_layer, is_feature_layer, spatial_reference, extent,
                       supported_query_formats, capabilities, max_record_count,
                       object_id_field, display_field, type_id_field, service_item_id,
                       record_count, is_verified, verification_status, is_historical,
                       historical_year, canonical_topic, superseded_by_layer_key,
                       source_notes
                FROM {table_name}
                ORDER BY source_priority NULLS LAST, service_name, layer_id;
                """
            )
        ).mappings()
        data = [dict(row) for row in rows]
    export_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    return export_path
