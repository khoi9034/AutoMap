"""Learned default suggestions from approved AutoMap patterns."""

from __future__ import annotations

from typing import Any

from app.pattern_library import list_clarification_defaults
from app.pattern_matcher import (
    find_similar_patterns,
    get_avoided_layers_from_patterns,
    get_common_clarification_answers,
    get_common_filter_defaults,
    get_preferred_layers_from_patterns,
)


def _question_map(questions: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(question.get("question_id")): question for question in questions if question.get("question_id")}


def _matching_stored_defaults(question_id: str, request_intelligence: dict[str, Any]) -> list[dict[str, Any]]:
    primary = request_intelligence.get("primary_intent")
    detected = set(request_intelligence.get("detected_intents") or [])
    try:
        defaults = list_clarification_defaults(limit=100)
    except Exception:
        return []
    matches = []
    for default in defaults:
        if default.get("intent") and default["intent"] not in detected and default["intent"] != primary:
            continue
        if question_id not in str(default.get("default_key") or "") and question_id not in str(default.get("question_text") or "").lower().replace(" ", "_"):
            if question_id not in {
                "near_distance" if default.get("question_type") == "distance" else "",
                "flood_layer_scope" if default.get("topic") == "flood" else "",
                "missing_development_data_decision" if default.get("topic") == "development" else "",
            }:
                continue
        matches.append(default)
    return sorted(matches, key=lambda item: float(item.get("confidence_score") or 0), reverse=True)


def suggest_clarification_defaults(
    raw_prompt: str,
    questions: list[dict[str, Any]],
    request_intelligence: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Suggest reviewable clarification defaults from approved patterns."""
    question_lookup = _question_map(questions)
    if not question_lookup:
        return {}
    patterns = find_similar_patterns(raw_prompt, request_intelligence)
    common_answers = get_common_clarification_answers(patterns)
    suggestions: dict[str, dict[str, Any]] = {}

    for answer in common_answers:
        question_id = answer.get("question_id")
        if question_id not in question_lookup:
            continue
        suggestions[question_id] = {
            "suggested_default": answer.get("answer_value"),
            "answer_label": answer.get("answer_label"),
            "default_source": "approved_patterns",
            "default_confidence": answer.get("confidence_score"),
            "explanation": f"Suggested from {answer.get('pattern_count')} approved similar request(s).",
            "similar_patterns": [pattern.get("pattern_key") for pattern in patterns[:3]],
        }

    for question_id in question_lookup:
        if question_id in suggestions:
            continue
        stored_matches = _matching_stored_defaults(question_id, request_intelligence)
        if not stored_matches:
            continue
        best = stored_matches[0]
        suggestions[question_id] = {
            "suggested_default": best.get("default_answer"),
            "answer_label": best.get("answer_label"),
            "default_source": best.get("source_pattern_key") or "clarification_defaults",
            "default_confidence": best.get("confidence_score"),
            "explanation": "Suggested from an approved clarification default.",
            "similar_patterns": [best.get("source_pattern_key")] if best.get("source_pattern_key") else [],
        }

    return suggestions


def suggest_layer_preferences(raw_prompt: str, request_intelligence: dict[str, Any]) -> dict[str, Any]:
    """Suggest preferred and avoided layer keys from similar approved patterns."""
    patterns = find_similar_patterns(raw_prompt, request_intelligence)
    return {
        "similar_patterns": [
            {
                "pattern_key": pattern.get("pattern_key"),
                "raw_prompt": pattern.get("raw_prompt"),
                "primary_intent": pattern.get("primary_intent"),
                "similarity_score": pattern.get("similarity_score"),
            }
            for pattern in patterns
        ],
        "preferred_layers": get_preferred_layers_from_patterns(patterns),
        "avoided_layers": get_avoided_layers_from_patterns(patterns),
        "common_filter_defaults": get_common_filter_defaults(patterns),
    }


def suggest_analysis_assumptions(raw_prompt: str, request_intelligence: dict[str, Any]) -> dict[str, Any]:
    """Suggest learned assumptions and missing-data decisions for review."""
    patterns = find_similar_patterns(raw_prompt, request_intelligence)
    assumptions: list[str] = []
    missing_decisions: list[Any] = []
    for pattern in patterns:
        for assumption in pattern.get("accepted_assumptions") or []:
            if str(assumption) not in assumptions:
                assumptions.append(str(assumption))
        for decision in pattern.get("missing_data_decisions") or []:
            if decision not in missing_decisions:
                missing_decisions.append(decision)
    return {
        "learned_assumptions": assumptions[:8],
        "missing_data_decisions": missing_decisions[:8],
    }


def build_learned_context(
    raw_prompt: str,
    request_intelligence: dict[str, Any],
    analysis_plan: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the recipe learned_context block without inventing layers."""
    patterns = find_similar_patterns(raw_prompt, request_intelligence)
    preferences = {
        "preferred_layers": get_preferred_layers_from_patterns(patterns),
        "avoided_layers": get_avoided_layers_from_patterns(patterns),
        "common_filter_defaults": get_common_filter_defaults(patterns),
    }
    assumptions = suggest_analysis_assumptions(raw_prompt, request_intelligence)
    confidence = max([float(pattern.get("similarity_score") or 0) for pattern in patterns] or [0.0])
    return {
        "similar_patterns": [
            {
                "pattern_key": pattern.get("pattern_key"),
                "raw_prompt": pattern.get("raw_prompt"),
                "primary_intent": pattern.get("primary_intent"),
                "topics": pattern.get("topics") or [],
                "similarity_score": pattern.get("similarity_score"),
                "final_publish_ready": pattern.get("final_publish_ready"),
            }
            for pattern in patterns
        ],
        "suggested_defaults": get_common_clarification_answers(patterns),
        "preferred_layers": preferences["preferred_layers"],
        "avoided_layers": preferences["avoided_layers"],
        "learned_assumptions": assumptions["learned_assumptions"],
        "missing_data_decisions": assumptions["missing_data_decisions"],
        "confidence_score": round(confidence, 3),
        "review_note": (
            "Learned defaults come from approved local patterns and remain reviewable; "
            "AutoMap still uses only verified catalog layers."
            if patterns
            else "No similar approved pattern found yet."
        ),
        "analysis_goal": (analysis_plan or {}).get("goal"),
    }
