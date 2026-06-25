"""Fallback planning for AutoMap Brain Kernel v1."""

from __future__ import annotations

from typing import Any


def plan_fallbacks(
    request_plan: dict[str, Any],
    operation_plan: dict[str, Any] | None = None,
    qa_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a deterministic fallback strategy for a request plan."""
    operation = operation_plan or {}
    qa = qa_result or {}
    request_type = str(request_plan.get("request_type") or "")
    fallbacks: list[dict[str, Any]] = []

    if request_type == "zoning_context":
        fallbacks.append(
            {
                "trigger": "commercial_values_uncertain",
                "action": "show_zoning_context",
                "reason": "Commercial zoning values were not confidently identified.",
                "shown_instead": "Muted zoning context clipped to the AOI.",
            }
        )
        fallbacks.append(
            {
                "trigger": "major_road_class_unavailable",
                "action": "show_clipped_road_context",
                "reason": "Major-road classification field is unavailable.",
                "shown_instead": "Road context clipped to the requested area.",
            }
        )
    elif request_type == "floodplain_screening":
        fallbacks.append(
            {
                "trigger": "intersection_unavailable",
                "action": "show_floodplain_context_only",
                "reason": "Parcel-floodplain intersection could not be completed safely.",
                "shown_instead": "100-year floodplain and requested boundary context.",
            }
        )
    elif request_type == "historical_lookup":
        fallbacks.append(
            {
                "trigger": "historical_layer_unavailable",
                "action": "return_data_limited_status",
                "reason": "Matching historical source is not available.",
                "shown_instead": "No current layer is relabeled as historical.",
            }
        )
    elif request_type in {"unsupported", "unsupported_area", "unsupported_request"}:
        fallbacks.append(
            {
                "trigger": "outside_supported_scope",
                "action": "return_unsupported_area",
                "reason": "Live workflows are scoped to Cabarrus County, NC.",
                "shown_instead": "Guidance to try a Cabarrus County address, parcel, or planning request.",
            }
        )

    qa_warnings = qa.get("warnings") or []
    fallback_used = bool(qa.get("fallback_used")) or operation.get("operation") == "context_only"
    return {
        "fallback_used": fallback_used,
        "fallback_options": fallbacks,
        "qa_warnings": qa_warnings,
        "refinement_guidance": [
            "Add a Cabarrus County place, parcel/PIN, address, or narrower geography.",
            "Use table mode for records/columns and map mode for spatial context.",
        ],
    }
