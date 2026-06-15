"""Plan GIS operations implied by deterministic request intent."""

from __future__ import annotations

from typing import Any

from app.intent_classifier import normalize_text, phrase_matches


def _has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase_matches(text, phrase) for phrase in phrases)


def _geography_names(parsed_request: dict[str, Any]) -> list[str]:
    return [geo.get("name", "") for geo in parsed_request.get("geography_terms") or [] if isinstance(geo, dict)]


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def plan_spatial_intent(
    prompt: str,
    parsed_request: dict[str, Any],
    classification: dict[str, Any],
) -> dict[str, Any]:
    """Convert request language and classified intent into GIS operation steps."""
    text = normalize_text(prompt)
    detected_intents = classification.get("detected_intents") or []
    spatial_relationships: list[dict[str, Any]] = []
    spatial_steps: list[dict[str, Any]] = []
    attribute_steps: list[dict[str, Any]] = []
    constraints: list[str] = []
    opportunities: list[str] = []
    ambiguity_flags: list[str] = []
    assumptions: list[str] = []
    blockers: list[str] = []

    geographies = _geography_names(parsed_request)
    if geographies:
        spatial_relationships.append(
            {
                "relationship": "within_geography",
                "target": geographies[0],
                "operation": "clip_or_filter_to_boundary",
            }
        )
        spatial_steps.append(
            {
                "operation": "clip_or_filter_to_geography",
                "description": f"Limit selected layers to {geographies[0]} using a verified boundary layer.",
                "needs_review": False,
            }
        )

    if _has_any(text, ["near", "around", "close to", "nearby", "adjacent to"]):
        spatial_relationships.append(
            {
                "relationship": "near",
                "operation": "buffer_or_proximity",
                "distance": None,
            }
        )
        spatial_steps.append(
            {
                "operation": "buffer_or_proximity",
                "description": "Select or review features within a human-confirmed distance threshold.",
                "needs_review": True,
                "review_reason": "The request uses proximity language without a distance.",
            }
        )
        _append_unique(ambiguity_flags, "near_distance_threshold_missing")

    if "flood_exposure" in detected_intents:
        if _has_any(text, ["avoid flood", "avoid flood zones", "not in flood", "not in floodplain", "exclude flood", "outside flood"]):
            spatial_relationships.append(
                {
                    "relationship": "exclude_constraint",
                    "target": "flood layers",
                    "operation": "exclude_intersecting_features",
                }
            )
            spatial_steps.append(
                {
                    "operation": "exclude_constrained_areas",
                    "description": "Exclude parcels or candidate areas that intersect flood hazard layers.",
                    "needs_review": False,
                }
            )
            _append_unique(constraints, "avoid flood hazard areas")
        else:
            spatial_relationships.append(
                {
                    "relationship": "intersects",
                    "target": "flood layers",
                    "operation": "intersect",
                }
            )
            spatial_steps.append(
                {
                    "operation": "intersect",
                    "description": "Identify features intersecting the selected flood hazard layer.",
                    "needs_review": False,
                }
            )
            _append_unique(constraints, "flood hazard exposure")

    if "school_district_lookup" in detected_intents:
        spatial_relationships.append(
            {
                "relationship": "overlay",
                "target": "school district layers",
                "operation": "overlay_school_boundaries",
            }
        )
        spatial_steps.append(
            {
                "operation": "overlay_school_boundaries",
                "description": "Overlay elementary, middle, and high school district boundaries where available.",
                "needs_review": False,
            }
        )
        _append_unique(constraints, "school district context")

    if "zoning_review" in detected_intents:
        spatial_steps.append(
            {
                "operation": "select_by_attribute",
                "description": "Use zoning attributes after field review to isolate requested zoning classes.",
                "needs_review": "commercial" in text or "industrial" in text or "residential" in text,
            }
        )
        if _has_any(text, ["commercial", "industrial", "residential", "allowed use"]):
            attribute_steps.append(
                {
                    "operation": "zoning_code_filter",
                    "description": "Confirm the zoning field and requested zoning code list before final use.",
                    "needs_review": True,
                }
            )
            _append_unique(ambiguity_flags, "zoning_code_definition_needed")

    if "transportation_corridor" in detected_intents:
        spatial_steps.append(
            {
                "operation": "overlay_transportation_access",
                "description": "Overlay road, centerline, corridor, or traffic context layers.",
                "needs_review": "high traffic" in text or "aadt" in text,
            }
        )
        _append_unique(opportunities, "transportation access")
        if _has_any(text, ["high traffic", "aadt"]):
            attribute_steps.append(
                {
                    "operation": "traffic_attribute_review",
                    "description": "Confirm the AADT or traffic threshold for high-traffic corridors.",
                    "needs_review": True,
                }
            )

    if "development_activity" in detected_intents or "development_pressure" in detected_intents:
        spatial_steps.append(
            {
                "operation": "overlay_development_activity",
                "description": "Overlay verified development activity layers if available, otherwise report missing data.",
                "needs_review": True,
            }
        )
        _append_unique(opportunities, "development activity signal")

    if "growth_suitability" in detected_intents:
        spatial_steps.append(
            {
                "operation": "rank_or_suitability_scoring",
                "description": "Combine opportunities and constraints into a reviewer-defined suitability screen.",
                "needs_review": True,
            }
        )
        _append_unique(ambiguity_flags, "suitability_scoring_assumptions_needed")
        _append_unique(opportunities, "growth suitability candidates")

    if "historical_comparison" in detected_intents:
        spatial_relationships.append(
            {
                "relationship": "compare_time_periods",
                "operation": "compare_current_vs_historical",
                "historical_year": parsed_request.get("historical_year"),
            }
        )
        spatial_steps.append(
            {
                "operation": "compare_current_vs_historical",
                "description": "Compare requested historical layers with current layers only after reviewer confirms scope.",
                "needs_review": parsed_request.get("historical_year") is None,
            }
        )

    if "recent" in (parsed_request.get("time_references") or []):
        attribute_steps.append(
            {
                "operation": "recent_date_filter",
                "description": "Apply a date filter after the reviewer confirms the date field and time range.",
                "needs_review": True,
            }
        )
        _append_unique(ambiguity_flags, "recent_time_range_needed")

    if "infrastructure_access" in detected_intents:
        blockers.append("Utility or infrastructure capacity data is not assumed unless a verified catalog layer exists.")
        _append_unique(constraints, "infrastructure access requires verified source")

    if not spatial_steps:
        assumptions.append("Treat request as a reference map unless the reviewer adds a spatial analysis instruction.")

    return {
        "spatial_relationships": spatial_relationships,
        "spatial_steps": spatial_steps,
        "attribute_steps": attribute_steps,
        "extracted_constraints": constraints,
        "extracted_opportunities": opportunities,
        "ambiguity_flags": ambiguity_flags,
        "assumptions": assumptions,
        "blockers": blockers,
    }
