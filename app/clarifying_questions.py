"""Clarifying question generation for ambiguous AutoMap requests."""

from __future__ import annotations

from typing import Any

from app.intent_classifier import normalize_text, phrase_matches


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase_matches(text, phrase) for phrase in phrases)


def _question(question: str, reason: str, examples: list[str], trigger: str) -> dict[str, Any]:
    return {
        "question": question,
        "reason": reason,
        "examples": examples,
        "trigger": trigger,
    }


def generate_clarifying_questions(
    prompt: str,
    parsed_request: dict[str, Any],
    spatial_plan: dict[str, Any],
    missing_data: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return deterministic reviewer questions implied by ambiguous request text."""
    text = normalize_text(prompt)
    missing_data = missing_data or []
    questions: list[dict[str, Any]] = []

    if _has_any(text, ["near", "around", "close to", "nearby", "adjacent to"]):
        questions.append(
            _question(
                "What distance should count as near?",
                "The request uses proximity language without a distance threshold.",
                ["500 feet", "0.25 miles", "0.5 miles"],
                "near",
            )
        )

    if "recent" in (parsed_request.get("time_references") or []) or _has_any(text, ["last 6 months", "last year"]):
        questions.append(
            _question(
                "What time range should count as recent?",
                "The request asks for recent activity but does not define the date range or date field.",
                ["last 1 year", "last 3 years", "last 5 years"],
                "recent",
            )
        )

    if _has_any(text, ["commercial", "commercial zoning", "commercial growth"]):
        questions.append(
            _question(
                "Which zoning codes should count as commercial?",
                "Commercial zoning language needs a reviewed field and code list before final use.",
                ["CC", "GC", "Office/Commercial districts"],
                "commercial",
            )
        )

    if _has_any(text, ["best sites", "good sites", "best places", "opportunity areas", "suitable", "suitability"]):
        questions.append(
            _question(
                "Which factors should AutoMap prioritize for suitability?",
                "Suitability requests require reviewer-defined weights and assumptions.",
                ["zoning", "road access", "flood avoidance", "parcel size", "development activity"],
                "suitability",
            )
        )

    if any(topic in missing_data for topic in ["development", "permits", "planning cases", "subdivision activity"]):
        questions.append(
            _question(
                "How should AutoMap handle missing current development activity data?",
                "A current permit, planning case, or development pipeline layer is not available in the verified catalog.",
                ["use a verified legacy fallback if available", "mark as missing", "wait for a new approved source"],
                "missing_development_data",
            )
        )

    if (
        "historical" in (parsed_request.get("time_references") or [])
        or _has_any(text, ["old parcels", "old zoning", "compare to current", "compared to current"])
    ) and parsed_request.get("historical_year") is None:
        questions.append(
            _question(
                "Which historical year or archive period should be compared?",
                "Historical comparison needs a specific year or approved archive layer.",
                ["2014", "2015", "current versus historical archive"],
                "historical",
            )
        )

    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in questions:
        key = item["question"]
        if key in seen:
            continue
        unique.append(item)
        seen.add(key)
    return unique
