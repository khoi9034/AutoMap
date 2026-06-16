"""Build local human-review packets for AutoMap draft map requests."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any

from app.layer_semantics import slugify
from app.recipe_engine import build_recipe
from app.webmap_builder import build_webmap_json, validate_webmap_json


REQUIRED_PACKET_FILES = {
    "recipe.json",
    "webmap.json",
    "review_summary.md",
    "warnings.json",
    "layer_review.json",
    "review.html",
}

PROTECTED_OUTPUT_MARKERS = {
    "cfs",
    "cfs_dev",
    ".env",
    "database_url",
    "postgres_admin_url",
    "your_local_postgres_password",
    "password",
    "token",
    "portalurl",
    "portalitem",
}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            deduped.append(text)
            seen.add(text)
    return deduped


def _definition_expression(operational_layer: dict[str, Any]) -> str | None:
    layer_definition = operational_layer.get("layerDefinition") or {}
    expression = layer_definition.get("definitionExpression")
    if isinstance(expression, str) and expression.strip():
        return expression.strip()
    return None


def _selected_layer_lookup(recipe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        layer["layer_key"]: layer
        for layer in recipe.get("selected_layers") or []
        if layer.get("layer_key")
    }


def _operational_layer_lookup(webmap_json: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        layer["autoMapLayerKey"]: layer
        for layer in webmap_json.get("operationalLayers") or []
        if layer.get("autoMapLayerKey")
    }


def _new_opendata_preference_statement(recipe: dict[str, Any]) -> str:
    selected = recipe.get("selected_layers") or []
    if not selected:
        return "No layers were selected."
    historical_year = recipe.get("parsed_request", {}).get("historical_year")
    historical_layers = [
        layer
        for layer in selected
        if str(layer.get("source_status") or "").startswith("legacy_historical")
    ]
    if historical_year and historical_layers:
        return f"Historical layers were selected because the user requested {historical_year}."
    if any(int(layer.get("source_priority") or 999) == 1 for layer in selected):
        return "Yes. Verified new OpenData layers were preferred where available."
    return "No verified new OpenData match was selected; fallback metadata was used."


def build_layer_review_table(recipe: dict[str, Any], webmap_json: dict[str, Any]) -> list[dict[str, Any]]:
    """Build analyst-facing layer review rows from recipe and WebMap layers."""
    recipe_layers = _selected_layer_lookup(recipe)
    rows: list[dict[str, Any]] = []
    for operational_layer in webmap_json.get("operationalLayers") or []:
        layer_key = operational_layer.get("autoMapLayerKey")
        recipe_layer = recipe_layers.get(layer_key, {})
        source_status = (
            recipe_layer.get("source_status")
            or operational_layer.get("autoMapSourceStatus")
            or ""
        )
        rows.append(
            {
                "title": operational_layer.get("title"),
                "layer_key": layer_key,
                "role": recipe_layer.get("role") or operational_layer.get("autoMapRole"),
                "layer_url": recipe_layer.get("layer_url") or operational_layer.get("layerUrl") or operational_layer.get("url"),
                "service_url": recipe_layer.get("service_url") or operational_layer.get("serviceUrl"),
                "source_status": source_status,
                "approval_status": recipe_layer.get("approval_status") or operational_layer.get("autoMapApprovalStatus"),
                "source_role": recipe_layer.get("source_role") or operational_layer.get("autoMapSourceRole"),
                "coverage_geography": recipe_layer.get("coverage_geography") or operational_layer.get("autoMapCoverageGeography"),
                "source_limitation": recipe_layer.get("source_limitation") or recipe_layer.get("known_limitations"),
                "gap_support": recipe_layer.get("gap_support") or operational_layer.get("autoMapGapSupport") or {},
                "source_priority": recipe_layer.get("source_priority") or operational_layer.get("autoMapSourcePriority"),
                "geometry_type": recipe_layer.get("geometry_type"),
                "definition_expression": _definition_expression(operational_layer),
                "opacity": operational_layer.get("opacity"),
                "visibility": operational_layer.get("visibility"),
                "confidence_score": recipe_layer.get("confidence_score") or operational_layer.get("autoMapConfidence"),
                "match_reasons": recipe_layer.get("match_reasons") or [],
                "needs_review": bool(operational_layer.get("autoMapNeedsReview")),
                "is_legacy": str(source_status).startswith("legacy"),
                "is_historical": source_status == "legacy_historical"
                or bool(recipe_layer.get("is_historical")),
            }
        )
    return rows


def build_warning_report(recipe: dict[str, Any], webmap_json: dict[str, Any]) -> dict[str, list[str]]:
    """Group recipe and WebMap warnings for human review."""
    layer_selection_warnings: list[str] = []
    filter_warnings: list[str] = []
    symbology_warnings: list[str] = []
    missing_data_warnings: list[str] = []
    source_coverage_warnings: list[str] = []
    historical_data_warnings: list[str] = []

    for warning in _as_list(recipe.get("review_reasons")):
        lowered = str(warning).lower()
        if "missing" in lowered and "data" in lowered:
            missing_data_warnings.append(str(warning))
        elif "filter" in lowered or "field" in lowered or "zoning" in lowered or "proximity" in lowered or "recent" in lowered:
            filter_warnings.append(str(warning))
        else:
            layer_selection_warnings.append(str(warning))

    for missing in _as_list(recipe.get("missing_data_needed")):
        missing_text = str(missing).lower()
        if not any(missing_text in warning.lower() for warning in missing_data_warnings):
            missing_data_warnings.append(f"Missing requested data: {missing}")

    for warning in _as_list((recipe.get("source_coverage") or {}).get("warnings")):
        source_coverage_warnings.append(str(warning))

    for layer_key, plan in (recipe.get("filter_plan") or {}).items():
        if plan.get("needs_review"):
            reason = plan.get("review_reason") or "Filter plan needs review."
            filter_warnings.append(f"{layer_key}: {reason}")

    for operational_layer in webmap_json.get("operationalLayers") or []:
        title = operational_layer.get("title") or operational_layer.get("autoMapLayerKey") or "Layer"
        for warning in _as_list(operational_layer.get("autoMapReviewWarnings")):
            text = f"{title}: {warning}"
            lowered = text.lower()
            if "renderer" in lowered or "symbol" in lowered or "styling" in lowered:
                symbology_warnings.append(text)
            elif "filter" in lowered or "field" in lowered or "zoning" in lowered:
                filter_warnings.append(text)
            elif "proxy" in lowered or "coverage" in lowered or "reference/context" in lowered:
                source_coverage_warnings.append(text)
            else:
                layer_selection_warnings.append(text)

    historical_year = recipe.get("parsed_request", {}).get("historical_year")
    for layer in recipe.get("selected_layers") or []:
        source_status = str(layer.get("source_status") or "")
        if source_status == "legacy_historical" or layer.get("is_historical"):
            if historical_year:
                historical_data_warnings.append(
                    f"Historical layer selected because user requested {historical_year}: {layer.get('layer_name')}"
                )
            else:
                historical_data_warnings.append(
                    f"Historical layer selected and needs review: {layer.get('layer_name')}"
                )

    webmap_validation = webmap_json.get("autoMapValidation") or validate_webmap_json(webmap_json)
    publishing_blockers = [
        "No ArcGIS item was published.",
        "No ArcGIS login is required for this local review packet.",
        "Review and approval are required before any future publishing step.",
    ]
    for error in webmap_validation.get("errors", []):
        publishing_blockers.append(f"WebMap validation error: {error}")

    return {
        "layer_selection_warnings": _dedupe(layer_selection_warnings),
        "filter_warnings": _dedupe(filter_warnings),
        "symbology_warnings": _dedupe(symbology_warnings),
        "missing_data_warnings": _dedupe(missing_data_warnings),
        "source_coverage_warnings": _dedupe(source_coverage_warnings),
        "historical_data_warnings": _dedupe(historical_data_warnings),
        "publishing_blockers": _dedupe(publishing_blockers),
    }


def build_review_summary(recipe: dict[str, Any], webmap_json: dict[str, Any]) -> str:
    """Build the Markdown review summary for a packet."""
    layer_rows = build_layer_review_table(recipe, webmap_json)
    warning_report = build_warning_report(recipe, webmap_json)
    lines = [
        f"# {recipe.get('map_title') or webmap_json.get('title') or 'AutoMap Draft'}",
        "",
        "This is a draft review packet and not an official map.",
        "",
        "## Original User Prompt",
        "",
        str(recipe.get("user_intent") or recipe.get("parsed_request", {}).get("raw_prompt") or ""),
        "",
        "## Selected Layers",
        "",
    ]
    if layer_rows:
        lines.append("| Layer | Role | Source Status | URL |")
        lines.append("| --- | --- | --- | --- |")
        for row in layer_rows:
            title = row.get("title") or row.get("layer_key") or "Layer"
            url = row.get("layer_url") or ""
            lines.append(
                f"| {title} | {row.get('role') or ''} | {row.get('source_status') or ''} | {url} |"
            )
    else:
        lines.append("No layers were selected.")

    lines.extend(
        [
            "",
            "## Source Preference",
            "",
            _new_opendata_preference_statement(recipe),
            "",
            "## Source Coverage",
            "",
        ]
    )
    source_coverage = recipe.get("source_coverage") or {}
    coverage_rows = []
    for group_name in ["official_sources", "proxy_sources", "limited_coverage_sources", "reference_sources", "missing_official_sources"]:
        for item in source_coverage.get(group_name) or []:
            coverage_rows.append((group_name, item))
    if coverage_rows:
        lines.append("| Type | Source | Role/Status | Coverage | Limitation |")
        lines.append("| --- | --- | --- | --- | --- |")
        for group_name, item in coverage_rows:
            title = item.get("display_title") or item.get("layer_name") or item.get("gap_key") or "Source"
            role = item.get("source_role") or item.get("status") or ""
            coverage = item.get("coverage_geography") or ""
            limitation = item.get("limitation") or item.get("reason") or ""
            lines.append(f"| {group_name.replace('_', ' ')} | {title} | {role} | {coverage} | {limitation} |")
    else:
        lines.append("No source coverage metadata was recorded.")

    lines.extend(
        [
            "",
            "## Filters And Definition Expressions",
            "",
        ]
    )
    expressions = [row for row in layer_rows if row.get("definition_expression")]
    if expressions:
        lines.append("| Layer | Definition Expression |")
        lines.append("| --- | --- |")
        for row in expressions:
            lines.append(f"| {row.get('title')} | `{row.get('definition_expression')}` |")
    else:
        lines.append("No definition expressions were drafted.")

    lines.extend(["", "## Spatial Operations", ""])
    for operation in recipe.get("spatial_operations") or []:
        lines.append(f"- {operation.get('operation')}: {operation.get('notes') or operation.get('output') or ''}")
    if not recipe.get("spatial_operations"):
        lines.append("No spatial operations were drafted.")

    lines.extend(
        [
            "",
            "## Suggested Extent",
            "",
            json.dumps(recipe.get("suggested_extent") or {}, indent=2, default=str),
            "",
            "## Confidence",
            "",
            f"Confidence score: {recipe.get('confidence_score')}",
            f"Needs review: {recipe.get('needs_review')}",
            "",
            "## Warnings",
            "",
        ]
    )
    any_warnings = False
    for group_name, warnings in warning_report.items():
        if not warnings:
            continue
        any_warnings = True
        lines.append(f"### {group_name.replace('_', ' ').title()}")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")
    if not any_warnings:
        lines.append("No warnings were generated.")

    lines.extend(["## Missing Data Needed", ""])
    missing_data = recipe.get("missing_data_needed") or []
    if missing_data:
        lines.extend(f"- {item}" for item in missing_data)
    else:
        lines.append("No missing data was reported.")

    lines.extend(["", "## Data Gaps Recorded", ""])
    if missing_data:
        lines.extend(f"- {item}" for item in missing_data)
    else:
        lines.append("No data gaps were recorded for this request.")

    return "\n".join(lines).strip() + "\n"


def _render_warning_group_html(title: str, warnings: list[str]) -> str:
    if not warnings:
        return f"<section><h3>{escape(title)}</h3><p>None.</p></section>"
    items = "".join(f"<li>{escape(warning)}</li>" for warning in warnings)
    return f"<section><h3>{escape(title)}</h3><ul>{items}</ul></section>"


def _build_review_html(
    recipe: dict[str, Any],
    webmap_json: dict[str, Any],
    warnings: dict[str, list[str]],
    layer_review: list[dict[str, Any]],
) -> str:
    title = recipe.get("map_title") or webmap_json.get("title") or "AutoMap Draft"
    prompt = recipe.get("user_intent") or recipe.get("parsed_request", {}).get("raw_prompt") or ""
    layer_rows = []
    for row in layer_review:
        url = row.get("layer_url") or ""
        link = f'<a href="{escape(url)}" target="_blank" rel="noreferrer">{escape(url)}</a>' if url else ""
        layer_rows.append(
            "<tr>"
            f"<td>{escape(str(row.get('title') or ''))}</td>"
            f"<td>{escape(str(row.get('role') or ''))}</td>"
            f"<td>{escape(str(row.get('source_status') or ''))}</td>"
            f"<td>{escape(str(row.get('source_role') or ''))}</td>"
            f"<td>{escape(str(row.get('coverage_geography') or ''))}</td>"
            f"<td>{escape(str(row.get('confidence_score') or ''))}</td>"
            f"<td>{link}</td>"
            "</tr>"
        )

    filter_rows = []
    for row in layer_review:
        expression = row.get("definition_expression")
        if expression:
            filter_rows.append(
                "<tr>"
                f"<td>{escape(str(row.get('title') or ''))}</td>"
                f"<td><code>{escape(expression)}</code></td>"
                "</tr>"
            )
    missing_data = recipe.get("missing_data_needed") or []
    raw_webmap = json.dumps(webmap_json, indent=2, default=str)
    warning_html = "".join(
        _render_warning_group_html(group_name.replace("_", " ").title(), group_warnings)
        for group_name, group_warnings in warnings.items()
    )
    coverage_rows = []
    for group_name in ["official_sources", "proxy_sources", "limited_coverage_sources", "reference_sources", "missing_official_sources"]:
        for item in (recipe.get("source_coverage") or {}).get(group_name) or []:
            coverage_rows.append(
                "<tr>"
                f"<td>{escape(group_name.replace('_', ' '))}</td>"
                f"<td>{escape(str(item.get('display_title') or item.get('layer_name') or item.get('gap_key') or ''))}</td>"
                f"<td>{escape(str(item.get('source_role') or item.get('status') or ''))}</td>"
                f"<td>{escape(str(item.get('coverage_geography') or ''))}</td>"
                f"<td>{escape(str(item.get('limitation') or item.get('reason') or ''))}</td>"
                "</tr>"
            )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(title))} - AutoMap Review</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --text: #17202a;
      --muted: #5f6b7a;
      --line: #d8dde6;
      --panel: #ffffff;
      --accent: #1f6feb;
    }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--bg);
      color: var(--text);
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
    h1, h2, h3 {{
      margin: 0 0 10px;
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
    code, pre {{
      background: #eef2f7;
      border-radius: 6px;
      padding: 2px 4px;
    }}
    pre {{
      max-height: 520px;
      overflow: auto;
      padding: 12px;
    }}
    a {{
      color: var(--accent);
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(str(title))}</h1>
      <p><strong>Original prompt:</strong> {escape(str(prompt))}</p>
      <p>This is a local draft review packet and not an official map.</p>
    </header>
    <section>
      <h2>Selected Layers</h2>
      <table>
        <thead><tr><th>Layer</th><th>Role</th><th>Source</th><th>Usage</th><th>Coverage</th><th>Confidence</th><th>REST URL</th></tr></thead>
        <tbody>{''.join(layer_rows) or '<tr><td colspan="7">No layers selected.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Source Coverage</h2>
      <table>
        <thead><tr><th>Type</th><th>Source</th><th>Role/Status</th><th>Coverage</th><th>Limitation</th></tr></thead>
        <tbody>{''.join(coverage_rows) or '<tr><td colspan="5">No source coverage metadata recorded.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Filters And Definition Expressions</h2>
      <table>
        <thead><tr><th>Layer</th><th>Expression</th></tr></thead>
        <tbody>{''.join(filter_rows) or '<tr><td colspan="2">No definition expressions drafted.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Warnings</h2>
      {warning_html}
    </section>
    <section>
      <h2>Missing Data</h2>
      {'<ul>' + ''.join(f'<li>{escape(str(item))}</li>' for item in missing_data) + '</ul>' if missing_data else '<p>No missing data was reported.</p>'}
    </section>
    <section>
      <h2>Draft WebMap JSON</h2>
      <details>
        <summary>Show raw WebMap JSON</summary>
        <pre>{escape(raw_webmap)}</pre>
      </details>
    </section>
  </main>
</body>
</html>
"""


def build_review_packet(prompt: str) -> dict[str, Any]:
    """Build a complete local review packet payload without saving it."""
    recipe = build_recipe(prompt)
    webmap_json = build_webmap_json(recipe)
    warnings = build_warning_report(recipe, webmap_json)
    layer_review = build_layer_review_table(recipe, webmap_json)
    summary = build_review_summary(recipe, webmap_json)
    review_html = _build_review_html(recipe, webmap_json, warnings, layer_review)
    return {
        "prompt": prompt,
        "recipe": recipe,
        "webmap_json": webmap_json,
        "review_summary": summary,
        "warnings": warnings,
        "layer_review": layer_review,
        "review_html": review_html,
    }


def make_packet_folder_name(prompt: str) -> str:
    """Create a safe, readable review packet folder name stem."""
    return slugify(prompt)[:90] or "automap_review_packet"


def save_review_packet(
    prompt: str,
    recipe: dict[str, Any],
    webmap_json: dict[str, Any],
    output_dir: str | Path = "outputs/review_packets",
) -> Path:
    """Save a local review packet folder under outputs/review_packets."""
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    packet_path = root / f"{timestamp}_{make_packet_folder_name(prompt)}"
    packet_path.mkdir(parents=True, exist_ok=False)

    warnings = build_warning_report(recipe, webmap_json)
    layer_review = build_layer_review_table(recipe, webmap_json)
    summary = build_review_summary(recipe, webmap_json)
    review_html = _build_review_html(recipe, webmap_json, warnings, layer_review)

    (packet_path / "recipe.json").write_text(json.dumps(recipe, indent=2, default=str), encoding="utf-8")
    (packet_path / "webmap.json").write_text(json.dumps(webmap_json, indent=2, default=str), encoding="utf-8")
    (packet_path / "review_summary.md").write_text(summary, encoding="utf-8")
    (packet_path / "warnings.json").write_text(json.dumps(warnings, indent=2, default=str), encoding="utf-8")
    (packet_path / "layer_review.json").write_text(json.dumps(layer_review, indent=2, default=str), encoding="utf-8")
    (packet_path / "review.html").write_text(review_html, encoding="utf-8")

    return packet_path


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _packet_text(packet_path: Path) -> str:
    chunks: list[str] = []
    for file_name in REQUIRED_PACKET_FILES:
        path = packet_path / file_name
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks).lower()


def _contains_protected_output_marker(packet_path: Path) -> str | None:
    combined = _packet_text(packet_path)
    for marker in sorted(PROTECTED_OUTPUT_MARKERS):
        if marker in combined:
            return marker
    return None


def validate_review_packet(packet_folder: str | Path) -> dict[str, Any]:
    """Validate a local AutoMap review packet folder."""
    packet_path = Path(packet_folder)
    errors: list[str] = []
    warnings: list[str] = []

    if not packet_path.exists() or not packet_path.is_dir():
        return {
            "is_valid": False,
            "errors": [f"Review packet folder not found: {packet_path}"],
            "warnings": [],
            "packet_path": str(packet_path),
        }

    missing_files = sorted(file_name for file_name in REQUIRED_PACKET_FILES if not (packet_path / file_name).exists())
    if missing_files:
        errors.append(f"Missing required packet files: {', '.join(missing_files)}")

    recipe: dict[str, Any] = {}
    webmap_json: dict[str, Any] = {}
    warning_report: dict[str, Any] = {}
    if not missing_files:
        try:
            recipe = _load_json(packet_path / "recipe.json")
            webmap_json = _load_json(packet_path / "webmap.json")
            warning_report = _load_json(packet_path / "warnings.json")
            _load_json(packet_path / "layer_review.json")
        except json.JSONDecodeError as exc:
            errors.append(f"Packet JSON is invalid: {exc}")

    if webmap_json:
        webmap_validation = validate_webmap_json(webmap_json)
        errors.extend(webmap_validation.get("errors", []))
        warnings.extend(webmap_validation.get("warnings", []))
        if not webmap_json.get("operationalLayers"):
            errors.append("webmap.json has no operationalLayers.")
        for index, operational_layer in enumerate(webmap_json.get("operationalLayers") or []):
            if not operational_layer.get("title"):
                errors.append(f"Operational layer {index} is missing title.")
            if not operational_layer.get("url"):
                errors.append(f"Operational layer {operational_layer.get('title') or index} is missing URL.")

    source_warnings = [
        *[str(item) for item in _as_list(recipe.get("review_reasons"))],
        *[str(item) for item in _as_list(recipe.get("missing_data_needed"))],
    ]
    for operational_layer in webmap_json.get("operationalLayers") or []:
        source_warnings.extend(str(item) for item in _as_list(operational_layer.get("autoMapReviewWarnings")))
    if source_warnings:
        grouped_count = sum(
            len(_as_list(items))
            for group, items in warning_report.items()
            if group != "publishing_blockers"
        )
        if grouped_count == 0:
            errors.append("Warnings were not preserved in warnings.json.")

    missing_data = [str(item) for item in _as_list(recipe.get("missing_data_needed"))]
    if missing_data:
        missing_text = " ".join(str(item) for item in _as_list(warning_report.get("missing_data_warnings"))).lower()
        for item in missing_data:
            if item.lower() not in missing_text:
                errors.append(f"Missing data was not preserved in warnings.json: {item}")

    protected_marker = _contains_protected_output_marker(packet_path)
    if protected_marker:
        errors.append(f"Generated packet contains protected or secret marker: {protected_marker}")

    return {
        "is_valid": not errors,
        "errors": _dedupe(errors),
        "warnings": _dedupe(warnings),
        "packet_path": str(packet_path),
        "required_files_present": not missing_files,
        "operational_layer_count": len(webmap_json.get("operationalLayers") or []),
    }
