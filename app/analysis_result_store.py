"""Local storage and AutoMap DB logging for spatial analysis runs."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.analysis_models import AnalysisExecutionResult
from app.db import _quote_identifier, get_engine
from app.layer_semantics import slugify
from app.ui_models import output_file_url, repo_root


ANALYSIS_OUTPUT_ROOT = Path("outputs/analysis")
PROTECTED_ANALYSIS_MARKERS = {
    ".env",
    "arcgis_password",
    "arcgis_username",
    "database_url",
    "password",
    "postgres_admin_url",
    "secret",
    "token",
    "cfs_dev",
}


def _analysis_runs_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.analysis_runs"


def _analysis_features_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.analysis_result_features"


def init_analysis_tables(schema_name: str = "automap") -> None:
    """Create additive AutoMap analysis tables safely."""
    runs_table = _analysis_runs_table(schema_name)
    features_table = _analysis_features_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {runs_table} (
                    id serial PRIMARY KEY,
                    analysis_run_id text UNIQUE,
                    raw_prompt text,
                    recipe_json jsonb,
                    operation_type text,
                    status text,
                    selected_layer_keys jsonb DEFAULT '[]'::jsonb,
                    input_counts jsonb DEFAULT '{{}}'::jsonb,
                    output_count integer,
                    output_geojson_path text,
                    analysis_receipt jsonb DEFAULT '{{}}'::jsonb,
                    warnings jsonb DEFAULT '[]'::jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {features_table} (
                    id serial PRIMARY KEY,
                    analysis_run_id text,
                    source_layer_key text,
                    source_object_id text,
                    properties jsonb,
                    geometry geometry,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "analysis_run_id": "text UNIQUE",
            "raw_prompt": "text",
            "recipe_json": "jsonb",
            "operation_type": "text",
            "status": "text",
            "selected_layer_keys": "jsonb DEFAULT '[]'::jsonb",
            "input_counts": "jsonb DEFAULT '{}'::jsonb",
            "output_count": "integer",
            "output_geojson_path": "text",
            "analysis_receipt": "jsonb DEFAULT '{}'::jsonb",
            "warnings": "jsonb DEFAULT '[]'::jsonb",
            "created_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {runs_table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _output_root() -> Path:
    root = ANALYSIS_OUTPUT_ROOT
    return root if root.is_absolute() else repo_root() / root


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _write_summary(path: Path, result: AnalysisExecutionResult) -> None:
    receipt = result.analysis_receipt or {}
    lines = [
        f"# AutoMap Analysis Run {result.analysis_run_id}",
        "",
        f"- Status: {result.status}",
        f"- Operation: {result.operation_type}",
        f"- Raw prompt: {result.raw_prompt}",
        f"- Output count: {result.output_count}",
        f"- Output GeoJSON: {result.output_geojson_path or 'not generated'}",
        "- Publishing: no ArcGIS item was created and nothing was uploaded.",
        "- Protected external planning database was not touched.",
        "",
        "## Counts",
        "```json",
        json.dumps(result.input_counts, indent=2, default=str),
        "```",
        "",
        "## Warnings",
    ]
    if result.warnings or result.blocked_reasons:
        lines.extend(f"- {item}" for item in [*result.warnings, *result.blocked_reasons])
    else:
        lines.append("- none")
    if receipt.get("where_clauses"):
        lines.extend(["", "## Where Clauses", "```json", json.dumps(receipt["where_clauses"], indent=2), "```"])
    path.write_text("\n".join(lines), encoding="utf-8")


def write_analysis_outputs(
    result: AnalysisExecutionResult,
    *,
    geojson: dict[str, Any] | None = None,
) -> AnalysisExecutionResult:
    """Write ignored local analysis output files."""
    title = result.recipe_json.get("map_title") or result.raw_prompt or result.analysis_run_id
    folder = _output_root() / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{slugify(title)[:90]}"
    folder.mkdir(parents=True, exist_ok=True)
    output_geojson_path: Path | None = None
    if geojson is not None:
        output_geojson_path = folder / "analysis_result.geojson"
        _write_json(output_geojson_path, geojson)
        result.output_geojson_path = output_geojson_path.relative_to(repo_root()).as_posix()
        result.derived_layer = {
            "id": f"automap_analysis_{result.analysis_run_id}",
            "title": result.analysis_receipt.get("derived_layer_title") or "Derived Local Analysis Result",
            "layer_key": f"analysis_{result.analysis_run_id}",
            "role": "derived_analysis_result",
            "source_status": "derived_local",
            "source_priority": 0,
            "url": output_file_url(result.output_geojson_path),
            "layer_url": output_file_url(result.output_geojson_path),
            "preview_type": "local_geojson",
            "visibility": True,
            "opacity": 0.85,
            "review_warnings": ["Derived local analysis result. Review before official use."],
            "derived_local_analysis": True,
        }
        result.analysis_receipt["derived_layer"] = result.derived_layer

    result.output_folder = folder.relative_to(repo_root()).as_posix()
    result.analysis_receipt.setdefault("analysis_run_id", result.analysis_run_id)
    result.analysis_receipt.setdefault("raw_prompt", result.raw_prompt)
    result.analysis_receipt.setdefault("operation_type", str(result.operation_type))
    result.analysis_receipt.setdefault("status", result.status)
    result.analysis_receipt.setdefault("max_feature_limits", {})
    result.analysis_receipt["output_geojson_path"] = result.output_geojson_path
    result.analysis_receipt["output_folder"] = result.output_folder
    result.analysis_receipt["output_count"] = result.output_count
    result.analysis_receipt["warnings"] = result.warnings
    result.analysis_receipt["blocked_reasons"] = result.blocked_reasons
    result.analysis_receipt["protected_external_database_touched"] = False
    result.analysis_receipt["published"] = False
    result.analysis_receipt["no_publish_statement"] = "No ArcGIS item was created, uploaded, shared, overwritten, or deleted."

    _write_json(folder / "input_recipe.json", result.recipe_json)
    _write_json(folder / "analysis_receipt.json", result.analysis_receipt)
    _write_summary(folder / "analysis_summary.md", result)
    return result


def record_analysis_run(result: AnalysisExecutionResult, schema_name: str = "automap") -> dict[str, Any]:
    """Upsert one analysis run receipt into AutoMap's own database."""
    init_analysis_tables(schema_name)
    table_name = _analysis_runs_table(schema_name)
    payload = result.to_dict()
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table_name} (
                    analysis_run_id, raw_prompt, recipe_json, operation_type, status,
                    selected_layer_keys, input_counts, output_count, output_geojson_path,
                    analysis_receipt, warnings
                )
                VALUES (
                    :analysis_run_id, :raw_prompt, CAST(:recipe_json AS jsonb),
                    :operation_type, :status, CAST(:selected_layer_keys AS jsonb),
                    CAST(:input_counts AS jsonb), :output_count, :output_geojson_path,
                    CAST(:analysis_receipt AS jsonb), CAST(:warnings AS jsonb)
                )
                ON CONFLICT (analysis_run_id) DO UPDATE SET
                    raw_prompt = EXCLUDED.raw_prompt,
                    recipe_json = EXCLUDED.recipe_json,
                    operation_type = EXCLUDED.operation_type,
                    status = EXCLUDED.status,
                    selected_layer_keys = EXCLUDED.selected_layer_keys,
                    input_counts = EXCLUDED.input_counts,
                    output_count = EXCLUDED.output_count,
                    output_geojson_path = EXCLUDED.output_geojson_path,
                    analysis_receipt = EXCLUDED.analysis_receipt,
                    warnings = EXCLUDED.warnings;
                """
            ),
            {
                "analysis_run_id": payload["analysis_run_id"],
                "raw_prompt": payload["raw_prompt"],
                "recipe_json": json.dumps(payload["recipe_json"]),
                "operation_type": payload["operation_type"],
                "status": payload["status"],
                "selected_layer_keys": json.dumps(payload["selected_layer_keys"]),
                "input_counts": json.dumps(payload["input_counts"]),
                "output_count": payload["output_count"],
                "output_geojson_path": payload["output_geojson_path"],
                "analysis_receipt": json.dumps(payload["analysis_receipt"]),
                "warnings": json.dumps(payload["warnings"]),
            },
        )
    return payload


def list_analysis_runs(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List recent analysis runs."""
    init_analysis_tables(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT analysis_run_id, raw_prompt, operation_type, status,
                       selected_layer_keys, input_counts, output_count,
                       output_geojson_path, analysis_receipt, warnings, created_at
                FROM {_analysis_runs_table(schema_name)}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return [dict(row) for row in rows]


def get_analysis_run(analysis_run_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one analysis run."""
    init_analysis_tables(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT analysis_run_id, raw_prompt, recipe_json, operation_type, status,
                       selected_layer_keys, input_counts, output_count,
                       output_geojson_path, analysis_receipt, warnings, created_at
                FROM {_analysis_runs_table(schema_name)}
                WHERE analysis_run_id = :analysis_run_id;
                """
            ),
            {"analysis_run_id": analysis_run_id},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"Analysis run not found: {analysis_run_id}")
    return dict(row)


def _iter_strings(value: Any) -> list[str]:
    strings: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            strings.append(str(key))
            strings.extend(_iter_strings(item))
    elif isinstance(value, list):
        for item in value:
            strings.extend(_iter_strings(item))
    elif isinstance(value, str):
        strings.append(value)
    return strings


def validate_analysis_run(analysis_run_id_or_path: str | Path) -> dict[str, Any]:
    """Validate an analysis run id or output folder."""
    errors: list[str] = []
    warnings: list[str] = []
    path = Path(analysis_run_id_or_path)
    if not path.exists():
        try:
            row = get_analysis_run(str(analysis_run_id_or_path))
            output_path = row.get("output_geojson_path")
            receipt = row.get("analysis_receipt") or {}
            if output_path:
                path = repo_root() / str(output_path)
                path = path.parent
            else:
                path = Path(str(receipt.get("output_folder") or ""))
        except FileNotFoundError as exc:
            errors.append(str(exc))
            path = Path()

    required = ["analysis_receipt.json", "input_recipe.json", "analysis_summary.md"]
    for file_name in required:
        if path and not (path / file_name).exists():
            errors.append(f"Missing required analysis output: {file_name}")
    receipt_data: dict[str, Any] = {}
    if path and (path / "analysis_receipt.json").exists():
        receipt_data = json.loads((path / "analysis_receipt.json").read_text(encoding="utf-8"))
    if receipt_data.get("status") == "completed" and not (path / "analysis_result.geojson").exists():
        errors.append("Completed analysis is missing analysis_result.geojson.")
    if path and (path / "analysis_result.geojson").exists():
        data = json.loads((path / "analysis_result.geojson").read_text(encoding="utf-8"))
        if data.get("type") != "FeatureCollection":
            errors.append("analysis_result.geojson is not a GeoJSON FeatureCollection.")
    combined = json.dumps(receipt_data, default=str).lower()
    for marker in PROTECTED_ANALYSIS_MARKERS:
        if marker in combined:
            errors.append(f"Analysis receipt contains protected marker: {marker}")
    if "no arcgis item was created" not in combined:
        warnings.append("Receipt should state that no ArcGIS item was created.")
    return {
        "is_valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "analysis_folder": str(path) if path else None,
    }
