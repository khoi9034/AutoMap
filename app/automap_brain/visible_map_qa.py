"""Brain v2 wrapper around bounded visible-map QA."""

from __future__ import annotations

from typing import Any

from app.visible_map_qa import visible_map_qa


def run_visible_map_qa(preview_config: dict[str, Any] | None, recipe: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    qa = visible_map_qa(preview_config, recipe, **kwargs)
    failed_rows = [
        row
        for row in qa.get("visible_feature_summary") or []
        if isinstance(row, dict) and row.get("visible") is not False and row.get("query_status") in {"query_failed", "source_unavailable"}
    ]
    qa["qa_status"] = "visible" if int(qa.get("visible_feature_total") or 0) > 0 else "query_failed" if failed_rows else "no_visible_features"
    qa["brain_version"] = "automap_brain_v2"
    return qa
