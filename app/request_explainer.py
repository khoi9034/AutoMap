"""Human-readable explanations for AutoMap request decisions."""

from __future__ import annotations

from typing import Any


def _list_text(values: list[str], fallback: str) -> str:
    return ", ".join(values) if values else fallback


def build_reasoning_summary(
    request_intelligence: dict[str, Any],
    analysis_plan: dict[str, Any],
    selected_layers: list[dict[str, Any]] | None = None,
    missing_data: list[str] | None = None,
) -> str:
    """Summarize how AutoMap interpreted the request without claiming hidden analysis."""
    primary = request_intelligence.get("primary_intent") or "unknown_or_unsupported"
    intents = request_intelligence.get("detected_intents") or [primary]
    required_layers = analysis_plan.get("required_layers") or []
    layer_count = len(selected_layers or [])
    missing = missing_data or []

    summary = (
        f"AutoMap interpreted the request as {primary} with supporting intents "
        f"{_list_text([intent for intent in intents if intent != primary], 'none')}. "
        f"It planned around required layer topics: {_list_text(required_layers, 'none')} "
        f"and selected {layer_count} verified catalog layer(s)."
    )
    if missing:
        summary += f" Missing verified data was reported for: {_list_text(missing, 'none')}."
    if request_intelligence.get("clarifying_questions"):
        summary += " Human review questions were generated for ambiguous terms."
    return summary


def intent_reasons_for_layer(
    layer: dict[str, Any],
    topic: str,
    request_intelligence: dict[str, Any] | None,
    analysis_plan: dict[str, Any] | None,
) -> list[str]:
    """Return intent-specific reasons for selecting a layer topic."""
    reasons: list[str] = []
    if not request_intelligence or not analysis_plan:
        return reasons

    required_layers = set(analysis_plan.get("required_layers") or [])
    optional_layers = set(analysis_plan.get("optional_layers") or [])
    category = layer.get("category") or topic

    if topic in required_layers or category in required_layers:
        reasons.append(f"{topic} is required by the detected request intent")
    if topic in optional_layers or category in optional_layers:
        reasons.append(f"{topic} supports the detected request intent")

    detected_intents = request_intelligence.get("detected_intents") or []
    if detected_intents:
        reasons.append(f"supports intent(s): {', '.join(detected_intents[:3])}")
    return reasons


def why_selected(layer: dict[str, Any], topic: str, request_intelligence: dict[str, Any] | None) -> str:
    """Explain why a selected layer belongs in the recipe."""
    name = layer.get("layer_name") or layer.get("layer_key") or "Layer"
    source_status = layer.get("source_status") or "unknown source"
    verified = "verified" if layer.get("is_verified") else "catalog"
    primary = (request_intelligence or {}).get("primary_intent") or "request"
    return f"{name} was selected because it matched the {topic} topic for the {primary} intent and is a {verified} {source_status} catalog record."


def why_not_legacy(layer: dict[str, Any], request_intelligence: dict[str, Any] | None) -> str:
    """Explain modern-vs-legacy preference without deleting fallback metadata."""
    if int(layer.get("source_priority") or 999) == 1:
        return "A verified new OpenData layer is preferred over legacy fallback records when available."
    if layer.get("is_historical"):
        return "Historical legacy layer was allowed because the request asked for historical context or a specific year."
    if str(layer.get("source_status") or "").startswith("legacy"):
        return "Legacy layer was used only as a fallback because no better verified modern equivalent was selected for this topic."
    return "Layer is not a legacy fallback."


def review_notes_for_layer(layer: dict[str, Any], topic: str) -> list[str]:
    """Return deterministic review notes for a selected layer."""
    notes: list[str] = []
    if layer.get("is_group_layer") and not layer.get("is_feature_layer"):
        notes.append("Group layer selected; reviewer should confirm a child feature layer is not more appropriate.")
    if layer.get("is_historical"):
        notes.append("Historical layer; do not use for current conditions unless the request asks for archive context.")
    if topic in {"development", "traffic", "utility"}:
        notes.append("Reviewer should confirm field availability and definitions before final use.")
    if not layer.get("layer_url"):
        notes.append("Layer URL is missing and must be resolved before preview or publishing.")
    return notes


def rejected_layer_reason(
    layer: dict[str, Any],
    selected_layers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Explain why a catalog candidate was rejected."""
    selected_same_category = [
        selected for selected in selected_layers if selected.get("category") == layer.get("category")
    ]
    superseded = bool(
        selected_same_category
        and str(layer.get("source_status") or "").startswith("legacy")
        and any(int(selected.get("source_priority") or 999) == 1 for selected in selected_same_category)
    )
    reason = "Lower scoring match than selected catalog layer."
    if superseded:
        reason = "Legacy or historical candidate was superseded by a verified new OpenData layer."
    elif layer.get("is_historical"):
        reason = "Historical candidate was not selected for a current request."
    elif layer.get("is_group_layer") and not layer.get("is_feature_layer"):
        reason = "Group layer scored lower than available feature-layer candidates."
    return {
        "reason_rejected": reason,
        "superseded_by_new_opendata": superseded,
        "is_legacy_or_historical": bool(str(layer.get("source_status") or "").startswith("legacy") or layer.get("is_historical")),
    }
