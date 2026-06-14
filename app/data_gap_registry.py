"""Data gap registry for missing AutoMap layer needs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.db import _quote_identifier, get_engine
from app.layer_semantics import slugify


DATA_GAP_COLUMNS = {
    "gap_key": "text UNIQUE",
    "topic": "text NOT NULL",
    "requested_by_prompt": "text",
    "missing_layer_type": "text",
    "reason": "text",
    "suggested_source": "text",
    "status": "text DEFAULT 'open'",
    "created_at": "timestamptz DEFAULT now()",
    "updated_at": "timestamptz DEFAULT now()",
}

KNOWN_GAPS = {
    "permits": {
        "gap_key": "current_permits",
        "topic": "permits",
        "missing_layer_type": "current permit layer",
        "reason": "Current permit layer is not available in the verified AutoMap layer catalog.",
        "suggested_source": "Cabarrus County permitting or development services source.",
    },
    "planning cases": {
        "gap_key": "current_planning_cases",
        "topic": "planning cases",
        "missing_layer_type": "current planning case layer",
        "reason": "Current planning case layer is not available in the verified AutoMap layer catalog.",
        "suggested_source": "Cabarrus County planning case or development pipeline source.",
    },
    "development": {
        "gap_key": "current_development_pipeline",
        "topic": "development",
        "missing_layer_type": "current development activity layer",
        "reason": "Current development activity layer is not available in the verified AutoMap layer catalog.",
        "suggested_source": "County development pipeline, permit, or planning case service.",
    },
    "subdivision activity": {
        "gap_key": "subdivision_activity",
        "topic": "subdivision activity",
        "missing_layer_type": "subdivision activity layer",
        "reason": "Subdivision activity layer is not available in the verified AutoMap layer catalog.",
        "suggested_source": "County planning or land development source.",
    },
}


def _qualified_table(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def ensure_data_gap_registry_table(schema_name: str = "automap") -> None:
    """Create or safely update automap.data_gap_registry."""
    schema = _quote_identifier(schema_name)
    table = _qualified_table(schema_name, "data_gap_registry")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY
                );
                """
            )
        )
        for column, column_type in DATA_GAP_COLUMNS.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS data_gap_registry_gap_key_uidx
                ON {table} (gap_key);
                """
            )
        )


def _gap_record(topic: str, prompt: str) -> dict[str, Any]:
    known = KNOWN_GAPS.get(topic)
    if known:
        return {**known, "requested_by_prompt": prompt, "status": "open"}
    return {
        "gap_key": f"missing_{slugify(topic)}",
        "topic": topic,
        "requested_by_prompt": prompt,
        "missing_layer_type": f"{topic} layer",
        "reason": f"{topic} was requested but no suitable verified catalog layer was selected.",
        "suggested_source": None,
        "status": "open",
    }


def data_gap_records_from_recipe(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    """Return data gap records implied by a recipe without writing them."""
    prompt = recipe.get("user_intent", "")
    return [_gap_record(topic, prompt) for topic in recipe.get("missing_data_needed") or []]


def upsert_data_gaps_from_recipe(recipe: dict[str, Any], schema_name: str = "automap") -> int:
    """Upsert data gap records for recipe missing_data_needed entries."""
    gaps = recipe.get("missing_data_needed") or []
    if not gaps:
        ensure_data_gap_registry_table(schema_name)
        return 0

    ensure_data_gap_registry_table(schema_name)
    table = _qualified_table(schema_name, "data_gap_registry")
    sql = text(
        f"""
        INSERT INTO {table} (
            gap_key, topic, requested_by_prompt, missing_layer_type, reason,
            suggested_source, status, created_at, updated_at
        )
        VALUES (
            :gap_key, :topic, :requested_by_prompt, :missing_layer_type, :reason,
            :suggested_source, :status, :created_at, :updated_at
        )
        ON CONFLICT (gap_key) DO UPDATE SET
            requested_by_prompt = EXCLUDED.requested_by_prompt,
            missing_layer_type = EXCLUDED.missing_layer_type,
            reason = EXCLUDED.reason,
            suggested_source = EXCLUDED.suggested_source,
            status = EXCLUDED.status,
            updated_at = now();
        """
    )
    engine = get_engine()
    now = datetime.now(UTC)
    with engine.begin() as connection:
        for record in data_gap_records_from_recipe(recipe):
            record.update({"created_at": now, "updated_at": now})
            connection.execute(sql, record)
    return len(gaps)


def list_data_gaps(schema_name: str = "automap") -> list[dict[str, Any]]:
    """List current data gaps."""
    ensure_data_gap_registry_table(schema_name)
    table = _qualified_table(schema_name, "data_gap_registry")
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT gap_key, topic, missing_layer_type, reason, suggested_source,
                       status, requested_by_prompt, updated_at
                FROM {table}
                ORDER BY status, topic, gap_key;
                """
            )
        ).mappings()
        return [dict(row) for row in rows]
