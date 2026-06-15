"""Generate local review/export report packages from AutoMap workflow packets."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any

from app.data_gap_registry import data_gap_records_from_recipe
from app.layer_semantics import slugify
from app.report_models import REQUIRED_REPORT_FILES, ReportPackage, ReportSource, SUPPORTED_REPORT_FORMATS
from app.review_packet_builder import build_layer_review_table
from app.ui_models import output_file_url, repo_root


OUTPUTS_ROOT = Path("outputs")
REPORTS_FOLDER = "reports"

PROTECTED_REPORT_MARKERS = {
    ".env",
    "arcgis_password",
    "arcgis_username",
    "cfs_dev",
    "database_url",
    "postgres_admin_url",
    "password",
    "secret",
    "steins",
    "token",
}

DRAFT_ONLY_DISCLAIMER = (
    "This AutoMap report is a local draft export for GIS review. It is not an official map, "
    "does not publish to ArcGIS, and does not create or share ArcGIS items."
)
CFS_UNTOUCHED_STATEMENT = "CFS repo and database were not accessed or modified by this report export."


def _outputs_root() -> Path:
    root = OUTPUTS_ROOT
    return root.resolve() if root.is_absolute() else (repo_root() / root).resolve()


def _reports_root() -> Path:
    return _outputs_root() / REPORTS_FOLDER


def _safe_output_path(path: str | Path) -> Path:
    candidate = Path(path)
    output_root = _outputs_root()
    if not candidate.is_absolute():
        parts = candidate.parts
        if parts and parts[0].lower() == "outputs":
            candidate = output_root.joinpath(*parts[1:])
        else:
            candidate = repo_root() / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise ValueError("Report paths must stay inside AutoMap outputs.") from exc
    return resolved


def _output_relative_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        try:
            return (Path("outputs") / resolved.relative_to(_outputs_root())).as_posix()
        except ValueError:
            return resolved.name


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _optional_json(path: Path) -> Any:
    if not path.exists():
        return {} if path.suffix == ".json" else None
    try:
        return _load_json(path)
    except (OSError, json.JSONDecodeError):
        return {}


def _packet_type(path: Path) -> str:
    if (path / "approved_webmap.json").exists():
        return "approved"
    if (path / "adjusted_webmap.json").exists():
        return "adjusted"
    if (path / "webmap.json").exists():
        return "review"
    raise FileNotFoundError(f"Unsupported AutoMap packet folder: {path}")


def _file_names(packet_type: str) -> dict[str, str]:
    if packet_type == "approved":
        return {
            "recipe": "approved_recipe.json",
            "webmap": "approved_webmap.json",
            "warnings": "approved_warnings.json",
            "layer_review": "approved_layer_review.json",
            "summary": "approved_review_summary.md",
        }
    if packet_type == "adjusted":
        return {
            "recipe": "adjusted_recipe.json",
            "webmap": "adjusted_webmap.json",
            "warnings": "adjusted_warnings.json",
            "layer_review": "adjusted_layer_review.json",
            "summary": "adjusted_review_summary.md",
        }
    return {
        "recipe": "recipe.json",
        "webmap": "webmap.json",
        "warnings": "warnings.json",
        "layer_review": "layer_review.json",
        "summary": "review_summary.md",
    }


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            rows.append(text)
            seen.add(text)
    return rows


def _definition_expression(layer: dict[str, Any]) -> str:
    definition = layer.get("layerDefinition") or {}
    expression = definition.get("definitionExpression")
    return expression.strip() if isinstance(expression, str) else ""


def _layer_url(row: dict[str, Any]) -> str:
    return str(row.get("layer_url") or row.get("url") or row.get("layerUrl") or "")


def _layer_rows(source: ReportSource) -> list[dict[str, Any]]:
    rows = source.layer_review or build_layer_review_table(source.recipe, source.webmap)
    if rows:
        return rows

    recipe_lookup = {
        layer.get("layer_key"): layer
        for layer in source.recipe.get("selected_layers") or []
        if layer.get("layer_key")
    }
    fallback_rows: list[dict[str, Any]] = []
    for layer in source.webmap.get("operationalLayers") or []:
        layer_key = layer.get("autoMapLayerKey")
        recipe_layer = recipe_lookup.get(layer_key) or {}
        fallback_rows.append(
            {
                "title": layer.get("title") or recipe_layer.get("layer_name") or layer_key,
                "layer_key": layer_key,
                "role": recipe_layer.get("role") or layer.get("autoMapRole"),
                "layer_url": recipe_layer.get("layer_url") or layer.get("layerUrl") or layer.get("url"),
                "service_url": recipe_layer.get("service_url") or layer.get("serviceUrl"),
                "source_status": recipe_layer.get("source_status") or layer.get("autoMapSourceStatus"),
                "source_priority": recipe_layer.get("source_priority") or layer.get("autoMapSourcePriority"),
                "geometry_type": recipe_layer.get("geometry_type"),
                "definition_expression": _definition_expression(layer),
                "opacity": layer.get("opacity"),
                "visibility": layer.get("visibility", True),
                "confidence_score": recipe_layer.get("confidence_score") or layer.get("autoMapConfidence"),
                "match_reasons": recipe_layer.get("match_reasons") or [],
            }
        )
    return fallback_rows


def _flatten_warning_items(value: Any, prefix: str = "") -> list[str]:
    if not value:
        return []
    if isinstance(value, dict):
        rows: list[str] = []
        for key, item in value.items():
            next_prefix = f"{prefix}: {key}" if prefix else str(key)
            rows.extend(_flatten_warning_items(item, next_prefix))
        return rows
    if isinstance(value, list):
        return [item for child in value for item in _flatten_warning_items(child, prefix)]
    text = str(value)
    return [f"{prefix}: {text}" if prefix else text]


def _warning_bucket(text: str) -> str:
    lowered = text.lower()
    if "missing" in lowered or "gap" in lowered:
        return "missing_data"
    if "filter" in lowered or "definition" in lowered or "expression" in lowered or "field" in lowered:
        return "filter_review"
    if "publish" in lowered or "block" in lowered or "ready" in lowered:
        return "publishing_blockers"
    if "historical" in lowered or "legacy" in lowered:
        return "historical_data"
    if "symbol" in lowered or "renderer" in lowered or "style" in lowered:
        return "symbology_review"
    return "layer_selection"


def _group_warnings(source: ReportSource) -> dict[str, list[str]]:
    groups = {
        "missing_data": [],
        "filter_review": [],
        "layer_selection": [],
        "symbology_review": [],
        "publishing_blockers": [],
        "historical_data": [],
        "safety_warnings": [DRAFT_ONLY_DISCLAIMER],
    }
    for text in _flatten_warning_items(source.warnings):
        groups.setdefault(_warning_bucket(text), []).append(text)
    for text in _as_list(source.recipe.get("review_reasons")):
        groups.setdefault(_warning_bucket(str(text)), []).append(str(text))
    for text in _as_list(source.recipe.get("missing_data_needed")):
        groups["missing_data"].append(f"Missing requested data: {text}")
    for reason in _as_list(source.approval_receipt.get("block_reasons")):
        groups["publishing_blockers"].append(str(reason))
    for key, values in list(groups.items()):
        groups[key] = _dedupe([str(value) for value in values])
    return groups


def load_report_source(packet_folder: str | Path) -> ReportSource:
    """Load a review, adjusted, or approved packet into normalized report source data."""
    packet_path = _safe_output_path(packet_folder)
    if not packet_path.exists() or not packet_path.is_dir():
        raise FileNotFoundError(f"AutoMap packet folder not found: {packet_folder}")
    packet_type = _packet_type(packet_path)
    files = _file_names(packet_type)
    recipe_path = packet_path / files["recipe"]
    webmap_path = packet_path / files["webmap"]
    if not recipe_path.exists() or not webmap_path.exists():
        raise FileNotFoundError(f"Packet is missing required recipe or WebMap JSON: {packet_path}")
    recipe = _load_json(recipe_path)
    webmap = _load_json(webmap_path)
    layer_review = _optional_json(packet_path / files["layer_review"]) or build_layer_review_table(recipe, webmap)
    return ReportSource(
        packet_path=packet_path,
        packet_type=packet_type,
        recipe=recipe,
        webmap=webmap,
        warnings=_optional_json(packet_path / files["warnings"]) or {},
        layer_review=layer_review if isinstance(layer_review, list) else [],
        adjustments=_optional_json(packet_path / "applied_adjustments.json") or {},
        approval_receipt=_optional_json(packet_path / "approval_receipt.json") or {},
        approval_file=_optional_json(packet_path / "approval_file.json") or {},
        publish_receipt=_optional_json(packet_path / "publish_receipt.json") or {},
        smoke_test_receipt=_optional_json(packet_path / "smoke_test_receipt.json") or {},
    )


def _report_title(source: ReportSource) -> str:
    map_title = source.recipe.get("map_title") or source.webmap.get("title") or source.packet_path.name
    return f"AutoMap Report - {map_title}"


def _workflow_status(source: ReportSource) -> str:
    if source.packet_type == "approved":
        return "approved_local_draft"
    if source.packet_type == "adjusted":
        return "adjusted_local_draft"
    return "review_packet"


def _symbology_notes(source: ReportSource) -> list[str]:
    notes: list[str] = []
    for item in _as_list(source.recipe.get("symbology_recommendations")):
        if isinstance(item, dict):
            notes.append(json.dumps(item, default=str))
        else:
            notes.append(str(item))
    for layer in source.webmap.get("operationalLayers") or []:
        title = layer.get("title") or layer.get("autoMapLayerKey") or "Layer"
        if layer.get("renderer"):
            notes.append(f"{title}: renderer configured")
        elif (layer.get("layerDefinition") or {}).get("drawingInfo"):
            notes.append(f"{title}: drawingInfo configured")
    return _dedupe(notes)


def build_report_data(source: ReportSource) -> dict[str, Any]:
    """Build JSON-serializable report data from normalized source packet artifacts."""
    layer_rows = _layer_rows(source)
    warning_groups = _group_warnings(source)
    map_title = source.recipe.get("map_title") or source.webmap.get("title") or source.packet_path.name
    original_prompt = (
        source.recipe.get("user_intent")
        or (source.recipe.get("parsed_request") or {}).get("raw_prompt")
        or source.webmap.get("description")
        or ""
    )
    definition_expressions = [
        {
            "layer": row.get("title") or row.get("layer_key"),
            "definition_expression": row.get("definition_expression"),
        }
        for row in layer_rows
        if row.get("definition_expression")
    ]
    adjustment_notes = {
        "reviewer_notes": (source.recipe.get("human_adjustment") or {}).get("reviewer_notes") or [],
        "missing_data_notes": (source.recipe.get("human_adjustment") or {}).get("missing_data_notes") or [],
        "applied_adjustments": source.adjustments,
    }
    approval = {
        "decision": source.approval_file.get("decision") or source.approval_receipt.get("decision"),
        "final_publish_ready": source.approval_receipt.get("final_publish_ready"),
        "block_reasons": source.approval_receipt.get("block_reasons") or [],
        "reviewer_notes": source.approval_receipt.get("reviewer_notes") or [],
        "local_approval_only": True if source.approval_receipt else None,
    }
    data = {
        "report_title": _report_title(source),
        "generated_at": datetime.now(UTC).isoformat(),
        "original_prompt": original_prompt,
        "generated_map_title": map_title,
        "workflow_status": _workflow_status(source),
        "packet_type": source.packet_type,
        "packet_path": _output_relative_path(source.packet_path),
        "selected_layers": layer_rows,
        "layer_roles": [
            {"layer": row.get("title") or row.get("layer_key"), "role": row.get("role")}
            for row in layer_rows
        ],
        "layer_urls": [_layer_url(row) for row in layer_rows if _layer_url(row)],
        "definition_expressions": definition_expressions,
        "spatial_operations": source.recipe.get("spatial_operations") or [],
        "symbology_notes": _symbology_notes(source),
        "warnings": warning_groups,
        "missing_data": source.recipe.get("missing_data_needed") or [],
        "data_gaps": source.recipe.get("data_gap_notes") or data_gap_records_from_recipe(source.recipe),
        "adjustment_notes": adjustment_notes,
        "approval": approval,
        "final_publish_ready": source.approval_receipt.get("final_publish_ready"),
        "dry_run_publish_receipt": source.publish_receipt,
        "portal_smoke_test_receipt": source.smoke_test_receipt,
        "draft_only_disclaimer": DRAFT_ONLY_DISCLAIMER,
        "cfs_untouched_statement": CFS_UNTOUCHED_STATEMENT,
        "supported_export_formats": SUPPORTED_REPORT_FORMATS,
    }
    return _redact_report_value(data)


def _redact_report_value(value: Any) -> Any:
    if isinstance(value, dict):
        safe: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _contains_protected_marker(key_text):
                continue
            safe[key] = _redact_report_value(item)
        return safe
    if isinstance(value, list):
        return [_redact_report_value(item) for item in value]
    if isinstance(value, str) and _contains_protected_marker(value):
        return "[redacted]"
    return value


def _contains_protected_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PROTECTED_REPORT_MARKERS)


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


def _protected_marker_in_report(value: Any) -> str | None:
    for text in _iter_strings(value):
        lowered = text.lower()
        for marker in sorted(PROTECTED_REPORT_MARKERS):
            if marker in lowered:
                return marker
    return None


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def _markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return ["No selected layers were recorded."]
    lines = [
        "| Layer | Role | Source Status | Definition Expression | REST URL |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("title") or row.get("layer_key") or ""),
                    str(row.get("role") or ""),
                    str(row.get("source_status") or ""),
                    f"`{row.get('definition_expression')}`" if row.get("definition_expression") else "",
                    _layer_url(row),
                ]
            )
            + " |"
        )
    return lines


def build_report_markdown(report_data: dict[str, Any]) -> str:
    """Build Markdown report summary text."""
    lines = [
        f"# {report_data['report_title']}",
        "",
        report_data["draft_only_disclaimer"],
        "",
        report_data["cfs_untouched_statement"],
        "",
        "## Request",
        "",
        f"- Original prompt: {report_data.get('original_prompt') or ''}",
        f"- Generated map title: {report_data.get('generated_map_title') or ''}",
        f"- Workflow status: {report_data.get('workflow_status') or ''}",
        f"- Packet type: {report_data.get('packet_type') or ''}",
        "",
        "## Selected Layers",
        "",
        *_markdown_table(report_data.get("selected_layers") or []),
        "",
        "## Spatial Operations",
        "",
    ]
    spatial = report_data.get("spatial_operations") or []
    if spatial:
        for operation in spatial:
            lines.append(f"- {json.dumps(operation, default=str)}")
    else:
        lines.append("No spatial operations were recorded.")

    lines.extend(["", "## Symbology Notes", ""])
    symbology = report_data.get("symbology_notes") or []
    lines.extend([f"- {note}" for note in symbology] or ["No symbology notes were recorded."])

    lines.extend(["", "## Warnings", ""])
    for group, warnings in (report_data.get("warnings") or {}).items():
        lines.append(f"### {str(group).replace('_', ' ').title()}")
        lines.extend([f"- {warning}" for warning in warnings] or ["- None"])
        lines.append("")

    lines.extend(["## Missing Data And Data Gaps", ""])
    missing = report_data.get("missing_data") or []
    lines.extend([f"- {item}" for item in missing] or ["No missing data was reported."])

    lines.extend(["", "## Adjustment And Approval", ""])
    approval = report_data.get("approval") or {}
    lines.append(f"- Final publish ready: {report_data.get('final_publish_ready')}")
    lines.append(f"- Approval decision: {approval.get('decision')}")
    block_reasons = approval.get("block_reasons") or []
    if block_reasons:
        lines.extend(f"- Block reason: {reason}" for reason in block_reasons)

    lines.extend(["", "## Dry-Run Receipts", ""])
    publish_receipt = report_data.get("dry_run_publish_receipt") or {}
    smoke_receipt = report_data.get("portal_smoke_test_receipt") or {}
    lines.append(f"- Publish dry-run receipt present: {bool(publish_receipt)}")
    lines.append(f"- Portal smoke-test dry-run receipt present: {bool(smoke_receipt)}")

    return "\n".join(lines).strip() + "\n"


def build_report_html(report_data: dict[str, Any]) -> str:
    """Build HTML report summary text."""
    layers = report_data.get("selected_layers") or []
    layer_rows = []
    for row in layers:
        url = _layer_url(row)
        link = f'<a href="{escape(url)}" target="_blank" rel="noreferrer">{escape(url)}</a>' if url else ""
        layer_rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('title') or row.get('layer_key') or ''))}</td>"
            f"<td>{escape(str(row.get('role') or ''))}</td>"
            f"<td>{escape(str(row.get('source_status') or ''))}</td>"
            f"<td><code>{escape(str(row.get('definition_expression') or ''))}</code></td>"
            f"<td>{link}</td>"
            "</tr>"
        )
    warning_sections = []
    for group, warnings in (report_data.get("warnings") or {}).items():
        items = "".join(f"<li>{escape(str(warning))}</li>" for warning in warnings) or "<li>None</li>"
        warning_sections.append(f"<section><h3>{escape(str(group).replace('_', ' ').title())}</h3><ul>{items}</ul></section>")
    missing_items = "".join(f"<li>{escape(str(item))}</li>" for item in report_data.get("missing_data") or "") or "<li>None</li>"
    approval = report_data.get("approval") or {}
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(report_data.get('report_title')))}</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --panel: #ffffff;
      --ink: #172033;
      --muted: #667085;
      --line: #d9e2ec;
      --blue: #1d5f9f;
      --amber: #a15c08;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.5;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }}
    header, section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin-bottom: 16px;
    }}
    .banner {{
      border-color: #ffd69a;
      background: #fff8ed;
      color: #573306;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      table-layout: fixed;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
      overflow-wrap: anywhere;
    }}
    th {{
      color: var(--muted);
      font-size: 0.9rem;
    }}
    code {{
      background: #eef3f8;
      border-radius: 4px;
      padding: 2px 4px;
    }}
    a {{
      color: var(--blue);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <p><strong>AutoMap: County GIS Request Engine</strong></p>
      <h1>{escape(str(report_data.get('generated_map_title') or report_data.get('report_title')))}</h1>
      <p><strong>Original prompt:</strong> {escape(str(report_data.get('original_prompt') or ''))}</p>
      <p><strong>Workflow status:</strong> {escape(str(report_data.get('workflow_status') or ''))}</p>
    </header>
    <section class="banner">
      <h2>Draft-only disclaimer</h2>
      <p>{escape(str(report_data.get('draft_only_disclaimer') or DRAFT_ONLY_DISCLAIMER))}</p>
      <p>{escape(str(report_data.get('cfs_untouched_statement') or CFS_UNTOUCHED_STATEMENT))}</p>
    </section>
    <section>
      <h2>Selected Layers</h2>
      <table>
        <thead><tr><th>Layer</th><th>Role</th><th>Source</th><th>Definition Expression</th><th>REST URL</th></tr></thead>
        <tbody>{''.join(layer_rows) or '<tr><td colspan="5">No selected layers recorded.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Warnings</h2>
      {''.join(warning_sections)}
    </section>
    <section>
      <h2>Missing Data</h2>
      <ul>{missing_items}</ul>
    </section>
    <section>
      <h2>Approval And Dry-Run Status</h2>
      <ul>
        <li>Final publish ready: {escape(str(report_data.get('final_publish_ready')))}</li>
        <li>Approval decision: {escape(str(approval.get('decision')))}</li>
        <li>Dry-run publish receipt present: {escape(str(bool(report_data.get('dry_run_publish_receipt'))))}</li>
        <li>Portal smoke-test receipt present: {escape(str(bool(report_data.get('portal_smoke_test_receipt'))))}</li>
      </ul>
    </section>
  </main>
</body>
</html>
"""


def _write_layer_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "title",
        "layer_key",
        "role",
        "layer_url",
        "service_url",
        "source_status",
        "source_priority",
        "geometry_type",
        "definition_expression",
        "opacity",
        "visibility",
        "confidence_score",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _file_links(report_path: Path) -> dict[str, str]:
    return {
        file_name: output_file_url(_output_relative_path(report_path / file_name))
        for file_name in sorted(REQUIRED_REPORT_FILES)
        if (report_path / file_name).exists()
    }


def generate_report(packet_folder: str | Path, output_root: str | Path | None = None) -> ReportPackage:
    """Generate a local report/export package from an AutoMap packet folder."""
    source = load_report_source(packet_folder)
    report_data = build_report_data(source)
    marker = _protected_marker_in_report(report_data)
    if marker:
        raise ValueError(f"Report data contains protected marker: {marker}")

    root = Path(output_root).resolve() if output_root else _reports_root()
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    title_slug = slugify(str(report_data.get("generated_map_title") or source.packet_path.name))[:90] or "automap_report"
    report_path = root / f"{timestamp}_{title_slug}"
    report_path.mkdir(parents=True, exist_ok=False)

    layer_rows = report_data.get("selected_layers") or []
    warning_report = report_data.get("warnings") or {}
    manifest = {
        "report_id": report_path.name,
        "report_path": _output_relative_path(report_path),
        "source_packet_path": _output_relative_path(source.packet_path),
        "source_packet_type": source.packet_type,
        "generated_at": report_data["generated_at"],
        "supported_formats": SUPPORTED_REPORT_FORMATS,
        "files": sorted(REQUIRED_REPORT_FILES),
        "pdf_supported": False,
        "pdf_note": "PDF export is not enabled in v1.7; HTML and Markdown are the supported readable report formats.",
        "draft_only_disclaimer": DRAFT_ONLY_DISCLAIMER,
    }

    (report_path / "report_summary.md").write_text(build_report_markdown(report_data), encoding="utf-8")
    (report_path / "report_summary.html").write_text(build_report_html(report_data), encoding="utf-8")
    _write_json(report_path / "report_data.json", report_data)
    _write_json(report_path / "warning_report.json", warning_report)
    _write_json(report_path / "export_manifest.json", manifest)
    _write_layer_csv(report_path / "layer_table.csv", layer_rows)

    validation = validate_report(report_path)
    return ReportPackage(
        report_id=report_path.name,
        report_path=report_path,
        report_title=str(report_data["report_title"]),
        packet_type=source.packet_type,
        packet_path=_output_relative_path(source.packet_path),
        files={file_name: str(report_path / file_name) for file_name in sorted(REQUIRED_REPORT_FILES)},
        validation=validation,
    )


def _folder_updated_at(path: Path) -> datetime:
    candidates = [path, *[item for item in path.iterdir() if item.is_file()]]
    latest = max(item.stat().st_mtime for item in candidates)
    return datetime.fromtimestamp(latest, tz=UTC)


def list_reports() -> list[dict[str, Any]]:
    """List generated report packages newest first."""
    root = _reports_root()
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        manifest = _optional_json(path / "export_manifest.json") or {}
        report_data = _optional_json(path / "report_data.json") or {}
        updated_at = _folder_updated_at(path)
        rows.append(
            {
                "report_id": path.name,
                "report_path": _output_relative_path(path),
                "report_title": report_data.get("report_title") or manifest.get("report_id") or path.name,
                "generated_map_title": report_data.get("generated_map_title"),
                "workflow_status": report_data.get("workflow_status"),
                "packet_type": report_data.get("packet_type") or manifest.get("source_packet_type"),
                "source_packet_path": report_data.get("packet_path") or manifest.get("source_packet_path"),
                "updated_at": updated_at.isoformat(),
                "files": _file_links(path),
            }
        )
    return sorted(rows, key=lambda row: row["updated_at"], reverse=True)


def get_report(report_id: str) -> dict[str, Any]:
    """Return report details and file links for one generated report id."""
    report_path = _safe_output_path(Path("outputs") / REPORTS_FOLDER / report_id)
    if not report_path.exists() or not report_path.is_dir():
        raise FileNotFoundError(f"Report not found: {report_id}")
    report_data = _optional_json(report_path / "report_data.json") or {}
    manifest = _optional_json(report_path / "export_manifest.json") or {}
    return {
        "report_id": report_path.name,
        "report_path": _output_relative_path(report_path),
        "report_data": report_data,
        "manifest": manifest,
        "files": _file_links(report_path),
        "validation": validate_report(report_path),
    }


def validate_report(report_folder: str | Path) -> dict[str, Any]:
    """Validate a generated local report package."""
    report_path = _safe_output_path(report_folder)
    errors: list[str] = []
    warnings: list[str] = []
    if not report_path.exists() or not report_path.is_dir():
        return {
            "is_valid": False,
            "errors": [f"Report folder not found: {report_folder}"],
            "warnings": [],
            "report_path": str(report_path),
        }

    missing_files = sorted(file_name for file_name in REQUIRED_REPORT_FILES if not (report_path / file_name).exists())
    if missing_files:
        errors.append(f"Missing required report files: {', '.join(missing_files)}")

    report_data: dict[str, Any] = {}
    warning_report: dict[str, Any] = {}
    manifest: dict[str, Any] = {}
    try:
        if (report_path / "report_data.json").exists():
            report_data = _load_json(report_path / "report_data.json")
        if (report_path / "warning_report.json").exists():
            warning_report = _load_json(report_path / "warning_report.json")
        if (report_path / "export_manifest.json").exists():
            manifest = _load_json(report_path / "export_manifest.json")
    except json.JSONDecodeError as exc:
        errors.append(f"Report JSON is invalid: {exc}")

    combined_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in report_path.iterdir()
        if path.is_file() and path.suffix.lower() in {".json", ".md", ".html", ".csv"}
    )
    marker = _protected_marker_in_report(combined_text)
    if marker:
        errors.append(f"Report contains protected marker: {marker}")

    layer_urls = [str(item) for item in report_data.get("layer_urls") or []]
    csv_text = (report_path / "layer_table.csv").read_text(encoding="utf-8", errors="ignore") if (report_path / "layer_table.csv").exists() else ""
    if layer_urls and not all(url in csv_text for url in layer_urls):
        errors.append("Layer URLs are not preserved in layer_table.csv.")
    if not layer_urls:
        warnings.append("No layer URLs were recorded in report_data.json.")

    warning_items = _flatten_warning_items(warning_report)
    if not warning_items:
        errors.append("Warnings were not preserved in warning_report.json.")

    summary_text = (report_path / "report_summary.md").read_text(encoding="utf-8", errors="ignore") if (report_path / "report_summary.md").exists() else ""
    html_text = (report_path / "report_summary.html").read_text(encoding="utf-8", errors="ignore") if (report_path / "report_summary.html").exists() else ""
    if DRAFT_ONLY_DISCLAIMER not in summary_text or "does not publish to ArcGIS" not in html_text:
        errors.append("Draft-only disclaimer is missing from report summaries.")
    if not manifest.get("pdf_supported") and "html" not in manifest.get("supported_formats", []):
        errors.append("Supported export formats are not documented in export_manifest.json.")

    return {
        "is_valid": not errors,
        "errors": _dedupe(errors),
        "warnings": _dedupe(warnings),
        "report_path": _output_relative_path(report_path),
        "required_files_present": not missing_files,
        "layer_url_count": len(layer_urls),
        "warning_count": len(warning_items),
    }
