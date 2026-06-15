"""FastAPI routes for AutoMap's local review UI."""

from __future__ import annotations

import json
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
from app.arcgis_publisher import publish_webmap_draft
from app.data_gap_registry import data_gap_records_from_recipe, list_data_gaps
from app.layer_catalog_store import search_layers
from app.packet_index import (
    build_preview_config,
    find_latest_packet,
    list_adjusted_packets,
    list_review_packets,
)
from app.recipe_engine import build_recipe
from app.review_packet_builder import (
    build_layer_review_table,
    build_review_packet,
    save_review_packet,
    validate_review_packet,
)
from app.ui_models import (
    CATALOG_SEARCH_EXAMPLES,
    EXAMPLE_PROMPTS,
    PROJECT_TITLE,
    SAFETY_BANNER,
    output_file_url,
    repo_root,
)
from app.webmap_exporter import export_recipe_and_webmap


router = APIRouter()
templates = Jinja2Templates(directory=str(repo_root() / "templates"))


def _base_context(request: Request, **extra: Any) -> dict[str, Any]:
    context = {
        "request": request,
        "project_title": PROJECT_TITLE,
        "safety_banner": SAFETY_BANNER,
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
    )


@router.get("/")
def index(request: Request):
    """Render the local UI home page."""
    review_packets = list_review_packets()[:5]
    adjusted_packets = list_adjusted_packets()[:5]
    latest_packet = find_latest_packet()
    return templates.TemplateResponse(
        request,
        "index.html",
        _base_context(
            request,
            review_packets=review_packets,
            adjusted_packets=adjusted_packets,
            latest_packet=latest_packet,
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
    packet_path = Path(packet_folder)
    adjustment_path = packet_path / "adjustments.ui.yaml"
    adjustment_path.write_text(adjustment_yaml, encoding="utf-8")
    adjusted_path = apply_adjustments_to_review_packet(packet_folder, adjustment_path)
    validation = validate_adjusted_packet(adjusted_path)
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


@router.post("/publish-dry-run")
def publish_dry_run(request: Request, adjusted_packet_folder: str = Form(...)):
    """Run dry-run publishing only; never real publish from the UI."""
    result = publish_webmap_draft(adjusted_packet_folder, dry_run=True, confirm_publish=False)
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
