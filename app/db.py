"""PostGIS connection helpers for AutoMap."""

import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from app.config import Settings, database_host_kind, get_settings, require_database_url


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_identifier(identifier: str) -> str:
    """Safely quote a PostgreSQL identifier controlled by AutoMap settings."""
    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(
            "AUTOMAP_DB_SCHEMA must be a simple PostgreSQL identifier, such as "
            "'automap'."
        )
    return f'"{identifier}"'


def get_engine(settings: Settings | None = None) -> Engine:
    """Create a SQLAlchemy engine for AutoMap's own PostGIS database."""
    loaded_settings = settings or get_settings()
    database_url = require_database_url(loaded_settings)
    engine_kwargs = {"future": True, "pool_pre_ping": True}
    if database_host_kind(database_url) == "supabase_pooler":
        # Render/Supabase session pooler connections are capped tightly; avoid
        # holding idle SQLAlchemy pooled clients across short status/init calls.
        engine_kwargs["poolclass"] = NullPool
    return create_engine(database_url, **engine_kwargs)


def test_db_connection(settings: Settings | None = None) -> dict:
    """Connect to PostGIS, ensure the AutoMap schema exists, and report status."""
    loaded_settings = settings or get_settings()
    schema_name = loaded_settings.AUTOMAP_DB_SCHEMA
    quoted_schema = _quote_identifier(schema_name)
    engine = get_engine(loaded_settings)

    with engine.begin() as connection:
        database_name = connection.execute(text("SELECT current_database();")).scalar_one()
        host_kind = database_host_kind(loaded_settings.DATABASE_URL)
        if database_name == "cfs_dev":
            raise ValueError("Connected database is protected CFS database 'cfs_dev'.")
        if host_kind in {"supabase_direct", "supabase_pooler"} and database_name != "postgres":
            raise ValueError("Supabase AutoMap connections must resolve to database 'postgres'.")
        if host_kind == "local_dev" and database_name != "automap":
            raise ValueError("Local AutoMap connections must resolve to database 'automap'.")
        connection.execute(text("SELECT current_schema();")).scalar_one()
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis_topology;"))
        postgis_version = connection.execute(text("SELECT PostGIS_Version();")).scalar_one()

        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema};"))
        connection.execute(text(f"SET search_path TO {quoted_schema}, public;"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {quoted_schema}.project_database_check (
                    id serial PRIMARY KEY,
                    project_name text NOT NULL,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        connection.execute(
            text(
                f"""
                INSERT INTO {quoted_schema}.project_database_check (project_name)
                VALUES ('automaps')
                ON CONFLICT DO NOTHING;
                """
            )
        )
        active_schema = connection.execute(text("SELECT current_schema();")).scalar_one()

    return {
        "database_connected": True,
        "database_name": database_name,
        "database_host_kind": host_kind,
        "postgis_version": postgis_version,
        "automap_schema": active_schema,
        "health_check_table": f"{schema_name}.project_database_check",
        "message": (
            f"Connected to database '{database_name}' with AutoMap schema "
            f"'{active_schema}'."
        ),
    }
