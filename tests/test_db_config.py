import pytest

from app.config import (
    AUTOMAP_DEV_DATABASE,
    DEFAULT_AUTOMAP_SCHEMA,
    Settings,
    allowed_origins_from_settings,
    database_host_kind,
    get_settings,
    parse_allowed_origins,
    require_database_url,
    validate_settings,
)
from app.db import _quote_identifier


def test_get_settings_reads_database_environment(monkeypatch):
    database_url = (
        "postgresql+psycopg2://postgres:secret@localhost:5433/"
        f"{AUTOMAP_DEV_DATABASE}"
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("AUTOMAP_DB_SCHEMA", "automap")

    settings = get_settings(load_env_file=False)

    assert settings.DATABASE_URL == database_url
    assert settings.AUTOMAP_DB_SCHEMA == "automap"


def test_get_settings_defaults_schema(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOMAP_DB_SCHEMA", raising=False)

    settings = get_settings(load_env_file=False)

    assert settings.DATABASE_URL is None
    assert settings.AUTOMAP_DB_SCHEMA == DEFAULT_AUTOMAP_SCHEMA


def test_require_database_url_raises_helpful_error_when_missing():
    settings = Settings(DATABASE_URL=None)

    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        require_database_url(settings)


def test_validate_settings_rejects_protected_cfs_database():
    settings = Settings(
        DATABASE_URL="postgresql+psycopg2://postgres:secret@localhost:5433/cfs_dev"
    )

    with pytest.raises(ValueError, match="protected CFS database"):
        validate_settings(settings)


def test_validate_settings_rejects_non_automap_database():
    settings = Settings(
        DATABASE_URL="postgresql+psycopg2://postgres:secret@localhost:5433/other_db"
    )

    with pytest.raises(ValueError, match="automap"):
        validate_settings(settings)


def test_validate_settings_rejects_nonlocal_automap_database():
    settings = Settings(
        DATABASE_URL="postgresql+psycopg2://postgres:secret@example.com:5432/automap"
    )

    with pytest.raises(ValueError, match="approved Supabase Session Pooler"):
        validate_settings(settings)


def test_validate_settings_allows_supabase_direct_postgres_database():
    settings = Settings(
        DATABASE_URL=(
            "postgresql+psycopg2://postgres:real-password"
            "@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres"
        )
    )

    validate_settings(settings)


def test_validate_settings_allows_supabase_session_pooler_database():
    for port in (5432, 6543):
        settings = Settings(
            DATABASE_URL=(
                "postgresql+psycopg2://postgres.mjfbpmatxvjczikqbuva:real-password"
                f"@aws-0-us-east-1.pooler.supabase.com:{port}/postgres"
            )
        )

        validate_settings(settings)
        assert database_host_kind(settings.DATABASE_URL) == "supabase_pooler"


def test_validate_settings_rejects_wrong_supabase_project_pooler_database():
    settings = Settings(
        DATABASE_URL=(
            "postgresql+psycopg2://postgres.wrongprojectref:real-password"
            "@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        )
    )

    with pytest.raises(ValueError, match="mjfbpmatxvjczikqbuva"):
        validate_settings(settings)


def test_validate_settings_rejects_random_postgres_host():
    settings = Settings(
        DATABASE_URL="postgresql+psycopg2://postgres:real-password@db.example.com:5432/postgres"
    )

    with pytest.raises(ValueError, match="approved Supabase"):
        validate_settings(settings)


def test_database_host_kind_classifies_allowed_targets():
    assert (
        database_host_kind("postgresql+psycopg2://postgres:secret@localhost:5433/automap")
        == "local_dev"
    )
    assert (
        database_host_kind(
            "postgresql+psycopg2://postgres:secret@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres"
        )
        == "supabase_direct"
    )
    assert (
        database_host_kind(
            "postgresql+psycopg2://postgres.mjfbpmatxvjczikqbuva:secret@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        )
        == "supabase_pooler"
    )
    assert database_host_kind("postgresql+psycopg2://postgres:secret@db.example.com:5432/postgres") == "unknown"


def test_validate_settings_rejects_placeholder_password():
    settings = Settings(
        DATABASE_URL=(
            "postgresql+psycopg2://postgres:YOUR_LOCAL_POSTGRES_PASSWORD"
            "@localhost:5433/automap"
        )
    )

    with pytest.raises(ValueError, match="placeholder password"):
        validate_settings(settings)


def test_validate_settings_rejects_supabase_placeholder_password():
    settings = Settings(
        DATABASE_URL=(
            "postgresql+psycopg2://postgres:YOUR_SUPABASE_DB_PASSWORD"
            "@db.mjfbpmatxvjczikqbuva.supabase.co:5432/postgres"
        )
    )

    with pytest.raises(ValueError, match="placeholder password"):
        validate_settings(settings)


def test_allowed_origins_parse_local_and_deployed_frontend():
    settings = Settings(
        DATABASE_URL=None,
        ALLOWED_ORIGINS="[http://localhost:3010,https://auto-map-cyan.vercel.app]",
        FRONTEND_ORIGIN="https://auto-map-cyan.vercel.app",
    )

    assert parse_allowed_origins(settings.ALLOWED_ORIGINS) == [
        "http://localhost:3010",
        "https://auto-map-cyan.vercel.app",
    ]
    assert allowed_origins_from_settings(settings).count("https://auto-map-cyan.vercel.app") == 1


def test_quote_identifier_accepts_simple_schema_name():
    assert _quote_identifier("automap") == '"automap"'


def test_quote_identifier_rejects_unsafe_schema_name():
    with pytest.raises(ValueError, match="simple PostgreSQL identifier"):
        _quote_identifier("automap;drop schema public")
