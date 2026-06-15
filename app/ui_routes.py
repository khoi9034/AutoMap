"""FastAPI routes for AutoMap's local review UI."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

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
from app.data_gap_registry import data_gap_records_from_recipe, list_data_gaps
from app.layer_catalog_store import search_layers
from app.packet_index import (
    build_preview_config,
    find_latest_packet,
    list_adjusted_packets,
    list_approved_packets,
    list_review_packets,
)
from app.portal_smoke_test import run_publish_smoke_test
from app.recipe_engine import build_recipe
from app.request_history import list_request_history, record_request_history
from app.review_packet_builder import (
    build_layer_review_table,
    build_review_packet,
    save_review_packet,
    validate_review_packet,
)
from app.ui_models import (
    CATALOG_SEARCH_EXAMPLES,
    DEMO_SCENARIOS,
    EXAMPLE_PROMPTS,
    AUTOMAP_VERSION,
    PROJECT_TITLE,
    SAFETY_BANNER,
    output_file_url,
    repo_root,
)
from app.system_status import get_system_status
from app.webmap_exporter import export_recipe_and_webmap


router = APIRouter()
templates = Jinja2Templates(directory=str(repo_root() / "templates"))


def _base_context(request: Request, **extra: Any) -> dict[str, Any]:
    context = {
        "request": request,
        "project_title": PROJECT_TITLE,
        "safety_banner": SAFETY_BANNER,
        "automap_version": AUTOMAP_VERSION,
        "example_prompts": EXAMPLE_PROMPTS,
        "catalog_search_examples": CATALOG_SEARCH_EXAMPLES,
    }
    context.update(extra)
    return context


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


def _safe_local_output_path(path: str) -> Path:
    root = repo_root().resolve()
    output_root = (root / "outputs").resolve()
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(output_root)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Local file is outside AutoMap outputs.") from exc
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Local file not found.")
    return resolved


def _record_history_safely(**kwargs: Any) -> None:
    try:
        record_request_history(**kwargs)
    except Exception:
        return


def _preview_url_for_source(source: str | Path) -> str:
    text = Path(source).as_posix()
    if "/" in text or "\\" in text or text.endswith(".json"):
        return f"/preview?{urlencode({'path': text})}"
    return f"/preview/{text}"


def _preview_config_url(*, packet_id: str | None = None, path: str | None = None) -> str:
    query = {}
    if path:
        query["path"] = path
    elif packet_id:
        query["packet_id"] = packet_id
    return "/api/preview-config" if not query else f"/api/preview-config?{urlencode(query)}"


def _latest_matching_preview_url(prompt: str) -> str | None:
    from app.layer_semantics import slugify

    slug = slugify(prompt)[:90]
    for packet in [*list_adjusted_packets(), *list_review_packets()]:
        packet_id = packet.get("packet_id") or ""
        if slug and slug in packet_id:
            return packet.get("preview_url")
    return None


def _preview_context(request: Request, *, packet_id: str | None = None, path: str | None = None) -> dict[str, Any]:
    source = path or packet_id
    try:
        config = build_preview_config(source)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _base_context(
        request,
        preview_config=config,
        preview_config_url=_preview_config_url(packet_id=packet_id, path=path),
        webmap_file_url=output_file_url(config["webmap_path"]),
        review_file_url=output_file_url(Path(config["packet_path"]) / "review.html")
        if config["draft_status"] == "review_packet"
        else None,
        adjusted_review_file_url=output_file_url(Path(config["packet_path"]) / "adjusted_review.html")
        if config["draft_status"] == "adjusted_review"
        else None,
        approved_review_file_url=output_file_url(Path(config["packet_path"]) / "approved_review.html")
        if config["draft_status"] == "approved_review"
        else None,
    )


@router.get("/")
def index(request: Request):
    """Render the local UI home page."""
    review_packets = list_review_packets()[:5]
    adjusted_packets = list_adjusted_packets()[:5]
    approved_packets = list_approved_packets()[:5]
    latest_packet = find_latest_packet()
    system_status = get_system_status()
    return templates.TemplateResponse(
        request,
        "index.html",
        _base_context(
            request,
            review_packets=review_packets,
            adjusted_packets=adjusted_packets,
            approved_packets=approved_packets,
            latest_packet=latest_packet,
            system_status=system_status,
        ),
    )


@router.get("/health")
def health() -> dict[str, Any]:
    """Return local UI health without touching external services."""
    return {
        "status": "ok",
        "app": "AutoMap local UI",
        "real_publishing_enabled_in_ui": False,
        "arcgis_login_required": False,
    }


@router.get("/local-file")
def local_file(path: str):
    """Serve generated output files from the local outputs directory."""
    return FileResponse(_safe_local_output_path(path))


@router.get("/demo")
def demo(request: Request):
    """Render approved v1 demo scenarios."""
    scenarios = [
        {**scenario, "preview_url": _latest_matching_preview_url(scenario["prompt"])}
        for scenario in DEMO_SCENARIOS
    ]
    return templates.TemplateResponse(
        request,
        "demo.html",
        _base_context(request, scenarios=scenarios),
    )


@router.get("/status")
def status(request: Request):
    """Render sanitized AutoMap local system status."""
    return templates.TemplateResponse(
        request,
        "status.html",
        _base_context(request, status=get_system_status()),
    )


@router.get("/history")
def history(request: Request):
    """Render recent local request history."""
    try:
        rows = list_request_history(limit=50)
        history_error = None
    except Exception as exc:
        rows = []
        history_error = str(exc)
    return templates.TemplateResponse(
        request,
        "history.html",
        _base_context(request, rows=rows, history_error=history_error, status=get_system_status()),
    )


@router.get("/approval")
def approval(request: Request):
    """Render the local reviewer approval gate."""
    try:
        approval_rows = list_approval_history(limit=50)
        approval_error = None
    except Exception as exc:
        approval_rows = []
        approval_error = str(exc)
    return templates.TemplateResponse(
        request,
        "approval.html",
        _base_context(
            request,
            approval_rows=approval_rows,
            approval_error=approval_error,
            adjusted_packets=list_adjusted_packets()[:10],
            approved_packets=list_approved_packets()[:10],
            status=get_system_status(),
        ),
    )


@router.get("/preview")
def preview(request: Request, packet_id: str | None = None, path: str | None = None):
    """Render a local browser map preview for the latest or requested draft."""
    return templates.TemplateResponse(request, "map_preview.html", _preview_context(request, packet_id=packet_id, path=path))


@router.get("/preview/{packet_id}")
def preview_packet(request: Request, packet_id: str):
    """Render a local browser map preview for a packet id."""
    return templates.TemplateResponse(request, "map_preview.html", _preview_context(request, packet_id=packet_id))


@router.get("/api/preview-config")
def preview_config(
    packet_id: str | None = Query(default=None),
    path: str | None = Query(default=None),
) -> dict[str, Any]:
    """Return sanitized local preview configuration JSON."""
    try:
        return build_preview_config(path or packet_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/recipe")
def make_recipe(request: Request, prompt: str = Form(...)):
    """Create and display a recipe for a plain-English request."""
    recipe = build_recipe(prompt)
    _record_history_safely(
        raw_prompt=prompt,
        workflow_step="recipe",
        map_title=recipe.get("map_title"),
        status="created",
        notes={"selected_layer_count": len(recipe.get("selected_layers") or [])},
    )
    data_gaps = data_gap_records_from_recipe(recipe)
    return templates.TemplateResponse(
        request,
        "recipe.html",
        _base_context(request, prompt=prompt, recipe=recipe, data_gaps=data_gaps),
    )


@router.post("/review-packet")
def make_review_packet(request: Request, prompt: str = Form(...)):
    """Create a local review packet and display its summary."""
    packet = build_review_packet(prompt)
    packet_path = save_review_packet(prompt, packet["recipe"], packet["webmap_json"])
    _record_history_safely(
        raw_prompt=prompt,
        workflow_step="review_packet",
        map_title=packet["recipe"].get("map_title"),
        status="created",
        packet_path=str(packet_path),
        notes={"selected_layer_count": len(packet["recipe"].get("selected_layers") or [])},
    )
    validation = validate_review_packet(packet_path)
    layer_review = build_layer_review_table(packet["recipe"], packet["webmap_json"])
    files = _packet_file_links(
        packet_path,
        ["recipe.json", "webmap.json", "review_summary.md", "warnings.json", "review.html"],
    )
    return templates.TemplateResponse(
        request,
        "review_packet.html",
        _base_context(
            request,
            prompt=prompt,
            packet_path=str(packet_path),
            recipe=packet["recipe"],
            warnings=packet["warnings"],
            layer_review=layer_review,
            validation=validation,
            files=files,
            preview_url=_preview_url_for_source(packet_path),
            webmap_file_url=output_file_url(Path(packet_path) / "webmap.json"),
            review_file_url=output_file_url(Path(packet_path) / "review.html"),
        ),
    )


@router.post("/webmap-draft")
def make_webmap_draft(request: Request, prompt: str = Form(...)):
    """Create a local WebMap draft JSON output."""
    result = export_recipe_and_webmap(prompt)
    webmap_path = result["webmap_path"]
    return templates.TemplateResponse(
        request,
        "recipe.html",
        _base_context(
            request,
            prompt=prompt,
            recipe=result["recipe"],
            webmap_path=str(webmap_path),
            webmap_file_url=output_file_url(webmap_path),
            preview_url=_preview_url_for_source(webmap_path),
            validation=result["validation"],
            data_gaps=data_gap_records_from_recipe(result["recipe"]),
        ),
    )


@router.post("/adjustment-template")
def adjustment_template(request: Request, packet_folder: str = Form(...)):
    """Create and display an editable adjustment YAML template."""
    template_path = create_adjustment_template(packet_folder)
    adjustment_text = template_path.read_text(encoding="utf-8")
    return templates.TemplateResponse(
        request,
        "adjusted_packet.html",
        _base_context(
            request,
            packet_path=packet_folder,
            template_path=str(template_path),
            adjustment_yaml=adjustment_text,
        ),
    )


@router.post("/apply-adjustments")
def apply_adjustments(
    request: Request,
    packet_folder: str = Form(...),
    adjustment_yaml: str = Form(...),
):
    """Save edited adjustment YAML and create a separate adjusted packet."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    adjustment_path = _write_ignored_helper_file(
        "adjustment_templates",
        f"{Path(packet_folder).name}_adjustments_ui_{timestamp}.yaml",
        adjustment_yaml,
    )
    adjusted_path = apply_adjustments_to_review_packet(packet_folder, adjustment_path)
    validation = validate_adjusted_packet(adjusted_path)
    recipe_for_history = _read_json(Path(adjusted_path) / "adjusted_recipe.json")
    _record_history_safely(
        raw_prompt=recipe_for_history.get("user_intent"),
        workflow_step="adjustment",
        map_title=recipe_for_history.get("map_title"),
        status="created",
        packet_path=packet_folder,
        adjusted_packet_path=str(adjusted_path),
        notes={"validation": validation},
    )
    files = _packet_file_links(
        adjusted_path,
        [
            "adjusted_recipe.json",
            "adjusted_webmap.json",
            "applied_adjustments.json",
            "adjusted_warnings.json",
            "adjusted_review.html",
        ],
    )
    adjusted_warnings = _read_json(Path(adjusted_path) / "adjusted_warnings.json")
    layer_review = _read_json(Path(adjusted_path) / "adjusted_layer_review.json")
    return templates.TemplateResponse(
        request,
        "adjusted_packet.html",
        _base_context(
            request,
            packet_path=packet_folder,
            template_path=str(adjustment_path),
            adjustment_yaml=adjustment_yaml,
            adjusted_path=str(adjusted_path),
            validation=validation,
            adjusted_warnings=adjusted_warnings,
            layer_review=layer_review,
            files=files,
            preview_url=_preview_url_for_source(adjusted_path),
            webmap_file_url=output_file_url(Path(adjusted_path) / "adjusted_webmap.json"),
            adjusted_review_file_url=output_file_url(Path(adjusted_path) / "adjusted_review.html"),
        ),
    )


@router.post("/approval-template")
def approval_template(request: Request, adjusted_packet_folder: str = Form(...)):
    """Create and display an editable approval YAML template."""
    template_path = create_approval_template(adjusted_packet_folder)
    approval_text = template_path.read_text(encoding="utf-8")
    return templates.TemplateResponse(
        request,
        "approved_packet.html",
        _base_context(
            request,
            adjusted_path=adjusted_packet_folder,
            template_path=str(template_path),
            approval_yaml=approval_text,
        ),
    )


@router.post("/apply-approval")
def apply_approval(
    request: Request,
    adjusted_packet_folder: str = Form(...),
    approval_yaml: str = Form(...),
):
    """Apply reviewer approval and create a separate approved packet."""
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    approval_path = _write_ignored_helper_file(
        "approval_templates",
        f"{Path(adjusted_packet_folder).name}_approval_ui_{timestamp}.yaml",
        approval_yaml,
    )
    approved_path = apply_approval_to_adjusted_packet(adjusted_packet_folder, approval_path)
    validation = validate_approved_packet(approved_path)
    receipt = _read_json(Path(approved_path) / "approval_receipt.json")
    approved_warnings = _read_json(Path(approved_path) / "approved_warnings.json")
    layer_review = _read_json(Path(approved_path) / "approved_layer_review.json")
    approved_recipe = _read_json(Path(approved_path) / "approved_recipe.json")
    _record_history_safely(
        raw_prompt=approved_recipe.get("user_intent"),
        workflow_step="approval",
        map_title=approved_recipe.get("map_title"),
        status="publish_ready" if receipt.get("final_publish_ready") else "blocked",
        adjusted_packet_path=adjusted_packet_folder,
        notes={
            "approved_packet_path": str(approved_path),
            "final_publish_ready": receipt.get("final_publish_ready"),
            "block_reasons": receipt.get("block_reasons") or [],
        },
    )
    files = _packet_file_links(
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
    )
    return templates.TemplateResponse(
        request,
        "approved_packet.html",
        _base_context(
            request,
            adjusted_path=adjusted_packet_folder,
            template_path=str(approval_path),
            approval_yaml=approval_yaml,
            approved_path=str(approved_path),
            validation=validation,
            approval_receipt=receipt,
            approved_warnings=approved_warnings,
            layer_review=layer_review,
            files=files,
            smoke_test_receipt=_optional_json(Path(approved_path) / "smoke_test_receipt.json"),
            smoke_test_receipt_url=output_file_url(Path(approved_path) / "smoke_test_receipt.json")
            if (Path(approved_path) / "smoke_test_receipt.json").exists()
            else None,
            preview_url=_preview_url_for_source(approved_path),
            webmap_file_url=output_file_url(Path(approved_path) / "approved_webmap.json"),
            approved_review_file_url=output_file_url(Path(approved_path) / "approved_review.html"),
        ),
    )


@router.post("/publish-dry-run")
def publish_dry_run(request: Request, adjusted_packet_folder: str = Form(...)):
    """Run dry-run publishing only; never real publish from the UI."""
    result = publish_webmap_draft(adjusted_packet_folder, dry_run=True, confirm_publish=False)
    recipe_for_history = {}
    packet_path = Path(adjusted_packet_folder)
    recipe_path = packet_path / "approved_recipe.json"
    if not recipe_path.exists():
        recipe_path = packet_path / "adjusted_recipe.json"
    if recipe_path.exists():
        recipe_for_history = _read_json(recipe_path)
    _record_history_safely(
        raw_prompt=recipe_for_history.get("user_intent"),
        workflow_step="dry_run_publish",
        map_title=recipe_for_history.get("map_title"),
        status=str(result.get("status") or "dry_run"),
        adjusted_packet_path=adjusted_packet_folder,
        notes={
            "created_item": result.get("created_item"),
            "published": result.get("published"),
            "shared_public": result.get("shared_public"),
            "shared_organization": result.get("shared_organization"),
        },
    )
    if (packet_path / "approved_webmap.json").exists():
        receipt = _read_json(packet_path / "approval_receipt.json") if (packet_path / "approval_receipt.json").exists() else {}
        validation = validate_approved_packet(packet_path)
        files = _packet_file_links(
            packet_path,
            [
                "approved_recipe.json",
                "approved_webmap.json",
                "approval_file.json",
                "approval_receipt.json",
                "approved_warnings.json",
                "approved_layer_review.json",
                "approved_review_summary.md",
                "approved_review.html",
                "publish_receipt.json",
            ],
        )
        return templates.TemplateResponse(
            request,
            "approved_packet.html",
            _base_context(
                request,
                approved_path=adjusted_packet_folder,
                validation=validation,
                approval_receipt=receipt,
                publish_result=result,
                publish_receipt=output_file_url(packet_path / "publish_receipt.json"),
                smoke_test_receipt=_optional_json(packet_path / "smoke_test_receipt.json"),
                smoke_test_receipt_url=output_file_url(packet_path / "smoke_test_receipt.json")
                if (packet_path / "smoke_test_receipt.json").exists()
                else None,
                files=files,
                preview_url=_preview_url_for_source(adjusted_packet_folder),
                webmap_file_url=output_file_url(packet_path / "approved_webmap.json"),
                approved_review_file_url=output_file_url(packet_path / "approved_review.html"),
            ),
        )
    return templates.TemplateResponse(
        request,
        "adjusted_packet.html",
        _base_context(
            request,
            adjusted_path=adjusted_packet_folder,
            publish_result=result,
            publish_receipt=output_file_url(Path(adjusted_packet_folder) / "publish_receipt.json"),
            preview_url=_preview_url_for_source(adjusted_packet_folder),
            webmap_file_url=output_file_url(Path(adjusted_packet_folder) / "adjusted_webmap.json"),
        ),
    )


@router.post("/portal-smoke-test-dry-run")
def portal_smoke_test_dry_run(request: Request, approved_packet_folder: str = Form(...)):
    """Run a dry-run portal smoke test only; never real publish from the UI."""
    packet_path = Path(approved_packet_folder)
    result = run_publish_smoke_test(approved_packet_folder, confirm_publish=False)
    receipt = _read_json(packet_path / "approval_receipt.json") if (packet_path / "approval_receipt.json").exists() else {}
    validation = validate_approved_packet(packet_path)
    files = _packet_file_links(
        packet_path,
        [
            "approved_recipe.json",
            "approved_webmap.json",
            "approval_file.json",
            "approval_receipt.json",
            "approved_warnings.json",
            "approved_layer_review.json",
            "approved_review_summary.md",
            "approved_review.html",
            "smoke_test_receipt.json",
        ],
    )
    return templates.TemplateResponse(
        request,
        "approved_packet.html",
        _base_context(
            request,
            approved_path=approved_packet_folder,
            validation=validation,
            approval_receipt=receipt,
            approved_warnings=_optional_json(packet_path / "approved_warnings.json"),
            layer_review=_optional_json(packet_path / "approved_layer_review.json") or [],
            smoke_test_result=result,
            smoke_test_receipt=_optional_json(packet_path / "smoke_test_receipt.json"),
            smoke_test_receipt_url=output_file_url(packet_path / "smoke_test_receipt.json")
            if (packet_path / "smoke_test_receipt.json").exists()
            else None,
            files=files,
            preview_url=_preview_url_for_source(approved_packet_folder),
            webmap_file_url=output_file_url(packet_path / "approved_webmap.json"),
            approved_review_file_url=output_file_url(packet_path / "approved_review.html"),
        ),
    )


@router.get("/catalog")
def catalog(request: Request, q: str = "flood"):
    """Search the local AutoMap layer catalog."""
    rows = search_layers(q) if q else []
    return templates.TemplateResponse(
        request,
        "catalog.html",
        _base_context(request, query=q, rows=rows),
    )


@router.get("/data-gaps")
def data_gaps(request: Request):
    """Display current AutoMap data gaps."""
    rows = list_data_gaps()
    return templates.TemplateResponse(
        request,
        "data_gaps.html",
        _base_context(request, rows=rows),
    )
