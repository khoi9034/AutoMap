"""Local AutoMap request history stored in the AutoMap schema."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any

from sqlalchemy import text

from app.db import _quote_identifier, get_engine


REQUEST_HISTORY_COLUMNS = {
    "raw_prompt": "text",
    "workflow_step": "text",
    "map_title": "text",
    "status": "text",
    "packet_path": "text",
    "adjusted_packet_path": "text",
    "created_at": "timestamptz DEFAULT now()",
    "notes": "jsonb DEFAULT '{}'::jsonb",
}


def _qualified_table(schema_name: str, table_name: str = "request_history") -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def ensure_request_history_table(schema_name: str = "automap") -> None:
    """Create or safely update automap.request_history."""
    schema = _quote_identifier(schema_name)
    table = _qualified_table(schema_name)
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
        for column, column_type in REQUEST_HISTORY_COLUMNS.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS request_history_created_at_idx
                ON {table} (created_at DESC);
                """
            )
        )


def record_request_history(
    *,
    raw_prompt: str | None,
    workflow_step: str,
    map_title: str | None = None,
    status: str = "ok",
    packet_path: str | None = None,
    adjusted_packet_path: str | None = None,
    notes: dict[str, Any] | None = None,
    schema_name: str = "automap",
) -> int:
    """Insert one local request history row."""
    ensure_request_history_table(schema_name)
    table = _qualified_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    raw_prompt, workflow_step, map_title, status, packet_path,
                    adjusted_packet_path, created_at, notes
                )
                VALUES (
                    :raw_prompt, :workflow_step, :map_title, :status,
                    :packet_path, :adjusted_packet_path, :created_at,
                    CAST(:notes AS jsonb)
                );
                """
            ),
            {
                "raw_prompt": raw_prompt,
                "workflow_step": workflow_step,
                "map_title": map_title,
                "status": status,
                "packet_path": packet_path,
                "adjusted_packet_path": adjusted_packet_path,
                "created_at": datetime.now(UTC),
                "notes": json.dumps(notes or {}, default=str),
            },
        )
    return 1


def list_request_history(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """Return recent local request history rows."""
    ensure_request_history_table(schema_name)
    table = _qualified_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT id, raw_prompt, workflow_step, map_title, status,
                       packet_path, adjusted_packet_path, created_at, notes
                FROM {table}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return [dict(row) for row in rows]
