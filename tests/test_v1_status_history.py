import subprocess
import sys
from uuid import uuid4

import pytest

from app.config import get_settings
from app.request_history import list_request_history, record_request_history
from app.system_status import format_system_status, get_system_status
from app.version import AUTOMAP_VERSION


def require_database_url():
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("AutoMap DATABASE_URL is not configured.")


def test_request_history_insert_works():
    require_database_url()
    prompt = f"pytest history prompt {uuid4()}"

    inserted = record_request_history(
        raw_prompt=prompt,
        workflow_step="recipe",
        map_title="Pytest History",
        status="created",
        notes={"source": "pytest"},
    )
    rows = list_request_history(limit=20)

    assert inserted == 1
    assert any(row["raw_prompt"] == prompt for row in rows)


def test_system_status_command_works():
    result = subprocess.run(
        [sys.executable, "-m", "app.main", "--system-status"],
        capture_output=True,
        text=True,
        check=True,
    )

    assert f"AutoMap version: {AUTOMAP_VERSION}" in result.stdout
    assert "ArcGIS publisher mode:" in result.stdout
    assert "real publish enabled=" in result.stdout
    assert "DB connected:" in result.stdout


def test_system_status_output_has_no_cfs_database_name_or_secrets():
    output = format_system_status(get_system_status()).lower()

    assert "cfs_dev" not in output
    assert "database_url" not in output
    assert "arcgis_password" not in output
    assert ".env" not in output
