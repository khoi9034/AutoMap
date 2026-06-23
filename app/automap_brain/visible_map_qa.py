"""Brain v2 wrapper around bounded visible-map QA."""

from __future__ import annotations

from typing import Any

from app.visible_map_qa import visible_map_qa


def run_visible_map_qa(preview_config: dict[str, Any] | None, recipe: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    qa = visible_map_qa(preview_config, recipe, **kwargs)
    qa["qa_status"] = "visible" if int(qa.get("visible_feature_total") or 0) > 0 else "no_visible_features"
    qa["brain_version"] = "automap_brain_v2"
    return qa
