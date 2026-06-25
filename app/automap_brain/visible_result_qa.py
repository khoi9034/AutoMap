"""Visible-result QA gate for AutoMap Brain Kernel v1."""

from __future__ import annotations

from typing import Any

from app.automap_brain.visible_map_qa import run_visible_map_qa


def run_visible_result_qa(preview_config: dict[str, Any] | None, recipe: dict[str, Any]) -> dict[str, Any]:
    """Run QA and add kernel-level pass/fail guidance."""
    qa = run_visible_map_qa(preview_config, recipe)
    warnings = list(qa.get("warnings") or [])
    visible_total = int(qa.get("visible_feature_total") or 0)
    request_type = str((recipe.get("request_plan") or {}).get("request_type") or recipe.get("request_type") or "")
    has_primary = any(
        isinstance(row, dict)
        and row.get("visible") is not False
        and str(row.get("expected_role") or "") in {"affected_parcels", "primary_result", "commercial_zoning", "route_line"}
        for row in qa.get("visible_feature_summary") or []
    )
    if visible_total <= 0:
        warnings.append("No visible operational features were confirmed.")
    if request_type in {"floodplain_screening", "zoning_context", "proximity"} and not has_primary:
        warnings.append("Primary result layer was not confirmed visible.")
    qa["kernel_version"] = "automap_brain_kernel_v1"
    qa["passes_kernel_gate"] = visible_total > 0 and (has_primary or request_type in {"general_map", "table_request"})
    qa["warnings"] = sorted({str(item) for item in warnings if item})
    return qa
