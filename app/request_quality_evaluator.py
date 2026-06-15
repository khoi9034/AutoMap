"""Quality scoring for deterministic AutoMap request understanding."""

from __future__ import annotations

from typing import Any

from app.intent_classifier import normalize_text, phrase_matches


UNSUPPORTED_PHRASES = {
    "subdivisions under review": "subdivision review data",
    "development pipeline": "current development pipeline",
    "construction activity": "current construction activity",
    "last 6 months": "recent construction or permit date range",
}


def _detect_unsupported_parts(prompt: str, missing_data: list[str]) -> list[str]:
    text = normalize_text(prompt)
    unsupported: list[str] = []
    for phrase, label in UNSUPPORTED_PHRASES.items():
        if phrase_matches(text, phrase):
            unsupported.append(label)
    for topic in missing_data:
        if topic in {"development", "permits", "planning cases", "subdivision activity"}:
            label = f"missing verified {topic} layer"
            if label not in unsupported:
                unsupported.append(label)
    return unsupported


def evaluate_request_quality(
    prompt: str,
    parsed_request: dict[str, Any],
    classification: dict[str, Any],
    spatial_plan: dict[str, Any],
    missing_data: list[str] | None = None,
) -> dict[str, Any]:
    """Score how completely AutoMap understood a request."""
    missing_data = missing_data or []
    detected_intents = classification.get("detected_intents") or []
    ambiguity_flags = list(spatial_plan.get("ambiguity_flags") or [])
    unsupported_parts = _detect_unsupported_parts(prompt, missing_data)

    score = 0.35
    if detected_intents and detected_intents != ["unknown_or_unsupported"]:
        score += 0.2
    if parsed_request.get("topics"):
        score += min(0.2, 0.06 * len(parsed_request["topics"]))
    if parsed_request.get("geography_terms"):
        score += 0.08
    if spatial_plan.get("spatial_steps"):
        score += 0.1
    if parsed_request.get("historical_year") is not None:
        score += 0.05

    score -= min(0.25, 0.06 * len(ambiguity_flags))
    score -= min(0.25, 0.07 * len(missing_data))
    score -= min(0.2, 0.06 * len(unsupported_parts))
    score = round(max(0.05, min(score, 0.99)), 3)

    if "unknown_or_unsupported" in detected_intents:
        score = min(score, 0.35)
        if "Request intent was not recognized by deterministic rules." not in unsupported_parts:
            unsupported_parts.append("Request intent was not recognized by deterministic rules.")

    return {
        "quality_score": score,
        "understood": score >= 0.55 and "unknown_or_unsupported" not in detected_intents,
        "ambiguity_flags": ambiguity_flags,
        "unsupported_parts": unsupported_parts,
        "missing_data": missing_data,
    }
