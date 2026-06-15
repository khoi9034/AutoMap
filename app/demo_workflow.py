"""Safe local AutoMap v1 demo workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.adjustment_engine import (
    apply_adjustments_to_review_packet,
    create_adjustment_template,
    validate_adjusted_packet,
)
from app.arcgis_publisher import publish_webmap_draft
from app.recipe_engine import build_recipe
from app.request_history import record_request_history
from app.review_packet_builder import build_review_packet, save_review_packet
from app.webmap_builder import build_webmap_json
from app.webmap_exporter import save_webmap_json


DEMO_PROMPT = "Show parcels in Concord that are in the 100-year floodplain."


def _record_history_safely(**kwargs: Any) -> None:
    try:
        record_request_history(**kwargs)
    except Exception:
        # History should not block the local demo workflow.
        return


def run_demo_workflow(prompt: str = DEMO_PROMPT, ui_port: int = 8001) -> dict[str, Any]:
    """Run the safe local demo flow without real publishing."""
    recipe = build_recipe(prompt)
    _record_history_safely(
        raw_prompt=prompt,
        workflow_step="recipe",
        map_title=recipe.get("map_title"),
        status="created",
        notes={"selected_layer_count": len(recipe.get("selected_layers") or [])},
    )

    webmap_json = build_webmap_json(recipe)
    webmap_path = save_webmap_json(webmap_json)

    packet = build_review_packet(prompt)
    packet_path = save_review_packet(prompt, packet["recipe"], packet["webmap_json"])
    _record_history_safely(
        raw_prompt=prompt,
        workflow_step="review_packet",
        map_title=packet["recipe"].get("map_title"),
        status="created",
        packet_path=str(packet_path),
        notes={"webmap_path": str(webmap_path)},
    )

    adjustment_template_path = create_adjustment_template(packet_path)
    adjusted_path = apply_adjustments_to_review_packet(packet_path, adjustment_template_path)
    adjusted_validation = validate_adjusted_packet(adjusted_path)
    _record_history_safely(
        raw_prompt=prompt,
        workflow_step="adjustment",
        map_title=packet["recipe"].get("map_title"),
        status="created",
        packet_path=str(packet_path),
        adjusted_packet_path=str(adjusted_path),
        notes={"validation": adjusted_validation},
    )

    publish_result = publish_webmap_draft(adjusted_path, dry_run=True, confirm_publish=False)
    _record_history_safely(
        raw_prompt=prompt,
        workflow_step="dry_run_publish",
        map_title=packet["recipe"].get("map_title"),
        status=str(publish_result.get("status") or "dry_run"),
        packet_path=str(packet_path),
        adjusted_packet_path=str(adjusted_path),
        notes={
            "created_item": publish_result.get("created_item"),
            "published": publish_result.get("published"),
            "shared_public": publish_result.get("shared_public"),
            "shared_organization": publish_result.get("shared_organization"),
        },
    )

    preview_url = f"http://127.0.0.1:{ui_port}/preview?path={Path(adjusted_path).as_posix()}"
    return {
        "prompt": prompt,
        "map_title": recipe.get("map_title"),
        "selected_layer_count": len(recipe.get("selected_layers") or []),
        "webmap_path": str(webmap_path),
        "review_packet_path": str(packet_path),
        "adjustment_template_path": str(adjustment_template_path),
        "adjusted_packet_path": str(adjusted_path),
        "adjusted_packet_valid": adjusted_validation.get("is_valid"),
        "publish_result": publish_result,
        "preview_url": preview_url,
        "real_publish_attempted": False,
    }
