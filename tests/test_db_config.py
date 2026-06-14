import pytest

from app.config import DEFAULT_AUTOMAP_SCHEMA, Settings, get_settings, require_database_url
from app.db import _quote_identifier


def test_get_settings_reads_database_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost/db")
    monkeypatch.setenv("AUTOMAP_DB_SCHEMA", "automap_test")

    settings = get_settings()

    assert settings.DATABASE_URL == "postgresql+psycopg2://user:pass@localhost/db"
    assert settings.AUTOMAP_DB_SCHEMA == "automap_test"


def test_get_settings_defaults_schema(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("AUTOMAP_DB_SCHEMA", raising=False)

    settings = get_settings()

    assert settings.DATABASE_URL is None
    assert settings.AUTOMAP_DB_SCHEMA == DEFAULT_AUTOMAP_SCHEMA


def test_require_database_url_raises_helpful_error_when_missing():
    settings = Settings(DATABASE_URL=None)

    with pytest.raises(ValueError, match="DATABASE_URL is not configured"):
        require_database_url(settings)


def test_quote_identifier_accepts_simple_schema_name():
    assert _quote_identifier("automap") == '"automap"'


def test_quote_identifier_rejects_unsafe_schema_name():
    with pytest.raises(ValueError, match="simple PostgreSQL identifier"):
        _quote_identifier("automap;drop schema public")
