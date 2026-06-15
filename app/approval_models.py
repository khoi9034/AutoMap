"""Reviewer approval model helpers for AutoMap adjusted packets."""

from __future__ import annotations

from typing import Any


APPROVAL_DECISIONS = {"approved", "needs_changes", "rejected"}
WARNING_ACTIONS = {"resolved", "accepted", "keep"}
MISSING_DATA_ACTIONS = {"accepted", "deferred", "not_applicable", "provided"}

APPROVAL_FIELDS = {
    "reviewer_name",
    "reviewer_role",
    "decision",
    "reviewer_notes",
    "warning_resolutions",
    "accepted_risks",
    "missing_data_decisions",
    "publish_ready_requested",
}

APPROVED_PACKET_FILES = {
    "approved_recipe.json",
    "approved_webmap.json",
    "approval_file.json",
    "approval_receipt.json",
    "approved_warnings.json",
    "approved_layer_review.json",
    "approved_review_summary.md",
    "approved_review.html",
}


def empty_approval() -> dict[str, Any]:
    """Return a predictable empty approval payload."""
    return {
        "reviewer_name": None,
        "reviewer_role": None,
        "decision": "needs_changes",
        "reviewer_notes": [],
        "warning_resolutions": [],
        "accepted_risks": [],
        "missing_data_decisions": [],
        "publish_ready_requested": False,
    }


def normalize_approval(approval: dict[str, Any] | None) -> dict[str, Any]:
    """Fill optional approval fields with predictable defaults."""
    normalized = empty_approval()
    for key, value in (approval or {}).items():
        if key in normalized:
            normalized[key] = value
    for list_key in ["reviewer_notes", "warning_resolutions", "accepted_risks", "missing_data_decisions"]:
        value = normalized.get(list_key)
        if value is None:
            normalized[list_key] = []
        elif not isinstance(value, list):
            normalized[list_key] = [value]
    normalized["decision"] = str(normalized.get("decision") or "needs_changes").strip().lower()
    normalized["publish_ready_requested"] = bool(normalized.get("publish_ready_requested"))
    return normalized


def validate_approval_shape(approval: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors for an approval payload."""
    errors: list[str] = []
    unknown_fields = sorted(set(approval) - APPROVAL_FIELDS)
    if unknown_fields:
        errors.append(f"Unknown approval fields: {', '.join(unknown_fields)}")

    if not isinstance(approval.get("reviewer_name"), str) or not approval.get("reviewer_name", "").strip():
        errors.append("reviewer_name is required.")
    if approval.get("reviewer_role") is not None and not isinstance(approval.get("reviewer_role"), str):
        errors.append("reviewer_role must be a string.")

    decision = str(approval.get("decision") or "").strip().lower()
    if decision not in APPROVAL_DECISIONS:
        errors.append("decision must be approved, needs_changes, or rejected.")

    if not isinstance(approval.get("publish_ready_requested"), bool):
        errors.append("publish_ready_requested must be true or false.")

    for list_key in ["reviewer_notes", "warning_resolutions", "accepted_risks", "missing_data_decisions"]:
        if not isinstance(approval.get(list_key, []), list):
            errors.append(f"{list_key} must be a list.")

    for index, resolution in enumerate(approval.get("warning_resolutions") or []):
        if not isinstance(resolution, dict):
            errors.append(f"warning_resolutions[{index}] must be an object.")
            continue
        if not str(resolution.get("warning_id") or "").strip():
            errors.append(f"warning_resolutions[{index}].warning_id is required.")
        action = str(resolution.get("action") or "").strip().lower()
        if action not in WARNING_ACTIONS:
            errors.append(f"warning_resolutions[{index}].action must be resolved, accepted, or keep.")
        if action == "keep" and not str(resolution.get("note") or "").strip():
            errors.append(f"warning_resolutions[{index}].note is required when action is keep.")

    for index, decision_item in enumerate(approval.get("missing_data_decisions") or []):
        if not isinstance(decision_item, dict):
            errors.append(f"missing_data_decisions[{index}] must be an object.")
            continue
        if not str(decision_item.get("item") or "").strip():
            errors.append(f"missing_data_decisions[{index}].item is required.")
        action = str(decision_item.get("action") or "").strip().lower()
        if action not in MISSING_DATA_ACTIONS:
            errors.append(
                f"missing_data_decisions[{index}].action must be accepted, deferred, not_applicable, or provided."
            )
        if not str(decision_item.get("note") or "").strip():
            errors.append(f"missing_data_decisions[{index}].note is required.")

    return errors
