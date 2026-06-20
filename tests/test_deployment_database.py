import pytest

from app.config import Settings
from app.deployment_database import deployment_init_db
from app.main import _deployment_init_db


def test_deployment_init_refuses_cfs_dev_before_connecting():
    settings = Settings(DATABASE_URL="postgresql+psycopg2://postgres:secret@localhost:5433/cfs_dev")

    with pytest.raises(ValueError, match="protected CFS database"):
        deployment_init_db(settings=settings, initializers=[])


def test_deployment_init_cli_does_not_print_database_password(monkeypatch, capsys):
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:FAKE_PASSWORD_FOR_TEST@localhost:5433/cfs_dev",
    )
    monkeypatch.setenv("AUTOMAP_DB_SCHEMA", "automap")

    status = _deployment_init_db()
    output = capsys.readouterr().out.lower()

    assert status == 1
    assert "protected cfs database" in output
    assert "fake_password_for_test" not in output
    assert "database_url" not in output
