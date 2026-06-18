"""Write local table export packages under ignored outputs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.layer_semantics import slugify
from app.table_request_models import utc_now
from app.ui_models import output_file_url, repo_root


TABLE_OUTPUT_ROOT = Path("outputs/tables")


def _root() -> Path:
    root = repo_root() / TABLE_OUTPUT_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def _file_link(path: Path) -> dict[str, str]:
    try:
        relative = path.resolve().relative_to(repo_root().resolve()).as_posix()
        url = output_file_url(relative)
    except ValueError:
        relative = path.resolve().as_posix()
        url = ""
    return {"name": path.name, "path": relative, "url": url}


def _folder_for(table_recipe: dict[str, Any]) -> Path:
    slug = slugify(str(table_recipe.get("table_title") or "table_export"))[:80] or "table_export"
    folder = _root() / f"{utc_now().replace(':', '').replace('-', '')}_{slug}"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def export_csv(table_result: dict[str, Any], folder: Path) -> Path:
    path = folder / "table_export.csv"
    fields = [field.get("name") for field in table_result.get("selected_fields") or [] if field.get("name")]
    rows = table_result.get("rows") or []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields or ["status"])
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in (fields or ["status"])})
    return path


def export_json(table_result: dict[str, Any], folder: Path) -> Path:
    path = folder / "table_export.json"
    path.write_text(json.dumps(table_result, indent=2, default=str), encoding="utf-8")
    return path


def export_markdown_summary(table_result: dict[str, Any], folder: Path) -> Path:
    path = folder / "table_summary.md"
    recipe = table_result.get("table_recipe") or table_result
    lines = [
        f"# {recipe.get('table_title') or 'AutoMap Table Export'}",
        "",
        f"Prompt: {recipe.get('raw_prompt') or ''}",
        f"Safety status: {recipe.get('safety_status')}",
        f"Estimated rows: {recipe.get('estimated_count')}",
        f"Exported rows: {len(table_result.get('rows') or [])}",
        "",
        "## Warnings",
        *(f"- {warning}" for warning in recipe.get("warnings") or ["No warnings recorded."]),
        "",
        "Draft table export. Local only. No ArcGIS item was published.",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def export_manifest(table_result: dict[str, Any], folder: Path, files: list[Path]) -> Path:
    path = folder / "export_manifest.json"
    try:
        output_folder = folder.resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        output_folder = folder.resolve().as_posix()
    manifest = {
        "table_request_id": table_result.get("table_request_id"),
        "export_id": table_result.get("export_id"),
        "created_at": utc_now(),
        "output_folder": output_folder,
        "files": [_file_link(file) for file in files],
        "formats": ["csv", "json", "markdown"],
        "returnGeometry": False,
        "draft_only": True,
        "published": False,
    }
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path


def write_table_export_package(table_result: dict[str, Any]) -> dict[str, Any]:
    folder = _folder_for(table_result.get("table_recipe") or table_result)
    preview_path = folder / "table_preview.json"
    preview_path.write_text(json.dumps({"rows": table_result.get("preview_rows") or []}, indent=2, default=str), encoding="utf-8")
    csv_path = export_csv(table_result, folder)
    json_path = export_json(table_result, folder)
    md_path = export_markdown_summary(table_result, folder)
    manifest_path = export_manifest(table_result, folder, [preview_path, csv_path, json_path, md_path])
    files = [_file_link(path) for path in [preview_path, csv_path, json_path, md_path, manifest_path]]
    try:
        output_folder = folder.resolve().relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        output_folder = folder.resolve().as_posix()
    return {"output_folder": output_folder, "files": files}
