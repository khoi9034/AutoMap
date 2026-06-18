"""Persistence helpers for exact Map Composer map state."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from app.db import _quote_identifier, get_engine


def init_composer_map_state_table(schema_name: str = "automap") -> None:
    """Create the additive composer map state table in AutoMap's schema."""
    quoted_schema = _quote_identifier(schema_name)
    table = f"{quoted_schema}.composer_map_states"
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY,
                    composer_session_id text UNIQUE,
                    map_state_json jsonb,
                    created_at timestamptz DEFAULT now(),
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )


def upsert_composer_map_state(
    composer_session_id: str,
    map_state: dict[str, Any],
    schema_name: str = "automap",
) -> None:
    """Insert or update a saved composer map state."""
    init_composer_map_state_table(schema_name)
    quoted_schema = _quote_identifier(schema_name)
    table = f"{quoted_schema}.composer_map_states"
    payload = json.dumps(map_state, default=str)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (composer_session_id, map_state_json)
                VALUES (:composer_session_id, CAST(:map_state_json AS jsonb))
                ON CONFLICT (composer_session_id)
                DO UPDATE SET
                    map_state_json = EXCLUDED.map_state_json,
                    updated_at = now();
                """
            ),
            {"composer_session_id": composer_session_id, "map_state_json": payload},
        )


def get_composer_map_state(composer_session_id: str, schema_name: str = "automap") -> dict[str, Any] | None:
    """Load a composer map state from AutoMap's database when available."""
    init_composer_map_state_table(schema_name)
    quoted_schema = _quote_identifier(schema_name)
    table = f"{quoted_schema}.composer_map_states"
    engine = get_engine()
    with engine.begin() as connection:
        row = connection.execute(
            text(f"SELECT map_state_json FROM {table} WHERE composer_session_id = :composer_session_id"),
            {"composer_session_id": composer_session_id},
        ).first()
    if not row:
        return None
    value = row[0]
    if isinstance(value, str):
        return json.loads(value)
    if isinstance(value, dict):
        return value
    return None
