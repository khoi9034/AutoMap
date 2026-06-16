"""Local parcel context report exports for AutoMap."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
import csv
import json
from pathlib import Path
from typing import Any

from app.parcel_context_engine import (
    build_parcel_context_recipe,
    get_parcel_set,
    parcel_report_slug,
)
from app.ui_models import output_file_url, repo_root


PARCEL_REPORT_OUTPUT_ROOT = Path("outputs/parcel_reports")
PARCEL_REPORT_FILES = [
    "parcel_context_report.html",
    "parcel_context_report.md",
    "parcel_context_report.json",
    "parcel_layer_summary.csv",
    "parcel_warnings.json",
    "export_manifest.json",
]
DRAFT_ONLY_DISCLAIMER = "This parcel context report is a local AutoMap review draft, not an official GIS map or decision."
CFS_UNTOUCHED_STATEMENT = "CFS repo and database were not accessed or modified by this AutoMap parcel workflow."


def _output_root() -> Path:
    root = PARCEL_REPORT_OUTPUT_ROOT
    return root if root.is_absolute() else repo_root() / root


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _repo_relative_or_absolute(path: Path) -> str:
    try:
        return path.relative_to(repo_root()).as_posix()
    except ValueError:
        return path.as_posix()


def _report_data(parcel_set_id: str, recipe: dict[str, Any]) -> dict[str, Any]:
    context = recipe.get("parcel_context") or {}
    return {
        "report_title": f"Parcel Context Report - {parcel_set_id}",
        "parcel_set_id": parcel_set_id,
        "original_prompt": recipe.get("user_intent"),
        "input_identifiers": context.get("parsed_identifiers") or [],
        "matched_parcels": context.get("matched_parcels_summary") or [],
        "unmatched_identifiers": context.get("unmatched_identifiers") or [],
        "candidate_matches": context.get("candidate_matches") or [],
        "selected_parcel_geojson": context.get("geometry_output_path"),
        "selected_context_layers": recipe.get("selected_layers") or [],
        "zoning_context": _layers_by_category(recipe, "zoning"),
        "flood_context": _layers_by_category(recipe, "flood"),
        "school_context": _layers_by_category(recipe, "schools"),
        "transportation_context": _layers_by_categories(recipe, {"transportation", "transportation_projects"}),
        "development_proxy_context": _layers_by_categories(recipe, {"development_activity_proxy", "planning_cases"}),
        "missing_official_data": recipe.get("missing_data_needed") or [],
        "source_coverage": recipe.get("source_coverage") or {},
        "warnings": recipe.get("review_reasons") or [],
        "draft_only_disclaimer": DRAFT_ONLY_DISCLAIMER,
        "cfs_untouched_statement": CFS_UNTOUCHED_STATEMENT,
        "no_publish_statement": "No ArcGIS item was created, uploaded, shared, overwritten, or deleted.",
    }


def _layers_by_category(recipe: dict[str, Any], category: str) -> list[dict[str, Any]]:
    return [layer for layer in recipe.get("selected_layers") or [] if layer.get("category") == category]


def _layers_by_categories(recipe: dict[str, Any], categories: set[str]) -> list[dict[str, Any]]:
    return [layer for layer in recipe.get("selected_layers") or [] if layer.get("category") in categories]


def build_parcel_report_markdown(report_data: dict[str, Any]) -> str:
    """Build Markdown for a parcel context report."""
    lines = [
        f"# {report_data['report_title']}",
        "",
        f"- Parcel set: {report_data.get('parcel_set_id')}",
        f"- Original prompt: {report_data.get('original_prompt') or ''}",
        f"- Matched parcels: {len(report_data.get('matched_parcels') or [])}",
        f"- Unmatched identifiers: {len(report_data.get('unmatched_identifiers') or [])}",
        f"- Selected parcel GeoJSON: {report_data.get('selected_parcel_geojson') or 'not generated'}",
        f"- Draft status: {report_data['draft_only_disclaimer']}",
        "- Publishing: no ArcGIS item was created or uploaded.",
        f"- CFS untouched: {report_data['cfs_untouched_statement']}",
        "",
        "## Matched Parcels",
    ]
    matched = report_data.get("matched_parcels") or []
    if matched:
        for row in matched:
            lines.append(
                f"- PIN14: {row.get('pin14') or '-'} | PIN: {row.get('pin') or '-'} | "
                f"Parcel ID: {row.get('parcel_id') or '-'} | Address: {row.get('address') or '-'}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Unmatched Identifiers"])
    unmatched = report_data.get("unmatched_identifiers") or []
    if unmatched:
        lines.extend(f"- {item.get('value') or item.get('normalized_value') or item}" for item in unmatched)
    else:
        lines.append("- none")
    lines.extend(["", "## Context Layers"])
    for layer in report_data.get("selected_context_layers") or []:
        lines.append(
            f"- {layer.get('display_title') or layer.get('layer_name')} | "
            f"{layer.get('category')} | {layer.get('source_role') or layer.get('source_status')}"
        )
    lines.extend(["", "## Missing Official Data"])
    missing = report_data.get("missing_official_data") or []
    lines.extend(f"- {item}" for item in missing) if missing else lines.append("- none recorded")
    lines.extend(["", "## Warnings"])
    warnings = report_data.get("warnings") or []
    lines.extend(f"- {item}" for item in warnings) if warnings else lines.append("- none")
    return "\n".join(lines)


def build_parcel_report_html(report_data: dict[str, Any]) -> str:
    """Build a simple HTML report for local parcel review."""
    layers = "".join(
        "<tr>"
        f"<td>{escape(str(layer.get('display_title') or layer.get('layer_name') or ''))}</td>"
        f"<td>{escape(str(layer.get('category') or ''))}</td>"
        f"<td>{escape(str(layer.get('source_role') or layer.get('source_status') or ''))}</td>"
        f"<td>{escape(str(layer.get('layer_url') or ''))}</td>"
        "</tr>"
        for layer in report_data.get("selected_context_layers") or []
    )
    warnings = "".join(f"<li>{escape(str(item))}</li>" for item in report_data.get("warnings") or [])
    unmatched = "".join(
        f"<li>{escape(str(item.get('value') or item.get('normalized_value') or item))}</li>"
        for item in report_data.get("unmatched_identifiers") or []
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>{escape(str(report_data['report_title']))}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; color: #172033; }}
    h1, h2 {{ color: #17416d; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
    th, td {{ border: 1px solid #d7e0ea; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #edf4fb; }}
    .notice {{ background: #fff7e6; border: 1px solid #f0c36d; padding: 12px; border-radius: 6px; }}
  </style>
</head>
<body>
  <h1>{escape(str(report_data['report_title']))}</h1>
  <p class="notice">{escape(DRAFT_ONLY_DISCLAIMER)}</p>
  <p><strong>Original prompt:</strong> {escape(str(report_data.get('original_prompt') or ''))}</p>
  <p><strong>Matched parcels:</strong> {len(report_data.get('matched_parcels') or [])}</p>
  <p><strong>Unmatched identifiers:</strong> {len(report_data.get('unmatched_identifiers') or [])}</p>
  <p><strong>Selected parcel GeoJSON:</strong> {escape(str(report_data.get('selected_parcel_geojson') or 'not generated'))}</p>
  <h2>Context Layers</h2>
  <table>
    <thead><tr><th>Layer</th><th>Category</th><th>Source role</th><th>URL</th></tr></thead>
    <tbody>{layers}</tbody>
  </table>
  <h2>Unmatched Identifiers</h2>
  <ul>{unmatched or '<li>none</li>'}</ul>
  <h2>Warnings</h2>
  <ul>{warnings or '<li>none</li>'}</ul>
  <p>{escape(CFS_UNTOUCHED_STATEMENT)}</p>
  <p>No ArcGIS item was created, uploaded, shared, overwritten, or deleted.</p>
</body>
</html>
"""


def _write_layer_summary(path: Path, layers: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["layer_key", "layer_name", "category", "source_role", "source_status", "approval_status", "layer_url"],
        )
        writer.writeheader()
        for layer in layers:
            writer.writerow(
                {
                    "layer_key": layer.get("layer_key"),
                    "layer_name": layer.get("display_title") or layer.get("layer_name"),
                    "category": layer.get("category"),
                    "source_role": layer.get("source_role"),
                    "source_status": layer.get("source_status"),
                    "approval_status": layer.get("approval_status"),
                    "layer_url": layer.get("layer_url"),
                }
            )


def generate_parcel_report(parcel_set_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Generate a local parcel context report package."""
    parcel_set = get_parcel_set(parcel_set_id, schema_name)
    recipe = build_parcel_context_recipe(parcel_set_id, raw_prompt=parcel_set.get("raw_input"), schema_name=schema_name)
    report_data = _report_data(parcel_set_id, recipe)
    folder = _output_root() / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{parcel_report_slug(parcel_set)}"
    folder.mkdir(parents=True, exist_ok=True)

    _write_json(folder / "parcel_context_report.json", report_data)
    (folder / "parcel_context_report.md").write_text(build_parcel_report_markdown(report_data), encoding="utf-8")
    (folder / "parcel_context_report.html").write_text(build_parcel_report_html(report_data), encoding="utf-8")
    _write_layer_summary(folder / "parcel_layer_summary.csv", report_data["selected_context_layers"])
    _write_json(folder / "parcel_warnings.json", {"warnings": report_data["warnings"], "missing_data": report_data["missing_official_data"]})
    manifest = {
        "report_id": folder.name,
        "parcel_set_id": parcel_set_id,
        "created_at": datetime.now(UTC).isoformat(),
        "files": {name: str(folder / name) for name in PARCEL_REPORT_FILES if (folder / name).exists()},
        "supported_formats": ["html", "markdown", "json", "csv"],
        "draft_only": True,
        "published": False,
    }
    _write_json(folder / "export_manifest.json", manifest)
    files = [
        {"name": name, "path": str(folder / name), "url": output_file_url(folder / name)}
        for name in PARCEL_REPORT_FILES
        if (folder / name).exists()
    ]
    return {
        "report_id": folder.name,
        "parcel_set_id": parcel_set_id,
        "report_folder": _repo_relative_or_absolute(folder),
        "report_title": report_data["report_title"],
        "files": files,
        "validation": validate_parcel_report(folder),
        "published": False,
    }


def validate_parcel_report(report_folder: str | Path) -> dict[str, Any]:
    """Validate required local parcel report files and safety text."""
    folder = Path(report_folder)
    if not folder.is_absolute():
        folder = repo_root() / folder
    errors: list[str] = []
    for name in PARCEL_REPORT_FILES:
        if not (folder / name).exists():
            errors.append(f"Missing required file: {name}")
    combined = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in folder.glob("*") if path.is_file())
    lowered = combined.lower()
    for marker in ["database_url", "password", "secret", "token", "arcgis_password"]:
        if marker in lowered:
            errors.append(f"Protected marker found in report output: {marker}")
    if "draft" not in lowered:
        errors.append("Draft-only disclaimer is missing.")
    if "no arcgis item" not in lowered:
        errors.append("No-publish statement is missing.")
    return {"is_valid": not errors, "errors": errors}
