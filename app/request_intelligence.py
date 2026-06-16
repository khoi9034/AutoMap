"""Request intelligence orchestrator for deterministic AutoMap recipes."""

from __future__ import annotations

from typing import Any

from app.clarifying_questions import generate_clarifying_questions
from app.intent_classifier import INTENT_LAYER_REQUIREMENTS, classify_intents
from app.parcel_input_parser import parse_parcel_input
from app.prompt_parser import parse_prompt
from app.request_explainer import build_reasoning_summary
from app.request_quality_evaluator import evaluate_request_quality
from app.scenario_classifier import classify_scenario
from app.spatial_intent_planner import plan_spatial_intent


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _layer_requirements(
    parsed_request: dict[str, Any],
    classification: dict[str, Any],
    spatial_plan: dict[str, Any],
) -> tuple[list[str], list[str]]:
    required: list[str] = []
    optional: list[str] = []

    for topic in parsed_request.get("topics") or []:
        _append_unique(required, topic)

    if parsed_request.get("geography_terms") and any(
        geo.get("type") not in {"county", "countywide"}
        for geo in parsed_request.get("geography_terms") or []
        if isinstance(geo, dict)
    ):
        _append_unique(required, "jurisdiction")

    for intent in classification.get("detected_intents") or []:
        requirement = INTENT_LAYER_REQUIREMENTS.get(intent, {})
        for topic in requirement.get("required") or []:
            _append_unique(required, topic)
        for topic in requirement.get("optional") or []:
            if topic not in required:
                _append_unique(optional, topic)

    if parsed_request.get("historical_year") is not None and not parsed_request.get("topics"):
        _append_unique(required, "parcel")
        _append_unique(required, "zoning")

    constraints = " ".join(spatial_plan.get("extracted_constraints") or [])
    if "flood" in constraints and "flood" not in required:
        _append_unique(optional, "flood")

    return required, optional


def _goal_from_intent(classification: dict[str, Any], parsed_request: dict[str, Any]) -> str:
    primary = classification.get("primary_intent") or "unknown_or_unsupported"
    geographies = [
        geo.get("name")
        for geo in parsed_request.get("geography_terms") or []
        if isinstance(geo, dict) and geo.get("name")
    ]
    place = f" for {geographies[0]}" if geographies else ""
    return f"Create a draft {primary.replace('_', ' ')} map recipe{place} using verified catalog layers."


def _blockers(missing_data: list[str], spatial_plan: dict[str, Any]) -> list[str]:
    blockers = list(spatial_plan.get("blockers") or [])
    for topic in missing_data:
        blockers.append(f"Missing verified catalog layer for {topic}.")
    return sorted(set(blockers))


def _scenario_context(prompt: str, parsed_request: dict[str, Any], spatial_plan: dict[str, Any]) -> dict[str, Any]:
    scenario = classify_scenario(prompt, parsed_request)
    scenario_type = scenario.get("scenario_type")
    detected = scenario_type != "unsupported_scenario"
    return {
        "scenario_detected": detected,
        "scenario_type": scenario_type,
        "recommended_scenario_workflow": (
            "Use --make-scenario or the Scenarios page to build a transparent scoring framework."
            if detected
            else None
        ),
        "suitability_factors": spatial_plan.get("extracted_opportunities") or [],
        "constraint_factors": spatial_plan.get("extracted_constraints") or [],
        "proxy_context": "Proxy sources remain context only and do not resolve official approvals.",
        "confidence_score": scenario.get("confidence_score"),
        "classification_reasons": scenario.get("classification_reasons") or [],
    }


def build_request_intelligence(
    prompt: str,
    parsed_request: dict[str, Any] | None = None,
    missing_data: list[str] | None = None,
    selected_layers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return enriched deterministic request understanding and an analysis plan."""
    parsed_request = parsed_request or parse_prompt(prompt)
    missing_data = sorted(set(missing_data or []))
    classification = classify_intents(prompt, parsed_request)
    spatial_plan = plan_spatial_intent(prompt, parsed_request, classification)
    required_layers, optional_layers = _layer_requirements(parsed_request, classification, spatial_plan)
    questions = generate_clarifying_questions(prompt, parsed_request, spatial_plan, missing_data)
    quality = evaluate_request_quality(prompt, parsed_request, classification, spatial_plan, missing_data)
    parcel_parse = parse_parcel_input(prompt)

    analysis_plan = {
        "goal": _goal_from_intent(classification, parsed_request),
        "required_layers": required_layers,
        "optional_layers": optional_layers,
        "spatial_steps": spatial_plan.get("spatial_steps") or [],
        "attribute_steps": spatial_plan.get("attribute_steps") or [],
        "assumptions": spatial_plan.get("assumptions") or [],
        "blockers": _blockers(missing_data, spatial_plan),
        "review_questions": questions,
    }

    request_intelligence = {
        "detected_intents": classification["detected_intents"],
        "confidence_by_intent": classification["confidence_by_intent"],
        "primary_intent": classification["primary_intent"],
        "secondary_intents": classification["secondary_intents"],
        "extracted_constraints": spatial_plan.get("extracted_constraints") or [],
        "extracted_opportunities": spatial_plan.get("extracted_opportunities") or [],
        "spatial_relationships": spatial_plan.get("spatial_relationships") or [],
        "ambiguity_flags": quality.get("ambiguity_flags") or [],
        "clarifying_questions": questions,
        "reasoning_summary": "",
        "unsupported_parts": quality.get("unsupported_parts") or [],
        "matched_phrases_by_intent": classification.get("matched_phrases_by_intent") or {},
        "quality_score": quality.get("quality_score"),
        "understood": quality.get("understood"),
        "scenario_context": _scenario_context(prompt, parsed_request, spatial_plan),
        "parcel_context": {
            "parcel_context_detected": bool(parcel_parse.get("parcel_intent")),
            "input_type": parcel_parse.get("input_type"),
            "parsed_identifier_count": len(parcel_parse.get("parsed_identifiers") or []),
            "address_candidate_count": len(parcel_parse.get("address_candidates") or []),
            "owner_lookup_requested": bool(parcel_parse.get("owner_lookup_requested")),
            "privacy_sensitive": bool(parcel_parse.get("privacy_sensitive")),
            "warnings": parcel_parse.get("warnings") or [],
            "recommended_workflow": (
                "Use the Parcel Workspace to safely parse, match, and review parcel-centered map context."
                if parcel_parse.get("parcel_intent")
                else None
            ),
        },
    }
    request_intelligence["reasoning_summary"] = build_reasoning_summary(
        request_intelligence,
        analysis_plan,
        selected_layers=selected_layers,
        missing_data=missing_data,
    )

    return {
        "request_intelligence": request_intelligence,
        "analysis_plan": analysis_plan,
    }
