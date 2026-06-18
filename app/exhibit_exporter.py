"""Generate local county exhibit and staff-report map export packages."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any

from app.exhibit_models import ExhibitPackage, REQUIRED_EXHIBIT_FILES, SUPPORTED_EXHIBIT_TYPES
from app.layer_semantics import slugify
from app.report_section_models import build_report_sections
from app.report_statistics_builder import build_report_statistics
from app.ui_models import output_file_url, repo_root


OUTPUTS_ROOT = Path("outputs")
EXHIBITS_FOLDER = "exhibits"

PROTECTED_EXHIBIT_MARKERS = {
    ".env",
    "arcgis_password",
    "arcgis_username",
    "cfs",
    "cfs_dev",
    "database_url",
    "password",
    "postgres_admin_url",
    "secret",
    "token",
}

DRAFT_EXHIBIT_DISCLAIMER = (
    "Draft only - for GIS review. This exhibit is not an official county map, "
    "does not publish to ArcGIS, and does not create ArcGIS items."
)


def _outputs_root() -> Path:
    root = OUTPUTS_ROOT
    return root.resolve() if root.is_absolute() else (repo_root() / root).resolve()


def _exhibits_root() -> Path:
    return _outputs_root() / EXHIBITS_FOLDER


def _output_relative(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        try:
            return (Path("outputs") / resolved.relative_to(_outputs_root())).as_posix()
        except ValueError:
            return resolved.name


def _file_link(path: Path, name: str | None = None) -> dict[str, str]:
    relative = _output_relative(path)
    return {"name": name or path.name, "path": relative, "url": output_file_url(relative)}


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, dict):
        return [value]
    return [value]


def _map_state(session: dict[str, Any]) -> dict[str, Any]:
    state = session.get("composer_map_state")
    return state if isinstance(state, dict) else {}


def _state_preview(session: dict[str, Any]) -> dict[str, Any]:
    state = _map_state(session)
    preview = state.get("preview_config") or session.get("preview_config") or {}
    return preview if isinstance(preview, dict) else {}


def _has_protected_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PROTECTED_EXHIBIT_MARKERS)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        clean: dict[str, Any] = {}
        for key, item in value.items():
            if _has_protected_marker(str(key)):
                continue
            clean[str(key)] = _sanitize(item)
        return clean
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, str):
        return "[redacted]" if _has_protected_marker(value) else value
    return value


def _collect_strings(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        strings: list[str] = []
        for key, item in value.items():
            if isinstance(item, list):
                strings.extend(str(entry) for entry in item)
            elif isinstance(item, str):
                strings.append(f"{key}: {item}")
        return strings
    if isinstance(value, (list, tuple, set)):
        return [str(item) for item in value]
    return [str(value)]


def _dedupe(strings: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in strings:
        text = item.strip()
        if not text or text.lower() in seen:
            continue
        seen.add(text.lower())
        result.append(text)
    return result


def classify_exhibit_type(session: dict[str, Any]) -> str:
    """Choose a staff-report exhibit template from composer metadata."""
    request_type = str(session.get("request_type") or "").lower()
    title = str(session.get("map_title") or (session.get("map_layout") or {}).get("title") or "").lower()
    prompt = str(session.get("raw_prompt") or session.get("prompt") or "").lower()
    combined = f"{request_type} {title} {prompt}"
    if "proximity" in request_type or "nearest" in combined or "route" in combined:
        return "proximity_exhibit"
    if "parcel" in request_type or "parcel" in combined or "pin" in combined:
        return "parcel_context_exhibit"
    if "flood" in combined:
        return "flood_exposure_exhibit"
    if "zoning" in combined:
        return "zoning_context_exhibit"
    if "scenario" in request_type or "suitability" in combined:
        return "scenario_exhibit"
    return "general_reference_exhibit"


def _source_role(layer: dict[str, Any], *, derived: bool = False) -> str:
    if derived:
        return "derived local"
    status = str(layer.get("source_status") or layer.get("sourceStatus") or "").lower()
    role = str(layer.get("role") or layer.get("display_role") or "").lower()
    if "proxy" in status or "proxy" in role:
        return "proxy"
    if "reference" in status or "reference" in role:
        return "reference"
    if status in {"active", "approved", "verified"}:
        return "official"
    return "reference"


def _layer_limitations(layer: dict[str, Any], *, derived: bool = False) -> str:
    if derived:
        return str(layer.get("route_warning") or layer.get("limitation") or "Local derived output; not uploaded or published.")
    warnings = layer.get("review_warnings") or layer.get("warnings") or []
    if isinstance(warnings, str):
        return warnings
    if warnings:
        return "; ".join(str(item) for item in _as_list(warnings))
    if layer.get("definition_expression"):
        return f"Filtered with definition expression: {layer.get('definition_expression')}"
    return str(layer.get("known_limitations") or layer.get("limitations") or "Review source currency and symbology before official use.")


def build_layer_source_rows(session: dict[str, Any]) -> list[dict[str, str]]:
    """Build a professional source table for exhibit outputs."""
    preview = _state_preview(session)
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    for overlay in _as_list(preview.get("derived_overlays")):
        if not isinstance(overlay, dict):
            continue
        title = str(overlay.get("title") or overlay.get("id") or "Local derived output")
        key = f"derived::{title}::{overlay.get('path') or overlay.get('url')}"
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "Display name": title,
                "Source layer": str(overlay.get("role") or overlay.get("geometry_role") or "Derived local output"),
                "Source status": "derived local",
                "Official / proxy / reference / derived local": "derived local",
                "REST URL or local output note": str(overlay.get("path") or overlay.get("url") or "Local derived output"),
                "Limitations": _layer_limitations(overlay, derived=True),
            }
        )

    context_layers = _as_list(preview.get("context_layers") or preview.get("operational_layers") or session.get("selected_layers"))
    for layer in context_layers:
        if not isinstance(layer, dict):
            continue
        title = str(layer.get("title") or layer.get("layer_name") or layer.get("layer_key") or "Context layer")
        source = str(layer.get("layer_key") or layer.get("id") or title)
        url = str(layer.get("layer_url") or layer.get("url") or layer.get("service_url") or "Layer catalog record")
        key = f"{source}::{url}"
        if key in seen:
            continue
        seen.add(key)
        source_status = str(layer.get("source_status") or layer.get("approval_status") or "reference")
        rows.append(
            {
                "Display name": title,
                "Source layer": source,
                "Source status": source_status,
                "Official / proxy / reference / derived local": _source_role(layer),
                "REST URL or local output note": url,
                "Limitations": _layer_limitations(layer),
            }
        )

    if not rows:
        rows.append(
            {
                "Display name": "No preview layers recorded",
                "Source layer": "Not available",
                "Source status": "needs_review",
                "Official / proxy / reference / derived local": "reference",
                "REST URL or local output note": "No source layer table available",
                "Limitations": "Generate a preview-ready composer session before exhibit export.",
            }
        )
    return rows


def build_warning_summary(session: dict[str, Any]) -> list[str]:
    state = _map_state(session)
    preview = _state_preview(session)
    proximity = state.get("proximity_summary") or session.get("proximity_result") or preview.get("proximity_result") or {}
    warnings: list[str] = []
    warnings.extend(_collect_strings(state.get("warnings") or session.get("warnings")))
    warnings.extend(_collect_strings(session.get("preview_blockers")))
    warnings.extend(f"Missing data: {item}" for item in _as_list(session.get("missing_data")))
    warnings.extend(_collect_strings(preview.get("warnings")))
    warnings.extend(_collect_strings(proximity.get("warnings") if isinstance(proximity, dict) else []))
    if isinstance(proximity, dict) and proximity.get("route_warning"):
        warnings.append(str(proximity["route_warning"]))
    if isinstance(proximity, dict) and proximity.get("property_match_status") == "not_resolved":
        warnings.append("Related parcel was not resolved from verified address/parcel fields.")
    warnings.append("Draft only - not an official county map.")
    warnings.append("No ArcGIS item was published or uploaded.")
    return _dedupe([str(item) for item in warnings])


def _key_findings(session: dict[str, Any]) -> list[dict[str, str]]:
    proximity = session.get("proximity_result") or {}
    findings: list[dict[str, str]] = []
    if isinstance(proximity, dict) and proximity:
        findings.extend(
            [
                {"label": "Origin", "value": str(proximity.get("origin_input") or session.get("origin_type") or "Not recorded")},
                {"label": "Nearest target", "value": str(proximity.get("target_name") or proximity.get("target_type") or "Not recorded")},
                {
                    "label": "Distance",
                    "value": (
                        f"{float(proximity['distance_value']):.2f} {proximity.get('distance_unit') or 'miles'}"
                        if isinstance(proximity.get("distance_value"), (int, float))
                        else "Not calculated"
                    ),
                },
                {"label": "Route mode", "value": str(proximity.get("route_label") or proximity.get("route_mode") or "Not a route map")},
                {"label": "Related parcel", "value": str(proximity.get("property_match_status") or "Not applicable")},
            ]
        )
    else:
        findings.extend(
            [
                {"label": "Map type", "value": classify_exhibit_type(session).replace("_", " ")},
                {"label": "Preview", "value": "Ready" if session.get("can_preview") else "Needs review"},
                {"label": "Selected layers", "value": str(len(session.get("selected_layers") or []))},
            ]
        )
    return findings


def _title_block(session: dict[str, Any], exhibit_type: str, created_at: str) -> dict[str, Any]:
    state = _map_state(session)
    preview = _state_preview(session)
    layout = preview.get("map_layout") or session.get("map_layout") or {}
    return {
        "title": state.get("map_title") or layout.get("title") or preview.get("map_title") or session.get("map_title") or "AutoMap Draft Exhibit",
        "subtitle": state.get("map_subtitle") or layout.get("subtitle") or "Draft preview only.",
        "original_prompt": state.get("raw_prompt") or session.get("raw_prompt") or session.get("prompt") or preview.get("original_prompt") or "",
        "prepared_by": "AutoMap Draft",
        "generated_at": created_at,
        "draft_status": "DRAFT - For GIS review only",
        "map_type": exhibit_type,
        "request_type": session.get("request_type") or "general_map",
        "workflow_session_id": session.get("composer_session_id") or session.get("workflow_id") or "",
    }


def _html_list(items: list[str]) -> str:
    return "\n".join(f"<li>{escape(item)}</li>" for item in items) or "<li>No warnings recorded.</li>"


def _render_layer_rows(rows: list[dict[str, str]]) -> str:
    cells = []
    for row in rows:
        cells.append(
            "<tr>"
            f"<td>{escape(row['Display name'])}</td>"
            f"<td>{escape(row['Source layer'])}</td>"
            f"<td>{escape(row['Source status'])}</td>"
            f"<td>{escape(row['Official / proxy / reference / derived local'])}</td>"
            f"<td>{escape(row['REST URL or local output note'])}</td>"
            f"<td>{escape(row['Limitations'])}</td>"
            "</tr>"
        )
    return "\n".join(cells)


def _render_key_findings(findings: list[dict[str, str]]) -> str:
    return "\n".join(
        f"<div><dt>{escape(item['label'])}</dt><dd>{escape(item['value'])}</dd></div>" for item in findings
    )


def _render_html(data: dict[str, Any], layer_rows: list[dict[str, str]], warnings: list[str]) -> str:
    title = data["title_block"]
    findings = data.get("key_findings") or []
    export_options = data.get("export_options") if isinstance(data.get("export_options"), dict) else {}
    export_mode = str(data.get("export_mode") or export_options.get("export_mode") or "map_exhibit_only")
    include_appendix = bool(export_options.get("include_appendix") or export_mode == "full_report")
    include_layer_table = include_appendix or export_mode == "full_report"
    warning_items = warnings if include_appendix else warnings[:4]
    layer_section = (
        f"""
    <section class="appendix">
      <h2>Layer Source Table</h2>
      <table>
        <thead><tr><th>Display name</th><th>Source layer</th><th>Status</th><th>Role</th><th>REST URL or local output note</th><th>Limitations</th></tr></thead>
        <tbody>{_render_layer_rows(layer_rows)}</tbody>
      </table>
    </section>"""
        if include_layer_table
        else ""
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{escape(title['title'])}</title>
  <style>
    body {{ margin: 0; background: #eef2f6; color: #172033; font-family: Arial, sans-serif; }}
    main {{ max-width: 1120px; margin: 24px auto; background: white; border: 1px solid #cbd5e1; box-shadow: 0 18px 45px rgba(15, 23, 42, .16); }}
    header {{ display: grid; grid-template-columns: 1fr auto; gap: 18px; border-bottom: 4px solid #203a56; padding: 22px 26px; }}
    h1 {{ margin: 0; font-size: 28px; color: #10233b; }}
    h2 {{ margin: 0 0 10px; color: #203a56; }}
    p {{ line-height: 1.45; }}
    .subtitle {{ margin: 6px 0 0; color: #475467; font-weight: 700; }}
    .badge {{ align-self: start; border: 2px solid #9a3412; border-radius: 999px; color: #9a3412; font-weight: 900; padding: 8px 12px; }}
    .meta {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 14px 26px; border-bottom: 1px solid #d8e0ea; background: #f8fafc; }}
    .meta div, .finding div {{ border-left: 3px solid #8eb8e0; padding-left: 10px; }}
    dt {{ color: #667085; font-size: 11px; font-weight: 800; text-transform: uppercase; }}
    dd {{ margin: 2px 0 0; font-weight: 800; }}
    section {{ padding: 22px 26px; border-bottom: 1px solid #d8e0ea; }}
    .map-frame {{ min-height: 520px; display: grid; place-items: center; border: 2px solid #203a56; background: linear-gradient(135deg, #eef5fb, #f9fbfd); color: #344054; text-align: center; }}
    .map-frame strong {{ display: block; margin-bottom: 8px; color: #10233b; font-size: 18px; }}
    .finding {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 10px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border: 1px solid #d8e0ea; padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; color: #203a56; }}
    .appendix {{ break-before: page; }}
    footer {{ padding: 18px 26px; color: #475467; font-size: 12px; }}
    @media print {{ body {{ background: white; }} main {{ margin: 0; border: 0; box-shadow: none; }} .map-frame {{ min-height: 430px; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{escape(title['title'])}</h1>
        <p class="subtitle">{escape(title['subtitle'])}</p>
        <p>{escape(title['original_prompt'])}</p>
      </div>
      <div class="badge">{escape(title['draft_status'])}</div>
    </header>
    <div class="meta">
      <div><dt>Prepared by</dt><dd>{escape(title['prepared_by'])}</dd></div>
      <div><dt>Generated</dt><dd>{escape(title['generated_at'])}</dd></div>
      <div><dt>Map type</dt><dd>{escape(title['map_type'].replace('_', ' ').title())}</dd></div>
      <div><dt>Session</dt><dd>{escape(str(title['workflow_session_id']) or 'Not recorded')}</dd></div>
    </div>
    <section>
      <div class="map-frame">
        <div>
          <strong>Exhibit map frame</strong>
          <p>This local package records the exhibit metadata and source table. Open the AutoMap print layout for the live basemap, legend, scale bar, and north arrow.</p>
        </div>
      </div>
    </section>
    <section>
      <h2>Key Findings / Map Notes</h2>
      <dl class="finding">{_render_key_findings(findings)}</dl>
    </section>
    {layer_section}
    <section>
      <h2>Warnings and Limitations</h2>
      <ul>{_html_list(warning_items)}</ul>
    </section>
    <footer>
      {escape(DRAFT_EXHIBIT_DISCLAIMER)} Local derived outputs stay on this machine and are not uploaded.
    </footer>
  </main>
</body>
</html>
"""


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "Display name",
        "Source layer",
        "Source status",
        "Official / proxy / reference / derived local",
        "REST URL or local output note",
        "Limitations",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _validate_package(folder: Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    for file_name in REQUIRED_EXHIBIT_FILES:
        if not (folder / file_name).exists():
            errors.append(f"Missing required file: {file_name}")
    for file_path in folder.glob("*"):
        if not file_path.is_file():
            continue
        try:
            text = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if _has_protected_marker(text):
            errors.append(f"Protected marker found in {file_path.name}")
    return {"is_valid": not errors, "errors": errors, "warnings": warnings}


def _manifest_files(folder: Path) -> list[dict[str, str]]:
    return [_file_link(folder / file_name, file_name) for file_name in REQUIRED_EXHIBIT_FILES if (folder / file_name).exists()]


def generate_exhibit_package_from_session(session: dict[str, Any], *, mode: str | None = None) -> ExhibitPackage:
    """Write a local exhibit package for a preview-ready map composer session."""
    if not session or not session.get("composer_session_id"):
        raise ValueError("A composer session id is required to generate an exhibit package.")
    if session.get("can_preview") is False:
        raise ValueError("Exhibit package generation requires a preview-ready composer session.")

    created_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    exhibit_type = mode or classify_exhibit_type(session)
    if exhibit_type not in SUPPORTED_EXHIBIT_TYPES:
        exhibit_type = "general_reference_exhibit"
    title_block = _title_block(session, exhibit_type, created_at)
    slug = slugify(str(title_block["title"]))[:80] or "automap-exhibit"
    timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    exhibit_id = f"exhibit_{timestamp}_{slug}"
    folder = _exhibits_root() / f"{timestamp}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)

    layer_rows = build_layer_source_rows(session)
    warning_summary = build_warning_summary(session)
    map_state = _map_state(session)
    export_options = map_state.get("export_options") if isinstance(map_state.get("export_options"), dict) else {}
    export_mode = str(map_state.get("export_mode") or export_options.get("export_mode") or "map_exhibit_only")
    statistics = build_report_statistics(map_state or session)
    report_sections = build_report_sections(map_state or session, statistics, (map_state or {}).get("report_section_config"))
    data = _sanitize(
        {
            "exhibit_id": exhibit_id,
            "title_block": title_block,
            "exhibit_type": exhibit_type,
            "source_prompt": session.get("raw_prompt") or session.get("prompt"),
            "composer_session_id": session.get("composer_session_id"),
            "request_type": session.get("request_type"),
            "map_layout": map_state.get("preview_config", {}).get("map_layout") if map_state else session.get("map_layout") or {},
            "preview_config": map_state.get("preview_config") if map_state else session.get("preview_config") or {},
            "map_state_json": map_state,
            "export_mode": export_mode,
            "export_options": export_options,
            "report_sections": report_sections,
            "statistics_sections": statistics,
            "key_findings": _key_findings(session),
            "layer_sources": layer_rows,
            "warnings": warning_summary,
            "draft_disclaimer": DRAFT_EXHIBIT_DISCLAIMER,
            "published": False,
        }
    )

    (folder / "exhibit_data.json").write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    (folder / "composer_map_state.json").write_text(json.dumps(_sanitize(map_state), indent=2, default=str), encoding="utf-8")
    (folder / "report_sections.json").write_text(json.dumps(_sanitize(report_sections), indent=2, default=str), encoding="utf-8")
    _write_csv(folder / "layer_sources.csv", _sanitize(layer_rows))
    (folder / "warnings.json").write_text(json.dumps(_sanitize({"warnings": warning_summary}), indent=2), encoding="utf-8")
    (folder / "exhibit.html").write_text(_render_html(data, _sanitize(layer_rows), _sanitize(warning_summary)), encoding="utf-8")

    manifest = _sanitize(
        {
            "exhibit_id": exhibit_id,
            "exhibit_title": title_block["title"],
            "exhibit_type": exhibit_type,
            "created_at": created_at,
            "exhibit_folder": _output_relative(folder),
            "files": _manifest_files(folder),
            "supported_formats": ["html", "json", "csv"],
            "pdf_export": "Use the browser print-to-PDF workflow from the AutoMap print layout.",
            "draft_only": True,
            "published": False,
        }
    )
    (folder / "export_manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    validation = _validate_package(folder)
    summary = {
        "title": title_block["title"],
        "subtitle": title_block["subtitle"],
        "prompt": title_block["original_prompt"],
        "created_at": created_at,
        "map_type": exhibit_type,
        "warning_count": len(warning_summary),
        "layer_count": len(layer_rows),
        "draft_status": title_block["draft_status"],
    }
    return ExhibitPackage(
        exhibit_id=exhibit_id,
        exhibit_folder=folder,
        exhibit_title=str(title_block["title"]),
        exhibit_type=exhibit_type,
        files=_manifest_files(folder),
        validation=validation,
        summary=summary,
    )


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _find_exhibit_folder(exhibit_id: str) -> Path:
    root = _exhibits_root()
    if not root.exists():
        raise FileNotFoundError(f"Exhibit not found: {exhibit_id}")
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        manifest_path = folder / "export_manifest.json"
        data_path = folder / "exhibit_data.json"
        try:
            manifest = _load_json(manifest_path) if manifest_path.exists() else {}
            data = _load_json(data_path) if data_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            continue
        if manifest.get("exhibit_id") == exhibit_id or data.get("exhibit_id") == exhibit_id or folder.name == exhibit_id:
            return folder
    raise FileNotFoundError(f"Exhibit not found: {exhibit_id}")


def list_exhibits() -> list[dict[str, Any]]:
    root = _exhibits_root()
    if not root.exists():
        return []
    exhibits: list[dict[str, Any]] = []
    for folder in root.iterdir():
        if not folder.is_dir():
            continue
        manifest_path = folder / "export_manifest.json"
        data_path = folder / "exhibit_data.json"
        try:
            manifest = _load_json(manifest_path) if manifest_path.exists() else {}
            data = _load_json(data_path) if data_path.exists() else {}
        except (OSError, json.JSONDecodeError):
            continue
        title_block = data.get("title_block") or {}
        exhibits.append(
            _sanitize(
                {
                    "exhibit_id": manifest.get("exhibit_id") or data.get("exhibit_id") or folder.name,
                    "exhibit_title": manifest.get("exhibit_title") or title_block.get("title") or folder.name,
                    "exhibit_type": manifest.get("exhibit_type") or data.get("exhibit_type") or "general_reference_exhibit",
                    "created_at": manifest.get("created_at") or title_block.get("generated_at"),
                    "source_prompt": data.get("source_prompt") or title_block.get("original_prompt"),
                    "exhibit_folder": _output_relative(folder),
                    "files": manifest.get("files") or _manifest_files(folder),
                    "draft_only": True,
                    "published": False,
                }
            )
        )
    return sorted(exhibits, key=lambda item: str(item.get("created_at") or ""), reverse=True)


def get_exhibit(exhibit_id: str) -> dict[str, Any]:
    folder = _find_exhibit_folder(exhibit_id)
    data = _load_json(folder / "exhibit_data.json")
    manifest = _load_json(folder / "export_manifest.json")
    return _sanitize(
        {
            "exhibit_id": exhibit_id,
            "exhibit_folder": _output_relative(folder),
            "exhibit_data": data,
            "manifest": manifest,
            "files": manifest.get("files") or _manifest_files(folder),
            "validation": _validate_package(folder),
            "draft_only": True,
            "published": False,
        }
    )


def get_exhibit_html(exhibit_id: str) -> str:
    folder = _find_exhibit_folder(exhibit_id)
    html_path = folder / "exhibit.html"
    if not html_path.exists():
        raise FileNotFoundError(f"Exhibit HTML not found: {exhibit_id}")
    return html_path.read_text(encoding="utf-8")
