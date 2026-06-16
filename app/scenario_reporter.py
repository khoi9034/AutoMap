"""Local report exports for AutoMap planning scenarios."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any

from app.layer_semantics import slugify
from app.scenario_builder import get_scenario
from app.scenario_models import CFS_UNTOUCHED_STATEMENT, SCENARIO_REPORT_FORMATS, SCENARIO_REPORT_REQUIRED_FILES
from app.ui_models import output_file_url, repo_root


SCENARIO_REPORT_OUTPUT_ROOT = Path("outputs/scenario_reports")
PROTECTED_SCENARIO_REPORT_MARKERS = {
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
}


def _output_root() -> Path:
    return repo_root() / SCENARIO_REPORT_OUTPUT_ROOT


def _repo_relative(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _layer_name(layer: dict[str, Any]) -> str:
    return str(layer.get("display_title") or layer.get("layer_name") or layer.get("layer_key") or "")


def _warning_rows(scenario: dict[str, Any]) -> list[str]:
    rows = []
    rows.extend(str(item) for item in scenario.get("proxy_warnings") or [])
    rows.extend(str(item) for item in (scenario.get("source_coverage") or {}).get("warnings") or [])
    return sorted(set(row for row in rows if row))


def _report_data(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_id": scenario.get("scenario_id"),
        "scenario_title": scenario.get("scenario_title"),
        "raw_prompt": scenario.get("raw_prompt"),
        "scenario_type": scenario.get("scenario_type"),
        "planning_goal": scenario.get("planning_goal"),
        "selected_layers": scenario.get("selected_layers") or [],
        "scoring_framework": scenario.get("scoring_framework") or [],
        "assumptions": scenario.get("assumptions") or [],
        "review_questions": scenario.get("review_questions") or [],
        "source_coverage": scenario.get("source_coverage") or {},
        "source_coverage_warnings": _warning_rows(scenario),
        "missing_data": scenario.get("missing_data") or [],
        "execution_status": scenario.get("execution_status"),
        "official_use_disclaimer": scenario.get("official_use_disclaimer"),
        "cfs_untouched_statement": CFS_UNTOUCHED_STATEMENT,
        "supported_export_formats": SCENARIO_REPORT_FORMATS,
    }


def build_scenario_report_markdown(report_data: dict[str, Any]) -> str:
    """Build Markdown for a scenario report."""
    lines = [
        f"# {report_data.get('scenario_title') or 'AutoMap Planning Scenario'}",
        "",
        str(report_data.get("official_use_disclaimer") or ""),
        "",
        str(report_data.get("cfs_untouched_statement") or ""),
        "",
        "## Request",
        "",
        f"- Prompt: {report_data.get('raw_prompt') or ''}",
        f"- Scenario type: {report_data.get('scenario_type') or ''}",
        f"- Goal: {report_data.get('planning_goal') or ''}",
        f"- Execution status: {report_data.get('execution_status') or ''}",
        "",
        "## Selected Layers",
        "",
        "| Layer | Category | Source role | URL |",
        "| --- | --- | --- | --- |",
    ]
    for layer in report_data.get("selected_layers") or []:
        lines.append(
            "| "
            + " | ".join(
                [
                    _layer_name(layer),
                    str(layer.get("category") or ""),
                    str(layer.get("source_role") or layer.get("source_status") or ""),
                    str(layer.get("layer_url") or ""),
                ]
            )
            + " |"
        )
    if not report_data.get("selected_layers"):
        lines.append("| No layers |  |  |  |")
    lines.extend(
        [
            "",
            "## Scoring Framework",
            "",
            "| Factor | Type | Weight | Direction | Method | Review |",
            "| --- | --- | ---: | --- | --- | --- |",
        ]
    )
    for factor in report_data.get("scoring_framework") or []:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(factor.get("factor_label") or factor.get("factor_key") or ""),
                    str(factor.get("factor_type") or ""),
                    str(factor.get("suggested_weight") or 0),
                    str(factor.get("direction") or ""),
                    str(factor.get("scoring_method") or ""),
                    "yes" if factor.get("needs_review") else "no",
                ]
            )
            + " |"
        )
    lines.extend(["", "## Review Questions", ""])
    lines.extend([f"- {item}" for item in report_data.get("review_questions") or []] or ["- None"])
    lines.extend(["", "## Source Coverage Warnings", ""])
    lines.extend([f"- {item}" for item in report_data.get("source_coverage_warnings") or []] or ["- None"])
    lines.extend(["", "## Missing Data", ""])
    lines.extend([f"- {item}" for item in report_data.get("missing_data") or []] or ["- None"])
    return "\n".join(lines).strip() + "\n"


def build_scenario_report_html(report_data: dict[str, Any]) -> str:
    """Build HTML for a scenario report."""
    layer_rows = "".join(
        "<tr>"
        f"<td>{escape(_layer_name(layer))}</td>"
        f"<td>{escape(str(layer.get('category') or ''))}</td>"
        f"<td>{escape(str(layer.get('source_role') or layer.get('source_status') or ''))}</td>"
        f"<td>{escape(str(layer.get('layer_url') or ''))}</td>"
        "</tr>"
        for layer in report_data.get("selected_layers") or []
    )
    factor_rows = "".join(
        "<tr>"
        f"<td>{escape(str(factor.get('factor_label') or factor.get('factor_key') or ''))}</td>"
        f"<td>{escape(str(factor.get('factor_type') or ''))}</td>"
        f"<td>{escape(str(factor.get('suggested_weight') or 0))}</td>"
        f"<td>{escape(str(factor.get('direction') or ''))}</td>"
        f"<td>{escape(str(factor.get('scoring_method') or ''))}</td>"
        f"<td>{'yes' if factor.get('needs_review') else 'no'}</td>"
        "</tr>"
        for factor in report_data.get("scoring_framework") or []
    )
    warnings = "".join(f"<li>{escape(str(item))}</li>" for item in report_data.get("source_coverage_warnings") or [])
    questions = "".join(f"<li>{escape(str(item))}</li>" for item in report_data.get("review_questions") or [])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{escape(str(report_data.get('scenario_title') or 'AutoMap Scenario Report'))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; color: #172033; margin: 32px; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #d7dde8; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #eef4fb; }}
    .notice {{ background: #fff7ed; border: 1px solid #fed7aa; padding: 12px; }}
  </style>
</head>
<body>
  <h1>{escape(str(report_data.get('scenario_title') or 'AutoMap Scenario Report'))}</h1>
  <p class="notice">{escape(str(report_data.get('official_use_disclaimer') or ''))}</p>
  <p>{escape(str(report_data.get('cfs_untouched_statement') or ''))}</p>
  <h2>Request</h2>
  <p><strong>Prompt:</strong> {escape(str(report_data.get('raw_prompt') or ''))}</p>
  <p><strong>Scenario type:</strong> {escape(str(report_data.get('scenario_type') or ''))}</p>
  <p><strong>Goal:</strong> {escape(str(report_data.get('planning_goal') or ''))}</p>
  <p><strong>Execution status:</strong> {escape(str(report_data.get('execution_status') or ''))}</p>
  <h2>Selected Layers</h2>
  <table><thead><tr><th>Layer</th><th>Category</th><th>Source role</th><th>URL</th></tr></thead><tbody>{layer_rows}</tbody></table>
  <h2>Scoring Framework</h2>
  <table><thead><tr><th>Factor</th><th>Type</th><th>Weight</th><th>Direction</th><th>Method</th><th>Review</th></tr></thead><tbody>{factor_rows}</tbody></table>
  <h2>Review Questions</h2>
  <ul>{questions or '<li>None</li>'}</ul>
  <h2>Source Coverage Warnings</h2>
  <ul>{warnings or '<li>None</li>'}</ul>
</body>
</html>
"""


def _write_scoring_csv(path: Path, factors: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "factor_key",
                "factor_label",
                "factor_type",
                "layer_keys",
                "suggested_weight",
                "direction",
                "scoring_method",
                "needs_review",
                "notes",
            ],
        )
        writer.writeheader()
        for factor in factors:
            row = dict(factor)
            row["layer_keys"] = ";".join(str(item) for item in factor.get("layer_keys") or [])
            writer.writerow(row)


def _validate_report_folder(folder: Path) -> dict[str, Any]:
    errors: list[str] = []
    for required in sorted(SCENARIO_REPORT_REQUIRED_FILES):
        if not (folder / required).exists():
            errors.append(f"Missing required file: {required}")
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in folder.glob("*") if path.is_file()).lower()
    for marker in sorted(PROTECTED_SCENARIO_REPORT_MARKERS):
        if marker in combined:
            errors.append(f"Scenario report contains protected marker: {marker}")
    return {"is_valid": not errors, "errors": errors}


def generate_scenario_report(scenario_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Generate a local scenario report package for one stored scenario."""
    scenario = get_scenario(scenario_id, schema_name=schema_name)
    report_data = _report_data(scenario)
    folder = _output_root() / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{slugify(report_data.get('scenario_title') or scenario_id)[:90]}"
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(folder / "scenario_report.json", report_data)
    (folder / "scenario_report.md").write_text(build_scenario_report_markdown(report_data), encoding="utf-8")
    (folder / "scenario_report.html").write_text(build_scenario_report_html(report_data), encoding="utf-8")
    _write_scoring_csv(folder / "scoring_framework.csv", report_data.get("scoring_framework") or [])
    _write_json(folder / "source_coverage.json", report_data.get("source_coverage") or {})
    manifest = {
        "scenario_id": scenario_id,
        "report_folder": _repo_relative(folder),
        "files": sorted(SCENARIO_REPORT_REQUIRED_FILES),
        "supported_formats": SCENARIO_REPORT_FORMATS,
        "generated_at": datetime.now(UTC).isoformat(),
        "published": False,
        "no_publish_statement": "No ArcGIS item was created, uploaded, shared, overwritten, or deleted.",
    }
    _write_json(folder / "export_manifest.json", manifest)
    validation = _validate_report_folder(folder)
    return {
        "scenario_id": scenario_id,
        "report_folder": _repo_relative(folder),
        "report_title": report_data.get("scenario_title"),
        "files": [
            {
                "name": name,
                "path": _repo_relative(folder / name),
                "url": output_file_url(_repo_relative(folder / name)),
            }
            for name in sorted(SCENARIO_REPORT_REQUIRED_FILES)
        ],
        "validation": validation,
    }
