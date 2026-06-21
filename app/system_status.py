"""Sanitized AutoMap v1 local system status."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import database_host_kind, get_settings
from app.arcgis_publisher import load_arcgis_publish_settings
from app.db import _quote_identifier, get_engine, test_db_connection
from app.packet_index import list_adjusted_packets, list_approved_packets, list_review_packets
from app.ports import (
    AUTOMAP_BACKEND_PORT,
    AUTOMAP_FRONTEND_PORT,
    CFS_RESERVED_BACKEND_PORT,
    CFS_RESERVED_FRONTEND_PORT,
)
from app.version import AUTOMAP_VERSION


def _qualified(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def _scalar_count(connection: Any, sql: str, params: dict[str, Any] | None = None) -> int:
    return int(connection.execute(text(sql), params or {}).scalar_one() or 0)


def categorize_database_error(exc: BaseException) -> str:
    """Map database exceptions to safe categories without leaking connection strings."""
    message = str(exc).lower()
    if "timeout" in message or "statement timeout" in message or "canceling statement" in message:
        return "timeout"
    if "password authentication failed" in message or "authentication failed" in message:
        return "auth_failed"
    if "network is unreachable" in message or "could not translate host" in message or "connection refused" in message:
        return "network_unreachable"
    if "emaxconnsession" in message or "max clients" in message or "pool_size" in message:
        return "pool_exhausted"
    if "ssl" in message:
        return "ssl_required"
    if "configured database" in message or "protected cfs database" in message or "must resolve to database" in message:
        return "database_rejected"
    return "unknown"


def _publisher_status(status: dict[str, Any]) -> None:
    status.setdefault("errors", [])
    try:
        publish_settings = load_arcgis_publish_settings()
        status["arcgis_publish_profile"] = publish_settings.publish_env
        status["real_publish_enabled"] = publish_settings.allow_real_publish and not publish_settings.dry_run
        status["arcgis_publisher_mode"] = (
            f"dry-run default={publish_settings.dry_run}; profile={publish_settings.publish_env}; "
            f"real publish enabled={status['real_publish_enabled']}"
        )
    except ValueError as exc:
        status["errors"].append(f"publisher_config:{categorize_database_error(exc)}")


def _base_status(schema: str, database_url: str | None) -> dict[str, Any]:
    return {
        "version": AUTOMAP_VERSION,
        "database_connected": False,
        "database_name": None,
        "database_host_kind": database_host_kind(database_url),
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
        "external_source_count": 0,
        "request_history_count": 0,
        "approval_history_count": 0,
        "analysis_run_count": 0,
        "analysis_refinement_count": 0,
        "analysis_report_count": 0,
        "planning_scenario_count": 0,
        "scenario_variant_count": 0,
        "scenario_comparison_count": 0,
        "parcel_set_count": 0,
        "parcel_context_session_count": 0,
        "parcel_field_map_count": 0,
        "proximity_request_count": 0,
        "proximity_result_count": 0,
        "composer_map_state_count": 0,
        "table_request_count": 0,
        "table_export_count": 0,
        "packets": {
            "review_packet_count": len(list_review_packets()),
            "adjusted_packet_count": len(list_adjusted_packets()),
            "approved_packet_count": len(list_approved_packets()),
        },
        "ports": {
            "frontend": AUTOMAP_FRONTEND_PORT,
            "backend_api": AUTOMAP_BACKEND_PORT,
            "reserved": [CFS_RESERVED_FRONTEND_PORT, CFS_RESERVED_BACKEND_PORT],
        },
        "arcgis_publisher_mode": "dry-run by default",
        "arcgis_publish_profile": "dev",
        "real_publish_enabled": False,
        "protected_database_status": "external project database was not accessed",
        "counts_partial": True,
        "status_mode": "quick",
        "errors": [],
    }


def get_database_health(schema_name: str | None = None, statement_timeout_ms: int = 3000) -> dict[str, Any]:
    """Return a fast, sanitized database health check for production badges."""
    settings = get_settings()
    schema = schema_name or settings.AUTOMAP_DB_SCHEMA
    result: dict[str, Any] = {
        "ok": False,
        "database_connected": False,
        "database_name": None,
        "database_host_kind": database_host_kind(settings.DATABASE_URL),
        "automap_schema": schema,
        "postgis_available": False,
        "postgis_version": None,
        "real_publish_enabled": False,
        "error_category": None,
    }
    _publisher_status(result)

    try:
        engine = get_engine(settings)
        with engine.connect() as connection:
            connection.execute(text(f"SET statement_timeout TO {int(statement_timeout_ms)};"))
            connection.execute(text("SELECT 1;")).scalar_one()
            database_name = connection.execute(text("SELECT current_database();")).scalar_one()
            postgis_version = connection.execute(text("SELECT PostGIS_Version();")).scalar_one()
            schema_exists = bool(
                connection.execute(
                    text("SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = :schema);"),
                    {"schema": schema},
                ).scalar_one()
            )
        result.update(
            {
                "ok": schema_exists,
                "database_connected": True,
                "database_name": database_name,
                "postgis_available": bool(postgis_version),
                "postgis_version": postgis_version,
                "error_category": None if schema_exists else "database_rejected",
            }
        )
    except (SQLAlchemyError, ValueError) as exc:
        result["error_category"] = categorize_database_error(exc)

    return result


def get_system_status(schema_name: str | None = None, mode: str = "quick") -> dict[str, Any]:
    """Return sanitized AutoMap status; quick mode avoids slow count fan-out."""
    settings = get_settings()
    schema = schema_name or settings.AUTOMAP_DB_SCHEMA
    normalized_mode = "full" if mode == "full" else "quick"
    status = _base_status(schema, settings.DATABASE_URL)
    status["status_mode"] = normalized_mode
    _publisher_status(status)

    db_health = get_database_health(schema)
    status.update(
        {
            "database_connected": bool(db_health.get("database_connected")),
            "database_name": db_health.get("database_name"),
            "database_host_kind": db_health.get("database_host_kind"),
            "automap_schema": db_health.get("automap_schema") or schema,
            "postgis_version": db_health.get("postgis_version"),
        }
    )
    if db_health.get("error_category"):
        status["errors"].append(f"database:{db_health['error_category']}")
    if normalized_mode == "quick" or not db_health.get("ok"):
        return status

    try:
        db_status = test_db_connection(settings)
        status.update(
            {
                "database_connected": bool(db_status.get("database_connected")),
                "database_name": db_status.get("database_name"),
                "database_host_kind": db_status.get("database_host_kind") or database_host_kind(settings.DATABASE_URL),
                "automap_schema": db_status.get("automap_schema") or schema,
                "postgis_version": db_status.get("postgis_version"),
            }
        )
        engine = get_engine(settings)
        with engine.connect() as connection:
            connection.execute(text("SET statement_timeout TO 4500;"))
            catalog_table = _qualified(schema, "layer_catalog")
            field_table = _qualified(schema, "layer_field_profile")
            value_table = _qualified(schema, "layer_value_profile")
            gaps_table = _qualified(schema, "data_gap_registry")
            external_source_table = _qualified(schema, "external_source_registry")
            history_table = _qualified(schema, "request_history")
            approval_table = _qualified(schema, "review_approval_history")
            analysis_table = _qualified(schema, "analysis_runs")
            refinement_table = _qualified(schema, "analysis_refinement_sessions")
            analysis_report_table = _qualified(schema, "analysis_report_history")
            scenario_table = _qualified(schema, "planning_scenarios")
            scenario_variant_table = _qualified(schema, "scenario_variants")
            scenario_comparison_table = _qualified(schema, "scenario_comparisons")
            parcel_sets_table = _qualified(schema, "parcel_sets")
            parcel_context_sessions_table = _qualified(schema, "parcel_context_sessions")
            parcel_field_map_table = _qualified(schema, "parcel_field_map")
            proximity_requests_table = _qualified(schema, "proximity_requests")
            proximity_results_table = _qualified(schema, "proximity_results")
            composer_map_states_table = _qualified(schema, "composer_map_states")
            table_requests_table = _qualified(schema, "table_requests")
            table_export_history_table = _qualified(schema, "table_export_history")
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
            status["external_source_count"] = _scalar_count(connection, f"SELECT count(*) FROM {external_source_table};")
            status["request_history_count"] = _scalar_count(connection, f"SELECT count(*) FROM {history_table};")
            status["approval_history_count"] = _scalar_count(connection, f"SELECT count(*) FROM {approval_table};")
            status["analysis_run_count"] = _scalar_count(connection, f"SELECT count(*) FROM {analysis_table};")
            status["analysis_refinement_count"] = _scalar_count(connection, f"SELECT count(*) FROM {refinement_table};")
            status["analysis_report_count"] = _scalar_count(connection, f"SELECT count(*) FROM {analysis_report_table};")
            status["planning_scenario_count"] = _scalar_count(connection, f"SELECT count(*) FROM {scenario_table};")
            status["scenario_variant_count"] = _scalar_count(connection, f"SELECT count(*) FROM {scenario_variant_table};")
            status["scenario_comparison_count"] = _scalar_count(connection, f"SELECT count(*) FROM {scenario_comparison_table};")
            status["parcel_set_count"] = _scalar_count(connection, f"SELECT count(*) FROM {parcel_sets_table};")
            status["parcel_context_session_count"] = _scalar_count(connection, f"SELECT count(*) FROM {parcel_context_sessions_table};")
            status["parcel_field_map_count"] = _scalar_count(connection, f"SELECT count(*) FROM {parcel_field_map_table};")
            status["proximity_request_count"] = _scalar_count(connection, f"SELECT count(*) FROM {proximity_requests_table};")
            status["proximity_result_count"] = _scalar_count(connection, f"SELECT count(*) FROM {proximity_results_table};")
            status["composer_map_state_count"] = _scalar_count(connection, f"SELECT count(*) FROM {composer_map_states_table};")
            status["table_request_count"] = _scalar_count(connection, f"SELECT count(*) FROM {table_requests_table};")
            status["table_export_count"] = _scalar_count(connection, f"SELECT count(*) FROM {table_export_history_table};")
        status["counts_partial"] = False
    except (SQLAlchemyError, ValueError) as exc:
        status["counts_partial"] = True
        status["errors"].append(f"counts:{categorize_database_error(exc)}")

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
        f"Database host kind: {status.get('database_host_kind') or 'unknown'}",
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
        f"External sources: {status.get('external_source_count', 0)}",
        f"Request history rows: {status['request_history_count']}",
        f"Approval history rows: {status['approval_history_count']}",
        f"Analysis runs: {status.get('analysis_run_count', 0)}",
        f"Analysis refinements: {status.get('analysis_refinement_count', 0)}",
        f"Analysis reports: {status.get('analysis_report_count', 0)}",
        f"Planning scenarios: {status.get('planning_scenario_count', 0)}",
        f"Scenario variants: {status.get('scenario_variant_count', 0)}",
        f"Scenario comparisons: {status.get('scenario_comparison_count', 0)}",
        f"Parcel sets: {status.get('parcel_set_count', 0)}",
        f"Parcel context sessions: {status.get('parcel_context_session_count', 0)}",
        f"Parcel field map rows: {status.get('parcel_field_map_count', 0)}",
        f"Proximity requests: {status.get('proximity_request_count', 0)}",
        f"Proximity results: {status.get('proximity_result_count', 0)}",
        f"Composer map states: {status.get('composer_map_state_count', 0)}",
        f"Table requests: {status.get('table_request_count', 0)}",
        f"Table exports: {status.get('table_export_count', 0)}",
        f"Review packets: {packets['review_packet_count']}",
        f"Adjusted packets: {packets['adjusted_packet_count']}",
        f"Approved packets: {packets['approved_packet_count']}",
        f"Frontend port: {status.get('ports', {}).get('frontend')}",
        f"Backend/API port: {status.get('ports', {}).get('backend_api')}",
        f"Reserved ports: {', '.join(str(port) for port in status.get('ports', {}).get('reserved', []))}",
        f"ArcGIS publisher mode: {status['arcgis_publisher_mode']}",
        f"Protected database reminder: {status['protected_database_status']}",
    ]
    if status["errors"]:
        lines.append("Errors:")
        lines.extend(f"- {error}" for error in status["errors"])
    return "\n".join(lines)
