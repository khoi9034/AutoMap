"""Export AutoMap analysis summaries as local draft report packages."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.analysis_summary_engine import build_analysis_summary_from_refinement, build_analysis_summary_from_run
from app.analysis_summary_models import (
    ANALYSIS_REPORT_FORMATS,
    ANALYSIS_REPORT_REQUIRED_FILES,
    AnalysisReportPackage,
    AnalysisSummaryReport,
    CFS_UNTOUCHED_ANALYSIS_STATEMENT,
    DRAFT_ONLY_ANALYSIS_REPORT_DISCLAIMER,
)
from app.db import _quote_identifier, get_engine
from app.layer_semantics import slugify
from app.ui_models import output_file_url, repo_root


ANALYSIS_REPORT_OUTPUT_ROOT = Path("outputs/analysis_reports")
PROTECTED_ANALYSIS_REPORT_MARKERS = {
    ".env",
    "arcgis_password",
    "arcgis_username",
    "database_url",
    "postgres_admin_url",
    "password",
    "secret",
    "steins",
    "token",
    "cfs_dev",
    "cabarrusfuturescape",
}


def _history_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.analysis_report_history"


def init_analysis_report_history_table(schema_name: str = "automap") -> None:
    """Create the additive analysis report history table in the AutoMap schema."""
    table = _history_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY,
                    report_id text UNIQUE,
                    source_analysis_run_id text,
                    source_refinement_session_id text,
                    report_folder text,
                    report_title text,
                    report_status text,
                    summary_json jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "report_id": "text UNIQUE",
            "source_analysis_run_id": "text",
            "source_refinement_session_id": "text",
            "report_folder": "text",
            "report_title": "text",
            "report_status": "text",
            "summary_json": "jsonb",
            "created_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _output_root() -> Path:
    root = ANALYSIS_REPORT_OUTPUT_ROOT
    return root if root.is_absolute() else repo_root() / root


def _repo_relative(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _contains_protected_marker(text: str) -> str | None:
    lowered = text.lower()
    for marker in sorted(PROTECTED_ANALYSIS_REPORT_MARKERS):
        if marker in lowered:
            return marker
    return None


def _iter_strings(value: Any) -> list[str]:
    if isinstance(value, dict):
        rows: list[str] = []
        for key, item in value.items():
            rows.append(str(key))
            rows.extend(_iter_strings(item))
        return rows
    if isinstance(value, list):
        return [text for item in value for text in _iter_strings(item)]
    if isinstance(value, str):
        return [value]
    return []


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            if _contains_protected_marker(str(key)):
                continue
            safe[key] = _redact(item)
        return safe
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, str) and _contains_protected_marker(value):
        return "[redacted]"
    return value


def _summary_tables(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "count_summary": [
            {
                "broad_count": report_data.get("broad_count"),
                "optimized_candidate_count": report_data.get("optimized_count"),
                "safety_limit": report_data.get("safety_limit"),
                "blocked": report_data.get("analysis_status") == "blocked",
            }
        ],
        "chunk_summary": next(
            (section.get("rows") for section in report_data.get("sections") or [] if section.get("summary_type") == "chunk_summary"),
            [],
        ),
        "grouped_attribute_summary": report_data.get("grouped_summaries") or [],
        "safety_summary": [
            {
                "geometry_downloaded": report_data.get("geometry_downloaded"),
                "geojson_created": report_data.get("geojson_created"),
                "selected_refinement_option": report_data.get("selected_refinement_option"),
            }
        ],
    }


def _warning_summary(report_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "warnings": report_data.get("warnings") or {},
        "missing_data": report_data.get("missing_data") or [],
        "narrowing_suggestions": report_data.get("narrowing_suggestions") or [],
        "draft_only_disclaimer": report_data.get("draft_only_disclaimer"),
    }


def _layer_title(layer: dict[str, Any]) -> str:
    return str(layer.get("layer_name") or layer.get("title") or layer.get("layer_key") or "")


def _layer_url(layer: dict[str, Any]) -> str:
    return str(layer.get("layer_url") or layer.get("url") or layer.get("rest_url") or "")


def _write_layer_csv(path: Path, layers: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["layer_key", "layer_name", "category", "role", "source_status", "layer_url"],
        )
        writer.writeheader()
        for layer in layers:
            writer.writerow(
                {
                    "layer_key": layer.get("layer_key"),
                    "layer_name": _layer_title(layer),
                    "category": layer.get("category"),
                    "role": layer.get("role"),
                    "source_status": layer.get("source_status"),
                    "layer_url": _layer_url(layer),
                }
            )


def _markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No selected layers were recorded."]
    lines = [
        "| Layer | Category | Role | Source | URL |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _layer_title(row),
                    str(row.get("category") or ""),
                    str(row.get("role") or ""),
                    str(row.get("source_status") or ""),
                    _layer_url(row),
                ]
            )
            + " |"
        )
    return lines


def build_analysis_report_markdown(report_data: dict[str, Any]) -> str:
    """Build Markdown for an analysis report."""
    lines = [
        f"# {report_data['report_title']}",
        "",
        report_data.get("draft_only_disclaimer") or DRAFT_ONLY_ANALYSIS_REPORT_DISCLAIMER,
        "",
        report_data.get("cfs_untouched_statement") or CFS_UNTOUCHED_ANALYSIS_STATEMENT,
        "",
        "## Request And Status",
        "",
        f"- Original prompt: {report_data.get('raw_prompt') or ''}",
        f"- Source type: {report_data.get('source_type') or ''}",
        f"- Analysis status: {report_data.get('analysis_status') or ''}",
        f"- Operation: {report_data.get('operation_type') or ''}",
        f"- Strategy used: {report_data.get('strategy_used') or ''}",
        f"- Selected refinement option: {report_data.get('selected_refinement_option') or 'not applicable'}",
        "",
        "## Counts And Safety",
        "",
        f"- Broad count: {report_data.get('broad_count')}",
        f"- Optimized candidate count: {report_data.get('optimized_count')}",
        f"- Safety limit: {report_data.get('safety_limit')}",
        f"- Geometry downloaded: {report_data.get('geometry_downloaded')}",
        f"- GeoJSON produced: {report_data.get('geojson_created')}",
        "",
        "## Selected Layers",
        "",
        *_markdown_table(report_data.get("selected_layers") or []),
        "",
        "## Grouped Summaries",
        "",
    ]
    grouped = report_data.get("grouped_summaries") or []
    if grouped:
        for item in grouped:
            lines.append(f"- {item.get('field_name') or item.get('summary_type')}: {item.get('status')}")
    else:
        lines.append("- None")
    lines.extend(["", "## Warnings", ""])
    for group, warnings in (report_data.get("warnings") or {}).items():
        lines.append(f"### {str(group).replace('_', ' ').title()}")
        lines.extend([f"- {warning}" for warning in warnings] or ["- None"])
        lines.append("")
    lines.extend(["## Recommended Next Refinements", ""])
    suggestions = report_data.get("narrowing_suggestions") or []
    lines.extend([f"- {item}" for item in suggestions] or ["- None"])
    return "\n".join(lines).strip() + "\n"


def build_analysis_report_html(report_data: dict[str, Any]) -> str:
    """Build HTML for an analysis report."""
    layers = report_data.get("selected_layers") or []
    layer_rows = []
    for layer in layers:
        url = _layer_url(layer)
        link = f'<a href="{escape(url)}" target="_blank" rel="noreferrer">{escape(url)}</a>' if url else ""
        layer_rows.append(
            "<tr>"
            f"<td>{escape(_layer_title(layer))}</td>"
            f"<td>{escape(str(layer.get('category') or ''))}</td>"
            f"<td>{escape(str(layer.get('role') or ''))}</td>"
            f"<td>{escape(str(layer.get('source_status') or ''))}</td>"
            f"<td>{link}</td>"
            "</tr>"
        )
    grouped_rows = []
    for item in report_data.get("grouped_summaries") or []:
        grouped_rows.append(
            "<tr>"
            f"<td>{escape(str(item.get('field_name') or item.get('summary_type') or ''))}</td>"
            f"<td>{escape(str(item.get('status') or ''))}</td>"
            f"<td>{escape(str(item.get('reason') or ''))}</td>"
            f"<td>{escape(str(len(item.get('rows') or [])))}</td>"
            "</tr>"
        )
    warnings = []
    for group, rows in (report_data.get("warnings") or {}).items():
        items = "".join(f"<li>{escape(str(row))}</li>" for row in rows) or "<li>None</li>"
        warnings.append(f"<section><h3>{escape(str(group).replace('_', ' ').title())}</h3><ul>{items}</ul></section>")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(report_data.get('report_title') or 'AutoMap Analysis Report'))}</title>
  <style>
    body {{ margin: 0; background: #f5f7fb; color: #172033; font-family: Arial, Helvetica, sans-serif; line-height: 1.5; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    header, section {{ background: #fff; border: 1px solid #d9e2ec; border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
    .banner {{ background: #fff8ed; border-color: #ffd69a; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
    .metrics div {{ background: #f8fafc; border: 1px solid #d9e2ec; border-radius: 8px; padding: 12px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border-bottom: 1px solid #d9e2ec; padding: 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ color: #667085; font-size: .9rem; }}
    a {{ color: #1d5f9f; }}
  </style>
</head>
<body>
  <main>
    <header>
      <p><strong>AutoMap: County GIS Request Engine</strong></p>
      <h1>{escape(str(report_data.get('report_title') or 'Analysis Report'))}</h1>
      <p><strong>Prompt:</strong> {escape(str(report_data.get('raw_prompt') or ''))}</p>
    </header>
    <section class="banner">
      <h2>Draft-only report</h2>
      <p>{escape(str(report_data.get('draft_only_disclaimer') or DRAFT_ONLY_ANALYSIS_REPORT_DISCLAIMER))}</p>
      <p>{escape(str(report_data.get('cfs_untouched_statement') or CFS_UNTOUCHED_ANALYSIS_STATEMENT))}</p>
    </section>
    <section>
      <h2>Counts And Safety</h2>
      <div class="metrics">
        <div><strong>Broad count</strong><br>{escape(str(report_data.get('broad_count')))}</div>
        <div><strong>Optimized count</strong><br>{escape(str(report_data.get('optimized_count')))}</div>
        <div><strong>Safety limit</strong><br>{escape(str(report_data.get('safety_limit')))}</div>
        <div><strong>Geometry downloaded</strong><br>{escape(str(report_data.get('geometry_downloaded')))}</div>
      </div>
    </section>
    <section>
      <h2>Selected Layers</h2>
      <table>
        <thead><tr><th>Layer</th><th>Category</th><th>Role</th><th>Source</th><th>URL</th></tr></thead>
        <tbody>{''.join(layer_rows) or '<tr><td colspan="5">No selected layers recorded.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Grouped Summaries</h2>
      <table>
        <thead><tr><th>Field</th><th>Status</th><th>Note</th><th>Groups</th></tr></thead>
        <tbody>{''.join(grouped_rows) or '<tr><td colspan="4">No grouped summaries available.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Warnings</h2>
      {''.join(warnings)}
    </section>
  </main>
</body>
</html>
"""


def _manifest(report_data: dict[str, Any], files: dict[str, str]) -> dict[str, Any]:
    return {
        "report_id": report_data.get("report_id"),
        "report_title": report_data.get("report_title"),
        "created_at": datetime.now(UTC).isoformat(),
        "source_type": report_data.get("source_type"),
        "source_analysis_run_id": report_data.get("source_analysis_run_id"),
        "source_refinement_session_id": report_data.get("source_refinement_session_id"),
        "supported_formats": ANALYSIS_REPORT_FORMATS,
        "files": files,
        "geometry_downloaded": report_data.get("geometry_downloaded"),
        "published": False,
        "draft_only": True,
    }


def _record_history(package: AnalysisReportPackage, report_data: dict[str, Any], schema_name: str = "automap") -> None:
    init_analysis_report_history_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {_history_table(schema_name)} (
                    report_id, source_analysis_run_id, source_refinement_session_id,
                    report_folder, report_title, report_status, summary_json
                )
                VALUES (
                    :report_id, :source_analysis_run_id, :source_refinement_session_id,
                    :report_folder, :report_title, :report_status, CAST(:summary_json AS jsonb)
                )
                ON CONFLICT (report_id) DO UPDATE SET
                    source_analysis_run_id = EXCLUDED.source_analysis_run_id,
                    source_refinement_session_id = EXCLUDED.source_refinement_session_id,
                    report_folder = EXCLUDED.report_folder,
                    report_title = EXCLUDED.report_title,
                    report_status = EXCLUDED.report_status,
                    summary_json = EXCLUDED.summary_json;
                """
            ),
            {
                "report_id": package.report_id,
                "source_analysis_run_id": package.source_analysis_run_id,
                "source_refinement_session_id": package.source_refinement_session_id,
                "report_folder": _repo_relative(package.report_path),
                "report_title": package.report_title,
                "report_status": str(report_data.get("analysis_status") or ""),
                "summary_json": json.dumps(report_data, default=str),
            },
        )


def export_analysis_report(summary: AnalysisSummaryReport) -> AnalysisReportPackage:
    """Write one local analysis report package and record history."""
    report_data = _redact(summary.to_dict())
    folder = _output_root() / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{slugify(summary.report_title)[:90]}"
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        "analysis_report.html": _repo_relative(folder / "analysis_report.html"),
        "analysis_report.md": _repo_relative(folder / "analysis_report.md"),
        "analysis_report.json": _repo_relative(folder / "analysis_report.json"),
        "summary_tables.json": _repo_relative(folder / "summary_tables.json"),
        "layer_summary.csv": _repo_relative(folder / "layer_summary.csv"),
        "warning_summary.json": _repo_relative(folder / "warning_summary.json"),
        "export_manifest.json": _repo_relative(folder / "export_manifest.json"),
    }
    (folder / "analysis_report.html").write_text(build_analysis_report_html(report_data), encoding="utf-8")
    (folder / "analysis_report.md").write_text(build_analysis_report_markdown(report_data), encoding="utf-8")
    _write_json(folder / "analysis_report.json", report_data)
    _write_json(folder / "summary_tables.json", _summary_tables(report_data))
    _write_layer_csv(folder / "layer_summary.csv", report_data.get("selected_layers") or [])
    _write_json(folder / "warning_summary.json", _warning_summary(report_data))
    _write_json(folder / "export_manifest.json", _manifest(report_data, files))
    package = AnalysisReportPackage(
        report_id=str(summary.report_id),
        report_path=folder,
        report_title=str(summary.report_title),
        source_type=str(summary.source_type),
        source_analysis_run_id=summary.source_analysis_run_id,
        source_refinement_session_id=summary.source_refinement_session_id,
        files=files,
    )
    package.validation = validate_analysis_report(folder)
    _record_history(package, report_data)
    return package


def generate_analysis_report(analysis_run_id: str, *, include_grouped_statistics: bool = True) -> AnalysisReportPackage:
    """Generate a local analysis report from an analysis run id."""
    summary = build_analysis_summary_from_run(analysis_run_id, include_grouped_statistics=include_grouped_statistics)
    return export_analysis_report(summary)


def generate_analysis_report_from_refinement(
    refinement_session_id: str,
    *,
    include_grouped_statistics: bool = True,
) -> AnalysisReportPackage:
    """Generate a local analysis report from a refinement session id."""
    summary = build_analysis_summary_from_refinement(refinement_session_id, include_grouped_statistics=include_grouped_statistics)
    return export_analysis_report(summary)


def list_analysis_reports(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List recorded analysis report packages."""
    init_analysis_report_history_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT report_id, source_analysis_run_id, source_refinement_session_id,
                       report_folder, report_title, report_status, summary_json, created_at
                FROM {_history_table(schema_name)}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        results: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["created_at"] = str(item.get("created_at")) if item.get("created_at") is not None else None
            if isinstance(item.get("summary_json"), str):
                try:
                    item["summary_json"] = json.loads(item["summary_json"])
                except json.JSONDecodeError:
                    item["summary_json"] = {}
            item["files"] = _file_links(item.get("report_folder"))
            results.append(_redact(item))
        return results


def get_analysis_report(report_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one analysis report history row plus file links."""
    init_analysis_report_history_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT report_id, source_analysis_run_id, source_refinement_session_id,
                       report_folder, report_title, report_status, summary_json, created_at
                FROM {_history_table(schema_name)}
                WHERE report_id = :report_id;
                """
            ),
            {"report_id": report_id},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"Analysis report not found: {report_id}")
    item = dict(row)
    item["created_at"] = str(item.get("created_at")) if item.get("created_at") is not None else None
    if isinstance(item.get("summary_json"), str):
        try:
            item["summary_json"] = json.loads(item["summary_json"])
        except json.JSONDecodeError:
            item["summary_json"] = {}
    item["files"] = _file_links(item.get("report_folder"))
    return _redact(item)


def _file_links(report_folder: str | None) -> list[dict[str, str]]:
    if not report_folder:
        return []
    folder = repo_root() / report_folder
    links = []
    for file_name in sorted(ANALYSIS_REPORT_REQUIRED_FILES):
        if (folder / file_name).exists():
            relative = f"{report_folder.rstrip('/')}/{file_name}"
            links.append({"name": file_name, "url": output_file_url(relative), "path": relative})
    return links


def validate_analysis_report(report_folder: str | Path) -> dict[str, Any]:
    """Validate required analysis report files and protected markers."""
    path = Path(report_folder)
    if not path.is_absolute():
        path = repo_root() / path
    errors: list[str] = []
    if not path.exists() or not path.is_dir():
        errors.append(f"Analysis report folder not found: {report_folder}")
    for file_name in sorted(ANALYSIS_REPORT_REQUIRED_FILES):
        if path.exists() and not (path / file_name).exists():
            errors.append(f"Missing required analysis report file: {file_name}")
    combined = ""
    if path.exists():
        for file_path in path.glob("*"):
            if file_path.is_file() and file_path.suffix.lower() in {".json", ".md", ".html", ".csv"}:
                combined += file_path.read_text(encoding="utf-8", errors="ignore").lower()
    marker = _contains_protected_marker(combined)
    if marker:
        errors.append(f"Analysis report contains protected marker: {marker}")
    if path.exists() and (path / "analysis_report.html").exists():
        html = (path / "analysis_report.html").read_text(encoding="utf-8", errors="ignore").lower()
        if "draft-only" not in html and "draft only" not in html:
            errors.append("Analysis report HTML is missing draft-only disclaimer.")
    if path.exists() and (path / "analysis_report.json").exists():
        try:
            data = json.loads((path / "analysis_report.json").read_text(encoding="utf-8"))
            if data.get("geometry_downloaded") and data.get("source_type") == "analysis_refinement":
                errors.append("Refinement report should not claim geometry was downloaded unless the refinement did so.")
        except json.JSONDecodeError:
            errors.append("analysis_report.json could not be parsed.")
    return {"is_valid": not errors, "errors": errors, "report_folder": _repo_relative(path) if path.exists() else str(report_folder)}
