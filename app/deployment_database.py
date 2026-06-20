"""Cloud deployment database initialization helpers for AutoMap."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.analysis_refinement_engine import init_refinement_tables
from app.analysis_report_exporter import init_analysis_report_history_table
from app.analysis_result_store import init_analysis_tables
from app.approval_engine import ensure_review_approval_history_table
from app.clarification_engine import ensure_clarification_sessions_table
from app.composer_state_store import init_composer_map_state_table
from app.config import Settings, get_settings, validate_settings
from app.data_gap_registry import ensure_data_gap_registry_table
from app.db import _quote_identifier, get_engine
from app.external_source_registry import init_external_source_tables
from app.field_profiler import ensure_field_intelligence_tables
from app.layer_catalog_store import ensure_layer_catalog_table
from app.parcel_context_engine import init_parcel_tables
from app.parcel_field_mapper import ensure_parcel_field_map_table
from app.pattern_library import init_pattern_tables
from app.proximity_engine import init_proximity_tables
from app.request_history import ensure_request_history_table
from app.scenario_builder import init_planning_scenario_table
from app.scenario_comparison import init_scenario_comparison_table
from app.scenario_variant_engine import init_scenario_variant_table
from app.table_query_engine import init_table_request_tables


POSTGIS_SQL_EDITOR_INSTRUCTION = (
    "Run CREATE EXTENSION IF NOT EXISTS postgis; in the Supabase SQL Editor, "
    "then rerun python -m app.main --deployment-init-db."
)

TableInitializer = tuple[str, Callable[[str], None]]


def deployment_table_initializers() -> list[TableInitializer]:
    """Return additive AutoMap table initializers used for cloud bootstrap."""
    return [
        ("layer_catalog", ensure_layer_catalog_table),
        ("field_intelligence", ensure_field_intelligence_tables),
        ("parcel_field_map", ensure_parcel_field_map_table),
        ("request_history", ensure_request_history_table),
        ("clarification_sessions", ensure_clarification_sessions_table),
        ("approved_patterns", init_pattern_tables),
        ("review_approval_history", ensure_review_approval_history_table),
        ("analysis", init_analysis_tables),
        ("analysis_refinements", init_refinement_tables),
        ("analysis_reports", init_analysis_report_history_table),
        ("data_gaps", ensure_data_gap_registry_table),
        ("external_sources", init_external_source_tables),
        ("parcel_workspace", init_parcel_tables),
        ("proximity", init_proximity_tables),
        ("planning_scenarios", init_planning_scenario_table),
        ("scenario_variants", init_scenario_variant_table),
        ("scenario_comparisons", init_scenario_comparison_table),
        ("composer_map_states", init_composer_map_state_table),
        ("table_requests", init_table_request_tables),
    ]


def _safe_error_type(exc: BaseException) -> str:
    """Return an error label without connection strings or secrets."""
    return exc.__class__.__name__


def _create_schema_and_health_check(
    schema_name: str,
    database_name: str,
    postgis_version: str,
    settings: Settings,
) -> None:
    quoted_schema = _quote_identifier(schema_name)
    engine = get_engine(settings)
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema};"))
        connection.execute(text(f"SET search_path TO {quoted_schema}, public;"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {quoted_schema}.project_database_check (
                    id serial PRIMARY KEY,
                    project_name text NOT NULL,
                    database_name text,
                    postgis_version text,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        connection.execute(text(f"ALTER TABLE {quoted_schema}.project_database_check ADD COLUMN IF NOT EXISTS database_name text;"))
        connection.execute(text(f"ALTER TABLE {quoted_schema}.project_database_check ADD COLUMN IF NOT EXISTS postgis_version text;"))
        connection.execute(
            text(
                f"""
                INSERT INTO {quoted_schema}.project_database_check (
                    project_name, database_name, postgis_version
                )
                VALUES ('automaps', :database_name, :postgis_version);
                """
            ),
            {"database_name": database_name, "postgis_version": postgis_version},
        )


def deployment_init_db(
    settings: Settings | None = None,
    initializers: Iterable[TableInitializer] | None = None,
) -> dict[str, Any]:
    """Initialize a Supabase/PostGIS AutoMap database without dropping data."""
    loaded_settings = settings or get_settings()
    validate_settings(loaded_settings)

    schema_name = loaded_settings.AUTOMAP_DB_SCHEMA
    engine = get_engine(loaded_settings)
    extension_warning: str | None = None

    try:
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            database_name = connection.execute(text("SELECT current_database();")).scalar_one()
            try:
                connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))
            except SQLAlchemyError as exc:
                extension_warning = (
                    f"PostGIS extension creation was not confirmed ({_safe_error_type(exc)}). "
                    f"{POSTGIS_SQL_EDITOR_INSTRUCTION}"
                )
            try:
                postgis_version = connection.execute(text("SELECT PostGIS_Version();")).scalar_one()
            except SQLAlchemyError as exc:
                return {
                    "success": False,
                    "database_connected": True,
                    "database_name": database_name,
                    "automap_schema": schema_name,
                    "postgis_version": None,
                    "created_tables": [],
                    "warnings": [extension_warning] if extension_warning else [],
                    "error": f"PostGIS is not available ({_safe_error_type(exc)}).",
                    "next_step": POSTGIS_SQL_EDITOR_INSTRUCTION,
                }
    except SQLAlchemyError as exc:
        return {
            "success": False,
            "database_connected": False,
            "database_name": None,
            "automap_schema": schema_name,
            "postgis_version": None,
            "created_tables": [],
            "warnings": [],
            "error": f"Database connection failed ({_safe_error_type(exc)}).",
            "next_step": "Verify DATABASE_URL uses the Supabase direct Postgres connection string.",
        }

    _create_schema_and_health_check(schema_name, database_name, str(postgis_version), loaded_settings)

    created_tables: list[str] = ["project_database_check"]
    warnings: list[str] = []
    if extension_warning:
        warnings.append(extension_warning)
    for label, initializer in initializers or deployment_table_initializers():
        try:
            initializer(schema_name)
            created_tables.append(label)
        except SQLAlchemyError as exc:
            warnings.append(f"{label} initializer failed with {_safe_error_type(exc)}.")

    return {
        "success": True,
        "database_connected": True,
        "database_name": database_name,
        "automap_schema": schema_name,
        "postgis_version": str(postgis_version),
        "created_tables": created_tables,
        "warnings": warnings,
        "message": "Deployment database initialization completed with safe CREATE IF NOT EXISTS operations.",
    }
