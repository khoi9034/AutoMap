"""Simple prompt-to-preview composer workflow for AutoMap."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import csv
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.adjustment_engine import apply_adjustments_to_recipe, apply_adjustments_to_webmap, write_adjusted_packet
from app.adjustment_models import normalize_adjustments
from app.packet_index import build_preview_config
from app.recipe_engine import PARCEL_NOT_MATCHED_WARNING, build_recipe
from app.report_generator import generate_report
from app.review_packet_builder import (
    build_layer_review_table,
    build_review_summary,
    build_warning_report,
    save_review_packet,
)
from app.ui_models import output_file_url, repo_root
from app.webmap_builder import build_webmap_json


COMPOSER_ROOT = Path("outputs/composer_sessions")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _session_root() -> Path:
    root = repo_root() / COMPOSER_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def _session_path(session_id: str) -> Path:
    if not session_id.startswith("composer_"):
        raise ValueError("Invalid composer session id.")
    path = (_session_root() / session_id).resolve()
    try:
        path.relative_to(_session_root().resolve())
    except ValueError as exc:
        raise ValueError("Composer session path must stay inside AutoMap outputs.") from exc
    return path


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _repo_relative(path: str | Path | None) -> str | None:
    if not path:
        return None
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _file_link(path: str | Path, name: str | None = None) -> dict[str, str]:
    relative = _repo_relative(path) or Path(path).as_posix()
    return {"name": name or Path(path).name, "path": relative, "url": output_file_url(relative)}


def _selected_layers(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "layer_key": layer.get("layer_key"),
            "layer_name": layer.get("layer_name"),
            "category": layer.get("category"),
            "role": layer.get("role"),
            "source_status": layer.get("source_status"),
            "source_role": layer.get("source_role"),
            "confidence_score": layer.get("confidence_score"),
            "layer_url": layer.get("layer_url"),
        }
        for layer in recipe.get("selected_layers") or []
    ]


def _review_warnings(recipe: dict[str, Any], parcel_context: dict[str, Any]) -> list[str]:
    warnings = [
        *[str(item) for item in recipe.get("review_reasons") or [] if item],
        *[str(item) for item in parcel_context.get("parcel_warnings") or [] if item],
    ]
    return sorted({warning for warning in warnings if warning})


def _preview_blockers(recipe: dict[str, Any]) -> list[str]:
    parcel_context = recipe.get("parcel_context") or {}
    if parcel_context and parcel_context.get("can_focus_map") is False:
        return [parcel_context.get("reason_if_not_focusable") or PARCEL_NOT_MATCHED_WARNING]
    validation = recipe.get("validation") or {}
    return [str(item) for item in validation.get("errors") or [] if item]


def _can_preview(recipe: dict[str, Any], webmap_json: dict[str, Any]) -> bool:
    if _preview_blockers(recipe):
        return False
    validation = webmap_json.get("autoMapValidation") or {}
    return bool(recipe.get("selected_layers")) and not bool(validation.get("errors"))


def _can_analyze(recipe: dict[str, Any]) -> bool:
    if recipe.get("parcel_context"):
        return False
    analysis = recipe.get("analysis_execution") or {}
    return bool(analysis.get("executable"))


def _next_action(can_preview: bool, blockers: list[str]) -> str:
    if blockers:
        return "correct_parcel_identifier" if any("parcel" in blocker.lower() for blocker in blockers) else "review_blockers"
    return "preview_map" if can_preview else "review_recipe"


def _preview_config_for(path: Path, can_preview: bool) -> dict[str, Any] | None:
    if not can_preview:
        return None
    return build_preview_config(path)


def _save_session_payload(session_folder: Path, payload: dict[str, Any]) -> None:
    _write_json(session_folder / "composer_session.json", payload)


def _base_session_response(
    *,
    session_id: str,
    raw_prompt: str,
    session_folder: Path,
    recipe: dict[str, Any],
    webmap_json: dict[str, Any],
    preview_config: dict[str, Any] | None,
    review_packet_path: Path | None,
    adjusted_packet_path: Path | None = None,
    report_package: Any | None = None,
    export_files: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    parcel_context = recipe.get("parcel_context") or {}
    blockers = _preview_blockers(recipe)
    can_preview = _can_preview(recipe, webmap_json)
    if blockers:
        can_preview = False
    packet_path = adjusted_packet_path or review_packet_path
    packet_id = packet_path.name if packet_path else None
    webmap_path = session_folder / ("adjusted_webmap.json" if (session_folder / "adjusted_webmap.json").exists() else "webmap.json")
    response = {
        "composer_session_id": session_id,
        "raw_prompt": raw_prompt,
        "map_title": recipe.get("map_title") or webmap_json.get("title"),
        "recipe": recipe,
        "webmap_json": webmap_json,
        "preview_config": preview_config,
        "selected_layers": _selected_layers(recipe),
        "warnings": _review_warnings(recipe, parcel_context),
        "missing_data": recipe.get("missing_data_needed") or [],
        "parcel_context": parcel_context,
        "can_preview": can_preview,
        "can_analyze": _can_analyze(recipe),
        "can_report": bool(packet_path),
        "preview_blockers": blockers,
        "next_action": _next_action(can_preview, blockers),
        "review_packet_id": review_packet_path.name if review_packet_path else None,
        "review_packet_path": _repo_relative(review_packet_path),
        "adjusted_packet_id": adjusted_packet_path.name if adjusted_packet_path else None,
        "adjusted_packet_path": _repo_relative(adjusted_packet_path),
        "packet_id": packet_id,
        "packet_path": _repo_relative(packet_path),
        "preview_url": f"/preview/{packet_id}" if packet_id and can_preview else None,
        "webmap_path": _repo_relative(webmap_path),
        "composer_session_path": _repo_relative(session_folder),
        "export": None,
        "draft_only": True,
        "published": False,
        "created_at": _utc_now(),
    }
    if report_package:
        response["export"] = {
            "report_id": report_package.report_id,
            "report_path": _repo_relative(report_package.report_path),
            "report_title": report_package.report_title,
            "files": export_files or [],
            "validation": report_package.validation,
        }
    return response


def _write_layer_csv(path: Path, recipe: dict[str, Any], webmap_json: dict[str, Any]) -> None:
    rows = build_layer_review_table(recipe, webmap_json)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["title", "layer_key", "role", "source_status", "opacity", "visibility", "layer_url"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in writer.fieldnames})


def _write_session_files(session_folder: Path, recipe: dict[str, Any], webmap_json: dict[str, Any]) -> None:
    warnings = build_warning_report(recipe, webmap_json)
    summary = build_review_summary(recipe, webmap_json)
    _write_json(session_folder / "recipe.json", recipe)
    _write_json(session_folder / "webmap.json", webmap_json)
    _write_json(session_folder / "warnings.json", warnings)
    _write_json(session_folder / "layer_review.json", build_layer_review_table(recipe, webmap_json))
    (session_folder / "review_summary.md").write_text(summary, encoding="utf-8")
    _write_layer_csv(session_folder / "layer_list.csv", recipe, webmap_json)


def generate_composer_draft(prompt: str) -> dict[str, Any]:
    """Generate one clean composer response without running analysis or publishing."""
    session_id = f"composer_{uuid4().hex[:12]}"
    session_folder = _session_path(session_id)
    session_folder.mkdir(parents=True, exist_ok=False)

    recipe = build_recipe(prompt)
    webmap_json = build_webmap_json(recipe)
    _write_session_files(session_folder, recipe, webmap_json)
    blockers = _preview_blockers(recipe)
    can_preview = _can_preview(recipe, webmap_json) and not blockers

    review_packet_path: Path | None = None
    if can_preview:
        review_packet_path = save_review_packet(prompt, recipe, webmap_json)
    preview_config = _preview_config_for(review_packet_path or session_folder, can_preview)

    response = _base_session_response(
        session_id=session_id,
        raw_prompt=prompt,
        session_folder=session_folder,
        recipe=recipe,
        webmap_json=webmap_json,
        preview_config=preview_config,
        review_packet_path=review_packet_path,
    )
    _save_session_payload(session_folder, response)
    return response


def get_composer_session(session_id: str) -> dict[str, Any]:
    """Return a previously created composer session."""
    path = _session_path(session_id) / "composer_session.json"
    if not path.exists():
        raise FileNotFoundError(f"Composer session not found: {session_id}")
    return _read_json(path)


def _simple_adjustments_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    layer_adjustments: dict[str, Any] = {}
    definition_expression_overrides: dict[str, str] = {}
    layer_order: list[str] = []
    for layer in payload.get("layers") or []:
        if not isinstance(layer, dict):
            continue
        key = str(layer.get("layer_key") or layer.get("title") or "").strip()
        if not key:
            continue
        layer_order.append(key)
        adjustment: dict[str, Any] = {}
        for source_key in ("visibility", "opacity", "title", "role", "showLegend", "remove_layer"):
            if source_key in layer:
                adjustment[source_key] = layer[source_key]
        if adjustment:
            layer_adjustments[key] = adjustment
        expression = layer.get("definition_expression")
        if isinstance(expression, str) and expression.strip():
            definition_expression_overrides[key] = expression.strip()
    adjustments = {
        "map_title": payload.get("map_title"),
        "map_description": payload.get("map_description"),
        "layer_order": payload.get("layer_order") or layer_order,
        "layer_adjustments": layer_adjustments,
        "definition_expression_overrides": definition_expression_overrides,
        "reviewer_notes": [payload["notes"]] if payload.get("notes") else [],
        "publish_ready": False,
    }
    return normalize_adjustments(adjustments)


def apply_composer_adjustments(session_id: str, adjustment_payload: dict[str, Any]) -> dict[str, Any]:
    """Apply simple UI adjustments and return an updated preview response."""
    session = get_composer_session(session_id)
    session_folder = _session_path(session_id)
    recipe = deepcopy(session.get("recipe") or {})
    webmap_json = deepcopy(session.get("webmap_json") or {})
    adjustments = _simple_adjustments_from_payload(adjustment_payload)
    adjusted_recipe = apply_adjustments_to_recipe(recipe, adjustments)
    adjusted_webmap = apply_adjustments_to_webmap(webmap_json, adjustments)

    _write_json(session_folder / "adjusted_recipe.json", adjusted_recipe)
    _write_json(session_folder / "adjusted_webmap.json", adjusted_webmap)
    _write_json(session_folder / "applied_adjustments.json", adjustments)
    _write_layer_csv(session_folder / "adjusted_layer_list.csv", adjusted_recipe, adjusted_webmap)

    review_packet_path = Path(session["review_packet_path"]) if session.get("review_packet_path") else None
    adjusted_packet_path: Path | None = None
    if review_packet_path:
        adjusted_packet_path = write_adjusted_packet(review_packet_path, adjusted_recipe, adjusted_webmap, adjustments)
    can_preview = _can_preview(adjusted_recipe, adjusted_webmap)
    preview_config = _preview_config_for(adjusted_packet_path or session_folder, can_preview)

    response = _base_session_response(
        session_id=session_id,
        raw_prompt=str(session.get("raw_prompt") or adjusted_recipe.get("user_intent") or ""),
        session_folder=session_folder,
        recipe=adjusted_recipe,
        webmap_json=adjusted_webmap,
        preview_config=preview_config,
        review_packet_path=review_packet_path,
        adjusted_packet_path=adjusted_packet_path,
    )
    response["applied_adjustments"] = adjustments
    response["next_action"] = "preview_adjusted_map" if can_preview else response["next_action"]
    _save_session_payload(session_folder, response)
    return response


def export_composer_session(session_id: str) -> dict[str, Any]:
    """Create local draft report/export links for a composer session."""
    session = get_composer_session(session_id)
    packet_path = session.get("adjusted_packet_path") or session.get("review_packet_path")
    if not packet_path:
        raise ValueError("Composer export requires a preview-ready review packet.")
    package = generate_report(packet_path)
    report_files = [
        _file_link(path, name)
        for name, path in sorted(package.files.items())
    ]
    session_folder = _session_path(session_id)
    webmap_path = session_folder / ("adjusted_webmap.json" if (session_folder / "adjusted_webmap.json").exists() else "webmap.json")
    local_files = [
        _file_link(webmap_path, "webmap.json"),
        _file_link(session_folder / "review_summary.md", "review_summary.md"),
        _file_link(session_folder / "layer_list.csv", "layer_list.csv"),
    ]
    response = {
        **session,
        "export": {
            "report_id": package.report_id,
            "report_path": _repo_relative(package.report_path),
            "report_title": package.report_title,
            "files": [*report_files, *local_files],
            "validation": package.validation,
        },
        "can_report": True,
        "next_action": "print_or_export",
    }
    _save_session_payload(session_folder, response)
    return response
