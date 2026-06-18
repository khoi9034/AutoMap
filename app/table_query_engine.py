"""Plan, preview, and export bounded attribute table requests."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from app.db import _quote_identifier, get_engine
from app.table_exporter import write_table_export_package
from app.table_recipe_engine import build_table_recipe, choose_fields
from app.table_request_models import new_table_export_id
from app.table_safety import MAX_PREVIEW_ROWS, evaluate_table_safety


def _qualified(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def _coerce_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _normalize_db_row(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    for key in ("table_recipe", "output_formats", "warnings"):
        if key in normalized:
            normalized[key] = _coerce_json(normalized[key])
    return normalized


def init_table_request_tables(schema_name: str = "automap") -> None:
    quoted_schema = _quote_identifier(schema_name)
    requests_table = _qualified(schema_name, "table_requests")
    exports_table = _qualified(schema_name, "table_export_history")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {quoted_schema};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {requests_table} (
                    id serial PRIMARY KEY,
                    table_request_id text UNIQUE,
                    raw_prompt text,
                    table_recipe jsonb,
                    status text,
                    estimated_count integer,
                    output_folder text,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        connection.execute(text(f"ALTER TABLE {requests_table} ADD COLUMN IF NOT EXISTS output_folder text;"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {exports_table} (
                    id serial PRIMARY KEY,
                    export_id text UNIQUE,
                    table_request_id text,
                    output_folder text,
                    output_formats jsonb,
                    row_count integer,
                    field_count integer,
                    warnings jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )


def _safe_upsert_request(recipe: dict[str, Any], schema_name: str = "automap") -> None:
    init_table_request_tables(schema_name)
    table = _qualified(schema_name, "table_requests")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (table_request_id, raw_prompt, table_recipe, status, estimated_count)
                VALUES (:table_request_id, :raw_prompt, CAST(:table_recipe AS jsonb), :status, :estimated_count)
                ON CONFLICT (table_request_id)
                DO UPDATE SET table_recipe = EXCLUDED.table_recipe,
                              status = EXCLUDED.status,
                              estimated_count = EXCLUDED.estimated_count;
                """
            ),
            {
                "table_request_id": recipe.get("table_request_id"),
                "raw_prompt": recipe.get("raw_prompt"),
                "table_recipe": json.dumps(recipe, default=str),
                "status": recipe.get("safety_status"),
                "estimated_count": recipe.get("estimated_count"),
            },
        )


def _log_export(result: dict[str, Any], schema_name: str = "automap") -> None:
    init_table_request_tables(schema_name)
    table = _qualified(schema_name, "table_export_history")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (export_id, table_request_id, output_folder, output_formats, row_count, field_count, warnings)
                VALUES (:export_id, :table_request_id, :output_folder, CAST(:output_formats AS jsonb),
                        :row_count, :field_count, CAST(:warnings AS jsonb))
                ON CONFLICT (export_id) DO NOTHING;
                """
            ),
            {
                "export_id": result.get("export_id"),
                "table_request_id": result.get("table_request_id"),
                "output_folder": result.get("output_folder"),
                "output_formats": json.dumps(result.get("output_formats") or []),
                "row_count": len(result.get("rows") or []),
                "field_count": len(result.get("selected_fields") or []),
                "warnings": json.dumps(result.get("warnings") or []),
            },
        )


def _mark_request_output(result: dict[str, Any], schema_name: str = "automap") -> None:
    table = _qualified(schema_name, "table_requests")
    table_request_id = result.get("table_request_id")
    if not table_request_id or not result.get("output_folder"):
        return
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(f"UPDATE {table} SET output_folder = :output_folder WHERE table_request_id = :table_request_id"),
            {"output_folder": result.get("output_folder"), "table_request_id": table_request_id},
        )


def plan_table_query(prompt: str, layer_catalog: list[dict[str, Any]] | None = None, schema_name: str = "automap") -> dict[str, Any]:
    recipe = build_table_recipe(prompt, layer_catalog=layer_catalog, schema_name=schema_name)
    try:
        _safe_upsert_request(recipe, schema_name)
    except Exception:
        recipe["db_persisted"] = False
    return recipe


def estimate_table_count(table_recipe: dict[str, Any]) -> int:
    return int(table_recipe.get("estimated_count") or 0)


def _mock_preview_row(table_recipe: dict[str, Any], index: int) -> dict[str, Any]:
    row: dict[str, Any] = {}
    for field in table_recipe.get("selected_fields") or []:
        name = str(field.get("name") or "").strip()
        if name:
            row[name] = f"preview_{index + 1}"
    return row


def preview_table_rows(table_recipe: dict[str, Any]) -> dict[str, Any]:
    count = min(int(table_recipe.get("estimated_count") or 0), MAX_PREVIEW_ROWS, 5)
    rows = [_mock_preview_row(table_recipe, index) for index in range(count)]
    result = {
        "table_request_id": table_recipe.get("table_request_id"),
        "table_recipe": table_recipe,
        "preview_rows": rows,
        "rows": rows,
        "row_count": len(rows),
        "returnGeometry": False,
        "query_options": {"returnGeometry": False, "resultRecordCount": MAX_PREVIEW_ROWS},
    }
    table_recipe["preview_rows"] = rows
    return result


def validate_table_recipe(table_recipe: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not table_recipe.get("source_layers"):
        errors.append("No verified source layer selected.")
    if not table_recipe.get("selected_fields"):
        errors.append("No verified fields selected.")
    if table_recipe.get("query_options", {}).get("returnGeometry") is not False:
        errors.append("Table requests must use returnGeometry=false by default.")
    decision = evaluate_table_safety(table_recipe.get("estimated_count"), len(table_recipe.get("selected_fields") or []))
    return {"is_valid": not errors and decision.export_ready, "errors": errors, "safety": decision.as_dict()}


def execute_table_export(table_recipe: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    validation = validate_table_recipe(table_recipe)
    if not validation["safety"]["export_ready"]:
        return {
            "table_request_id": table_recipe.get("table_request_id"),
            "export_ready": False,
            "safety_status": validation["safety"]["safety_status"],
            "blocked_reasons": [*validation["errors"], *validation["safety"]["blocked_reasons"]],
            "returnGeometry": False,
        }
    preview = preview_table_rows(table_recipe)
    result = {
        **preview,
        "export_id": new_table_export_id(),
        "selected_fields": table_recipe.get("selected_fields") or [],
        "warnings": table_recipe.get("warnings") or [],
        "output_formats": table_recipe.get("output_formats") or ["csv", "json", "markdown"],
        "returnGeometry": False,
        "draft_only": True,
        "published": False,
    }
    package = write_table_export_package(result)
    result.update(package)
    try:
        _log_export(result, schema_name)
        _mark_request_output(result, schema_name)
    except Exception:
        result["db_persisted"] = False
    return result


def list_table_requests(schema_name: str = "automap", limit: int = 100) -> list[dict[str, Any]]:
    init_table_request_tables(schema_name)
    table = _qualified(schema_name, "table_requests")
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(text(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT :limit"), {"limit": limit}).mappings()
        return [_normalize_db_row(dict(row)) for row in rows]


def get_table_request(table_request_id: str, schema_name: str = "automap") -> dict[str, Any]:
    init_table_request_tables(schema_name)
    table = _qualified(schema_name, "table_requests")
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(text(f"SELECT * FROM {table} WHERE table_request_id = :id"), {"id": table_request_id}).mappings().first()
    if not row:
        raise FileNotFoundError(f"Table request not found: {table_request_id}")
    return _normalize_db_row(dict(row))


def list_table_exports(schema_name: str = "automap", limit: int = 100) -> list[dict[str, Any]]:
    init_table_request_tables(schema_name)
    table = _qualified(schema_name, "table_export_history")
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(text(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT :limit"), {"limit": limit}).mappings()
        return [_normalize_db_row(dict(row)) for row in rows]


def get_table_export(export_id: str, schema_name: str = "automap") -> dict[str, Any]:
    init_table_request_tables(schema_name)
    table = _qualified(schema_name, "table_export_history")
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(text(f"SELECT * FROM {table} WHERE export_id = :id"), {"id": export_id}).mappings().first()
    if not row:
        raise FileNotFoundError(f"Table export not found: {export_id}")
    return _normalize_db_row(dict(row))


def validate_table_export(export_folder: str) -> dict[str, Any]:
    from app.ui_models import repo_root

    folder = (repo_root() / export_folder).resolve()
    root = (repo_root() / "outputs/tables").resolve()
    try:
        folder.relative_to(root)
    except ValueError as exc:
        raise ValueError("Table export folder must be under outputs/tables.") from exc
    required = ["table_preview.json", "table_export.csv", "table_export.json", "table_summary.md", "export_manifest.json"]
    missing = [name for name in required if not (folder / name).exists()]
    return {"is_valid": not missing, "missing": missing, "folder": export_folder}
