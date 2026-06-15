"""Sanitized AutoMap v1 local system status."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.data_gap_registry import ensure_data_gap_registry_table
from app.db import _quote_identifier, get_engine, test_db_connection
from app.field_profiler import ensure_field_intelligence_tables
from app.layer_catalog_store import ensure_layer_catalog_table
from app.packet_index import list_adjusted_packets, list_approved_packets, list_review_packets
from app.approval_engine import ensure_review_approval_history_table
from app.request_history import ensure_request_history_table
from app.version import AUTOMAP_VERSION


def _qualified(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def _scalar_count(connection: Any, sql: str, params: dict[str, Any] | None = None) -> int:
    return int(connection.execute(text(sql), params or {}).scalar_one() or 0)


def get_system_status(schema_name: str | None = None) -> dict[str, Any]:
    """Return sanitized local status for UI and CLI display."""
    settings = get_settings()
    schema = schema_name or settings.AUTOMAP_DB_SCHEMA
    status: dict[str, Any] = {
        "version": AUTOMAP_VERSION,
        "database_connected": False,
        "database_name": None,
        "automap_schema": schema,
        "postgis_version": None,
        "catalog": {
            "layer_count": 0,
            "verified_layer_count": 0,
            "new_opendata_layer_count": 0,
            "legacy_layer_count": 0,
            "historical_layer_count": 0,
        },
        "profiles": {
            "field_profile_count": 0,
            "value_profile_count": 0,
        },
        "data_gap_count": 0,
        "request_history_count": 0,
        "approval_history_count": 0,
        "packets": {
            "review_packet_count": len(list_review_packets()),
            "adjusted_packet_count": len(list_adjusted_packets()),
            "approved_packet_count": len(list_approved_packets()),
        },
        "arcgis_publisher_mode": "dry-run by default",
        "protected_database_status": "external project database was not accessed",
        "errors": [],
    }

    try:
        db_status = test_db_connection(settings)
        status.update(
            {
                "database_connected": bool(db_status.get("database_connected")),
                "database_name": db_status.get("database_name"),
                "automap_schema": db_status.get("automap_schema") or schema,
                "postgis_version": db_status.get("postgis_version"),
            }
        )
        ensure_layer_catalog_table(schema)
        ensure_field_intelligence_tables(schema)
        ensure_data_gap_registry_table(schema)
        ensure_request_history_table(schema)
        ensure_review_approval_history_table(schema)
        engine = get_engine(settings)
        with engine.connect() as connection:
            catalog_table = _qualified(schema, "layer_catalog")
            field_table = _qualified(schema, "layer_field_profile")
            value_table = _qualified(schema, "layer_value_profile")
            gaps_table = _qualified(schema, "data_gap_registry")
            history_table = _qualified(schema, "request_history")
            approval_table = _qualified(schema, "review_approval_history")
            status["catalog"] = {
                "layer_count": _scalar_count(connection, f"SELECT count(*) FROM {catalog_table};"),
                "verified_layer_count": _scalar_count(connection, f"SELECT count(*) FROM {catalog_table} WHERE is_verified = true;"),
                "new_opendata_layer_count": _scalar_count(
                    connection,
                    f"""
                    SELECT count(*)
                    FROM {catalog_table}
                    WHERE source_priority = 1
                       OR source_key = 'cabarrus_new_opendata';
                    """,
                ),
                "legacy_layer_count": _scalar_count(
                    connection,
                    f"""
                    SELECT count(*)
                    FROM {catalog_table}
                    WHERE COALESCE(source_status, '') LIKE 'legacy%';
                    """,
                ),
                "historical_layer_count": _scalar_count(
                    connection,
                    f"""
                    SELECT count(*)
                    FROM {catalog_table}
                    WHERE is_historical = true
                       OR COALESCE(source_status, '') = 'legacy_historical';
                    """,
                ),
            }
            status["profiles"] = {
                "field_profile_count": _scalar_count(connection, f"SELECT count(*) FROM {field_table};"),
                "value_profile_count": _scalar_count(connection, f"SELECT count(*) FROM {value_table};"),
            }
            status["data_gap_count"] = _scalar_count(connection, f"SELECT count(*) FROM {gaps_table};")
            status["request_history_count"] = _scalar_count(connection, f"SELECT count(*) FROM {history_table};")
            status["approval_history_count"] = _scalar_count(connection, f"SELECT count(*) FROM {approval_table};")
    except (SQLAlchemyError, ValueError) as exc:
        status["errors"].append(str(exc))

    return status


def format_system_status(status: dict[str, Any]) -> str:
    """Format sanitized status for the CLI."""
    catalog = status["catalog"]
    profiles = status["profiles"]
    packets = status["packets"]
    lines = [
        f"AutoMap version: {status['version']}",
        f"DB connected: {status['database_connected']}",
        f"Database name: {status.get('database_name') or 'unavailable'}",
        f"AutoMap schema: {status.get('automap_schema') or 'unavailable'}",
        f"PostGIS version: {status.get('postgis_version') or 'unavailable'}",
        f"Layer catalog records: {catalog['layer_count']}",
        f"Verified layers: {catalog['verified_layer_count']}",
        f"New OpenData layers: {catalog['new_opendata_layer_count']}",
        f"Legacy layers: {catalog['legacy_layer_count']}",
        f"Historical layers: {catalog['historical_layer_count']}",
        f"Field profiles: {profiles['field_profile_count']}",
        f"Value profiles: {profiles['value_profile_count']}",
        f"Data gaps: {status['data_gap_count']}",
        f"Request history rows: {status['request_history_count']}",
        f"Approval history rows: {status['approval_history_count']}",
        f"Review packets: {packets['review_packet_count']}",
        f"Adjusted packets: {packets['adjusted_packet_count']}",
        f"Approved packets: {packets['approved_packet_count']}",
        f"ArcGIS publisher mode: {status['arcgis_publisher_mode']}",
        f"Protected database reminder: {status['protected_database_status']}",
    ]
    if status["errors"]:
        lines.append("Errors:")
        lines.extend(f"- {error}" for error in status["errors"])
    return "\n".join(lines)
