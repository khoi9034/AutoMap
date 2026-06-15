"""JSON API routes for the AutoMap Next.js frontend."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.adjustment_engine import (
    apply_adjustments_to_review_packet,
    create_adjustment_template,
    validate_adjusted_packet,
)
from app.approval_engine import (
    apply_approval_to_adjusted_packet,
    create_approval_template,
    list_approval_history,
    validate_approved_packet,
)
from app.arcgis_publisher import publish_webmap_draft
from app.clarification_engine import (
    answer_clarification_session,
    create_clarification_session,
    get_clarification_session,
    list_clarification_sessions,
    refine_recipe_from_answers,
)
from app.data_gap_registry import data_gap_records_from_recipe, list_data_gaps
from app.feedback_learning import (
    learn_from_approved_packet,
    learn_from_clarification_session,
    recent_feedback,
    record_recipe_feedback,
)
from app.layer_catalog_store import search_layers
from app.packet_index import (
    build_preview_config,
    find_latest_packet,
    list_adjusted_packets,
    list_approved_packets,
    list_review_packets,
)
from app.portal_smoke_test import run_publish_smoke_test
from app.pattern_library import get_pattern, list_clarification_defaults, list_patterns
from app.recipe_engine import build_recipe
from app.report_generator import generate_report, get_report, list_reports
from app.request_history import list_request_history, record_request_history
from app.review_packet_builder import (
    build_layer_review_table,
    build_review_packet,
    save_review_packet,
    validate_review_packet,
)
from app.system_status import get_system_status
from app.ui_models import output_file_url, repo_root
from app.webmap_exporter import export_recipe_and_webmap


api_router = APIRouter(prefix="/api")

PROTECTED_API_MARKERS = {
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


class PromptRequest(BaseModel):
    """Prompt payload from the frontend."""

    prompt: str


class ClarificationAnswerPayload(BaseModel):
    """One frontend answer to a clarification question."""

    question_id: str
    answer_value: Any
    answer_label: str | None = None
    answered_by: str | None = None


class ClarificationAnswerRequest(BaseModel):
    """Clarification answer payload from the frontend."""

    answers: list[ClarificationAnswerPayload]
    answered_by: str | None = "local_reviewer"


class PacketPathRequest(BaseModel):
    """Packet path payload for local-only workflow actions."""

    packet_folder: str | None = None
    adjusted_packet_folder: str | None = None
    approved_packet_folder: str | None = None


class ReportRequest(BaseModel):
    """Report generation payload for local packet exports."""

    packet_folder: str


class LearnApprovedRequest(BaseModel):
    """Approved packet learning payload."""

    approved_packet_folder: str


class RecipeFeedbackRequest(BaseModel):
    """Recipe feedback payload for deterministic local learning."""

    raw_prompt: str
    recipe: dict[str, Any] = {}
    feedback_type: str
    feedback_json: dict[str, Any] = {}
    source_packet_path: str | None = None


class ApplyAdjustmentsRequest(BaseModel):
    """Apply a human-edited YAML adjustment body."""

    packet_folder: str
    adjustment_yaml: str


class ApplyApprovalRequest(BaseModel):
    """Apply a human-edited YAML approval body."""

    adjusted_packet_folder: str
    approval_yaml: str


def _has_protected_marker(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PROTECTED_API_MARKERS)


def _sanitize_for_api(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if _has_protected_marker(key_text):
                continue
            sanitized[key] = _sanitize_for_api(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_for_api(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize_for_api(item) for item in value]
    if isinstance(value, str):
        return "[redacted]" if _has_protected_marker(value) else value
    return value


def _json_response(value: Any) -> Any:
    return _sanitize_for_api(value)


def _read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _optional_json(path: str | Path) -> Any:
    json_path = Path(path)
    if not json_path.exists():
        return None
    try:
        return _read_json(json_path)
    except (OSError, json.JSONDecodeError):
        return None


def _write_ignored_helper_file(folder_name: str, file_name: str, content: str) -> Path:
    root = repo_root() / "outputs" / folder_name
    root.mkdir(parents=True, exist_ok=True)
    helper_path = root / file_name
    helper_path.write_text(content, encoding="utf-8")
    return helper_path


def _record_history_safely(**kwargs: Any) -> None:
    try:
        record_request_history(**kwargs)
    except Exception:
        return


def _packet_file_links(packet_path: str | Path, file_names: list[str]) -> list[dict[str, str]]:
    packet = Path(packet_path)
    return [
        {
            "name": file_name,
            "path": str(packet / file_name),
            "url": output_file_url(packet / file_name),
        }
        for file_name in file_names
        if (packet / file_name).exists()
    ]


def _repo_relative_output_path(path: str | Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(repo_root().resolve()).as_posix()
    except ValueError:
        return Path(path).as_posix()


def _preview_url_for_source(source: str | Path) -> str:
    text = Path(source).as_posix()
    if "/" in text or "\\" in text or text.endswith(".json"):
        return f"/preview?path={text}"
    return f"/preview/{text}"


def _packet_id_from_path(path: str | Path) -> str:
    return Path(path).name if Path(path).suffix == "" else Path(path).stem


def _path_from_packet_request(payload: PacketPathRequest) -> str:
    path = payload.approved_packet_folder or payload.adjusted_packet_folder or payload.packet_folder
    if not path:
        raise HTTPException(status_code=422, detail="A packet folder path is required.")
    return path


def _handle_value_error(exc: Exception) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@api_router.get("/status")
def api_status() -> Any:
    """Return sanitized AutoMap system status for the frontend."""
    return _json_response(get_system_status())


@api_router.get("/catalog/search")
def api_catalog_search(q: str = Query(default="flood")) -> Any:
    """Search the trusted AutoMap layer catalog."""
    rows = search_layers(q) if q else []
    return _json_response({"query": q, "rows": rows})


@api_router.get("/data-gaps")
def api_data_gaps() -> Any:
    """Return current AutoMap data gaps."""
    return _json_response({"rows": list_data_gaps()})


@api_router.get("/history")
def api_history(limit: int = Query(default=50, ge=1, le=200)) -> Any:
    """Return recent local request and approval history."""
    return _json_response(
        {
            "request_history": list_request_history(limit=limit),
            "approval_history": list_approval_history(limit=limit),
        }
    )


@api_router.get("/packets")
def api_packets() -> Any:
    """Return local output packet indexes."""
    review_packets = list_review_packets()
    adjusted_packets = list_adjusted_packets()
    approved_packets = list_approved_packets()
    return _json_response(
        {
            "latest": find_latest_packet(),
            "review_packets": review_packets,
            "adjusted_packets": adjusted_packets,
            "approved_packets": approved_packets,
            "counts": {
                "review_packets": len(review_packets),
                "adjusted_packets": len(adjusted_packets),
                "approved_packets": len(approved_packets),
            },
        }
    )


@api_router.get("/reports")
def api_reports() -> Any:
    """Return generated local report packages."""
    return _json_response({"reports": list_reports()})


@api_router.get("/reports/{report_id}")
def api_report_detail(report_id: str) -> Any:
    """Return one generated report package summary and file links."""
    try:
        return _json_response(get_report(report_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise _handle_value_error(exc) from exc


@api_router.post("/generate-report")
def api_generate_report(payload: ReportRequest) -> Any:
    """Generate a local report package from a review, adjusted, or approved packet."""
    try:
        package = generate_report(payload.packet_folder)
    except (FileNotFoundError, ValueError) as exc:
        raise _handle_value_error(exc) from exc
    return _json_response(
        {
            "report_id": package.report_id,
            "report_path": _repo_relative_output_path(package.report_path),
            "report_title": package.report_title,
            "packet_type": package.packet_type,
            "packet_path": package.packet_path,
            "files": _packet_file_links(
                _repo_relative_output_path(package.report_path),
                [
                    "report_summary.html",
                    "report_summary.md",
                    "report_data.json",
                    "layer_table.csv",
                    "warning_report.json",
                    "export_manifest.json",
                ],
            ),
            "validation": package.validation,
        }
    )


@api_router.get("/patterns")
def api_patterns(limit: int = Query(default=50, ge=1, le=200)) -> Any:
    """Return approved local learning patterns."""
    return _json_response(
        {
            "patterns": list_patterns(limit=limit),
            "clarification_defaults": list_clarification_defaults(limit=limit),
            "feedback_log": recent_feedback(limit=limit),
        }
    )


@api_router.post("/patterns/learn-from-approved")
def api_patterns_learn_from_approved(payload: LearnApprovedRequest) -> Any:
    """Learn an approved local pattern from an approved packet."""
    try:
        pattern = learn_from_approved_packet(payload.approved_packet_folder)
    except (FileNotFoundError, ValueError) as exc:
        raise _handle_value_error(exc) from exc
    return _json_response({"pattern": pattern})


@api_router.get("/patterns/{pattern_key}")
def api_pattern_detail(pattern_key: str) -> Any:
    """Return one approved local learning pattern."""
    try:
        return _json_response(get_pattern(pattern_key))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.post("/feedback/recipe")
def api_recipe_feedback(payload: RecipeFeedbackRequest) -> Any:
    """Record deterministic local recipe feedback."""
    try:
        feedback = record_recipe_feedback(
            payload.raw_prompt,
            payload.recipe,
            payload.feedback_type,
            payload.feedback_json,
            source_packet_path=payload.source_packet_path,
        )
    except ValueError as exc:
        raise _handle_value_error(exc) from exc
    return _json_response({"feedback": feedback})


@api_router.get("/clarification-defaults")
def api_clarification_defaults(limit: int = Query(default=50, ge=1, le=200)) -> Any:
    """Return learned clarification defaults."""
    return _json_response({"defaults": list_clarification_defaults(limit=limit)})


@api_router.get("/clarification")
def api_clarification_sessions(limit: int = Query(default=50, ge=1, le=200)) -> Any:
    """List recent local clarification sessions."""
    return _json_response({"sessions": list_clarification_sessions(limit=limit)})


@api_router.post("/clarification/start")
def api_clarification_start(payload: PromptRequest) -> Any:
    """Start an interactive clarification session from a prompt."""
    try:
        session = create_clarification_session(payload.prompt)
    except ValueError as exc:
        raise _handle_value_error(exc) from exc
    _record_history_safely(
        raw_prompt=payload.prompt,
        workflow_step="clarification",
        map_title=session.get("initial_recipe", {}).get("map_title"),
        status=session.get("status"),
        notes={"question_count": len(session.get("questions") or [])},
    )
    return _json_response(session)


@api_router.get("/clarification/{session_id}")
def api_clarification_detail(session_id: str) -> Any:
    """Return one clarification session."""
    try:
        return _json_response(get_clarification_session(session_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@api_router.post("/clarification/{session_id}/answer")
def api_clarification_answer(session_id: str, payload: ClarificationAnswerRequest) -> Any:
    """Save clarification answers."""
    try:
        answers = [answer.model_dump() for answer in payload.answers]
        session = answer_clarification_session(
            session_id,
            answers,
            answered_by=payload.answered_by or "local_reviewer",
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise _handle_value_error(exc) from exc
    return _json_response(session)


@api_router.post("/clarification/{session_id}/learn")
def api_clarification_learn(session_id: str) -> Any:
    """Record a clarification session as local feedback."""
    try:
        feedback = learn_from_clarification_session(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _json_response({"feedback": feedback})


@api_router.post("/clarification/{session_id}/refine")
def api_clarification_refine(session_id: str) -> Any:
    """Refine a recipe using saved clarification answers."""
    try:
        session = refine_recipe_from_answers(session_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise _handle_value_error(exc) from exc
    refined_recipe = session.get("refined_recipe") or {}
    _record_history_safely(
        raw_prompt=session.get("raw_prompt"),
        workflow_step="clarification_refined",
        map_title=refined_recipe.get("map_title"),
        status=session.get("status"),
        notes={"session_id": session_id, "changes_summary": session.get("changes_summary") or {}},
    )
    return _json_response(session)


@api_router.get("/preview-config/{packet_id}")
def api_preview_config(packet_id: str) -> Any:
    """Return sanitized preview config for a packet id."""
    try:
        return _json_response(build_preview_config(packet_id))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise _handle_value_error(exc) from exc


@api_router.post("/recipe")
def api_recipe(payload: PromptRequest) -> Any:
    """Build a map recipe from a prompt."""
    recipe = build_recipe(payload.prompt)
    _record_history_safely(
        raw_prompt=payload.prompt,
        workflow_step="recipe",
        map_title=recipe.get("map_title"),
        status="created",
        notes={"selected_layer_count": len(recipe.get("selected_layers") or [])},
    )
    return _json_response({"prompt": payload.prompt, "recipe": recipe, "data_gaps": data_gap_records_from_recipe(recipe)})


@api_router.post("/review-packet")
def api_review_packet(payload: PromptRequest) -> Any:
    """Create a local review packet from a prompt."""
    packet = build_review_packet(payload.prompt)
    packet_path = save_review_packet(payload.prompt, packet["recipe"], packet["webmap_json"])
    validation = validate_review_packet(packet_path)
    layer_review = build_layer_review_table(packet["recipe"], packet["webmap_json"])
    _record_history_safely(
        raw_prompt=payload.prompt,
        workflow_step="review_packet",
        map_title=packet["recipe"].get("map_title"),
        status="created",
        packet_path=str(packet_path),
        notes={"selected_layer_count": len(packet["recipe"].get("selected_layers") or [])},
    )
    return _json_response(
        {
            "prompt": payload.prompt,
            "packet_id": _packet_id_from_path(packet_path),
            "packet_path": str(packet_path),
            "recipe": packet["recipe"],
            "webmap_json": packet["webmap_json"],
            "warnings": packet["warnings"],
            "layer_review": layer_review,
            "validation": validation,
            "preview_url": _preview_url_for_source(packet_path),
            "files": _packet_file_links(
                packet_path,
                ["recipe.json", "webmap.json", "review_summary.md", "warnings.json", "layer_review.json", "review.html"],
            ),
        }
    )


@api_router.post("/webmap-draft")
def api_webmap_draft(payload: PromptRequest) -> Any:
    """Create a local WebMap draft JSON artifact from a prompt."""
    result = export_recipe_and_webmap(payload.prompt)
    return _json_response(
        {
            "prompt": payload.prompt,
            "packet_id": _packet_id_from_path(result["webmap_path"]),
            "recipe": result["recipe"],
            "webmap_json": result["webmap_json"],
            "validation": result["validation"],
            "webmap_path": str(result["webmap_path"]),
            "preview_url": _preview_url_for_source(result["webmap_path"]),
        }
    )


@api_router.post("/adjustment-template")
def api_adjustment_template(payload: PacketPathRequest) -> Any:
    """Create a local YAML adjustment template."""
    packet_folder = _path_from_packet_request(payload)
    try:
        template_path = create_adjustment_template(packet_folder)
    except (FileNotFoundError, ValueError) as exc:
        raise _handle_value_error(exc) from exc
    return _json_response(
        {
            "packet_folder": packet_folder,
            "template_path": str(template_path),
            "adjustment_yaml": template_path.read_text(encoding="utf-8"),
        }
    )


@api_router.post("/apply-adjustments")
def api_apply_adjustments(payload: ApplyAdjustmentsRequest) -> Any:
    """Apply YAML adjustments and create a separate adjusted packet."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    adjustment_path = _write_ignored_helper_file(
        "adjustment_templates",
        f"{Path(payload.packet_folder).name}_adjustments_frontend_{timestamp}.yaml",
        payload.adjustment_yaml,
    )
    try:
        adjusted_path = apply_adjustments_to_review_packet(payload.packet_folder, adjustment_path)
    except (FileNotFoundError, ValueError) as exc:
        raise _handle_value_error(exc) from exc
    validation = validate_adjusted_packet(adjusted_path)
    adjusted_warnings = _optional_json(Path(adjusted_path) / "adjusted_warnings.json")
    layer_review = _optional_json(Path(adjusted_path) / "adjusted_layer_review.json") or []
    return _json_response(
        {
            "packet_folder": payload.packet_folder,
            "template_path": str(adjustment_path),
            "adjusted_packet_id": _packet_id_from_path(adjusted_path),
            "adjusted_path": str(adjusted_path),
            "validation": validation,
            "adjusted_warnings": adjusted_warnings,
            "layer_review": layer_review,
            "preview_url": _preview_url_for_source(adjusted_path),
            "files": _packet_file_links(
                adjusted_path,
                [
                    "adjusted_recipe.json",
                    "adjusted_webmap.json",
                    "applied_adjustments.json",
                    "adjusted_warnings.json",
                    "adjusted_layer_review.json",
                    "adjusted_review.html",
                ],
            ),
        }
    )


@api_router.post("/approval-template")
def api_approval_template(payload: PacketPathRequest) -> Any:
    """Create a local YAML approval template."""
    adjusted_packet_folder = payload.adjusted_packet_folder or payload.packet_folder
    if not adjusted_packet_folder:
        raise HTTPException(status_code=422, detail="An adjusted packet folder path is required.")
    try:
        template_path = create_approval_template(adjusted_packet_folder)
    except (FileNotFoundError, ValueError) as exc:
        raise _handle_value_error(exc) from exc
    return _json_response(
        {
            "adjusted_packet_folder": adjusted_packet_folder,
            "template_path": str(template_path),
            "approval_yaml": template_path.read_text(encoding="utf-8"),
        }
    )


@api_router.post("/apply-approval")
def api_apply_approval(payload: ApplyApprovalRequest) -> Any:
    """Apply YAML approval and create a separate approved packet."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    approval_path = _write_ignored_helper_file(
        "approval_templates",
        f"{Path(payload.adjusted_packet_folder).name}_approval_frontend_{timestamp}.yaml",
        payload.approval_yaml,
    )
    try:
        approved_path = apply_approval_to_adjusted_packet(payload.adjusted_packet_folder, approval_path)
    except (FileNotFoundError, ValueError) as exc:
        raise _handle_value_error(exc) from exc
    validation = validate_approved_packet(approved_path)
    receipt = _optional_json(Path(approved_path) / "approval_receipt.json") or {}
    approved_warnings = _optional_json(Path(approved_path) / "approved_warnings.json") or {}
    layer_review = _optional_json(Path(approved_path) / "approved_layer_review.json") or []
    approved_recipe = _optional_json(Path(approved_path) / "approved_recipe.json") or {}
    _record_history_safely(
        raw_prompt=approved_recipe.get("user_intent"),
        workflow_step="approval",
        map_title=approved_recipe.get("map_title"),
        status="publish_ready" if receipt.get("final_publish_ready") else "blocked",
        adjusted_packet_path=payload.adjusted_packet_folder,
        notes={
            "approved_packet_path": str(approved_path),
            "final_publish_ready": receipt.get("final_publish_ready"),
            "block_reasons": receipt.get("block_reasons") or [],
        },
    )
    return _json_response(
        {
            "adjusted_packet_folder": payload.adjusted_packet_folder,
            "template_path": str(approval_path),
            "approved_packet_id": _packet_id_from_path(approved_path),
            "approved_path": str(approved_path),
            "validation": validation,
            "approval_receipt": receipt,
            "approved_warnings": approved_warnings,
            "layer_review": layer_review,
            "preview_url": _preview_url_for_source(approved_path),
            "files": _packet_file_links(
                approved_path,
                [
                    "approved_recipe.json",
                    "approved_webmap.json",
                    "approval_file.json",
                    "approval_receipt.json",
                    "approved_warnings.json",
                    "approved_layer_review.json",
                    "approved_review_summary.md",
                    "approved_review.html",
                ],
            ),
        }
    )


@api_router.post("/publish-dry-run")
def api_publish_dry_run(payload: PacketPathRequest) -> Any:
    """Run dry-run publishing only; this API cannot real-publish."""
    packet_path = _path_from_packet_request(payload)
    result = publish_webmap_draft(packet_path, dry_run=True, confirm_publish=False)
    receipt_path = Path(packet_path) / "publish_receipt.json"
    return _json_response(
        {
            "packet_id": _packet_id_from_path(packet_path),
            "packet_path": packet_path,
            "receipt_path": str(receipt_path) if receipt_path.exists() else None,
            "result": result,
        }
    )


@api_router.post("/portal-smoke-test-dry-run")
def api_portal_smoke_test_dry_run(payload: PacketPathRequest) -> Any:
    """Run a dry-run portal smoke test only; this API cannot real-publish."""
    packet_path = payload.approved_packet_folder or payload.packet_folder
    if not packet_path:
        raise HTTPException(status_code=422, detail="An approved packet folder path is required.")
    result = run_publish_smoke_test(packet_path, confirm_publish=False)
    receipt_path = Path(packet_path) / "smoke_test_receipt.json"
    return _json_response(
        {
            "approved_packet_id": _packet_id_from_path(packet_path),
            "approved_packet_folder": packet_path,
            "receipt_path": str(receipt_path) if receipt_path.exists() else None,
            "result": result,
        }
    )
