"""Transparent deterministic suitability scoring templates."""

from __future__ import annotations

from typing import Any

from app.scenario_models import ScenarioFactor


def _keys_for_categories(selected_layers: list[dict[str, Any]], categories: set[str]) -> list[str]:
    return [
        str(layer.get("layer_key"))
        for layer in selected_layers
        if layer.get("layer_key") and str(layer.get("category") or "") in categories
    ]


def _factor(
    key: str,
    label: str,
    factor_type: str,
    categories: set[str],
    selected_layers: list[dict[str, Any]],
    weight: float,
    direction: str,
    method: str,
    *,
    needs_review: bool = True,
    notes: str = "",
) -> dict[str, Any]:
    return ScenarioFactor(
        factor_key=key,
        factor_label=label,
        factor_type=factor_type,  # type: ignore[arg-type]
        layer_keys=_keys_for_categories(selected_layers, categories),
        suggested_weight=weight,
        direction=direction,  # type: ignore[arg-type]
        scoring_method=method,  # type: ignore[arg-type]
        needs_review=needs_review,
        notes=notes,
    ).to_dict()


def build_scoring_framework(
    scenario_type: str,
    selected_layers: list[dict[str, Any]],
    parsed_request: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build a deterministic scoring framework for a scenario."""
    parsed_request = parsed_request or {}
    commercial = "commercial" in (parsed_request.get("topic_details", {}).get("zoning_modifiers") or [])

    if scenario_type == "commercial_growth_suitability":
        return [
            _factor(
                "commercial_zoning",
                "Commercial or general business zoning",
                "opportunity",
                {"zoning"},
                selected_layers,
                0.3,
                "presence_is_good",
                "attribute_score",
                notes="Reviewer must confirm which zoning codes count as commercial.",
            ),
            _factor(
                "high_aadt",
                "High AADT / traffic corridor",
                "opportunity",
                {"transportation"},
                selected_layers,
                0.22,
                "higher_is_better",
                "attribute_score",
                notes="Reviewer must confirm high-traffic threshold.",
            ),
            _factor(
                "road_access",
                "Road access / centerline proximity",
                "opportunity",
                {"transportation"},
                selected_layers,
                0.18,
                "lower_is_better",
                "proximity_score",
                notes="Reviewer must confirm distance to roads.",
            ),
            _factor(
                "stip_context",
                "Nearby planned transportation projects",
                "context",
                {"transportation_projects"},
                selected_layers,
                0.05,
                "reference_only",
                "reference_context",
                notes="STIP is context only, not a development pipeline source.",
            ),
            _factor(
                "flood_constraint",
                "Floodplain or floodway avoidance",
                "constraint",
                {"flood"},
                selected_layers,
                -0.25,
                "presence_is_bad",
                "intersection_penalty",
                notes="Reviewer must confirm floodway, 100-year, 500-year, or all flood hazard layers.",
            ),
            _factor(
                "development_proxy",
                "Plan-review or Accela activity",
                "proxy",
                {"development_activity_proxy", "planning_cases"},
                selected_layers,
                0.0,
                "reference_only",
                "reference_context",
                notes="Proxy/context only; not permit approval or completed development.",
            ),
            _factor(
                "missing_current_permits",
                "Missing official current permit data",
                "constraint",
                set(),
                selected_layers,
                -0.1,
                "reference_only",
                "not_executable_yet",
                needs_review=True,
                notes="Current permits remain unresolved unless an official verified source is added.",
            ),
        ]

    if scenario_type == "residential_growth_suitability":
        return [
            _factor("residential_zoning", "Residential zoning", "opportunity", {"zoning"}, selected_layers, 0.28, "presence_is_good", "attribute_score"),
            _factor("road_access", "Road access", "opportunity", {"transportation"}, selected_layers, 0.2, "lower_is_better", "proximity_score"),
            _factor("flood_constraint", "Floodway/floodplain avoidance", "constraint", {"flood"}, selected_layers, -0.25, "presence_is_bad", "intersection_penalty"),
            _factor("school_context", "School district context", "context", {"schools"}, selected_layers, 0.0, "reference_only", "reference_context", notes="School capacity/utilization is not available unless a verified source is added."),
            _factor("development_proxy", "Development activity proxy", "proxy", {"development_activity_proxy"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("missing_current_permits", "Missing official current permit data", "constraint", set(), selected_layers, -0.1, "reference_only", "not_executable_yet"),
        ]

    if scenario_type == "development_pressure":
        return [
            _factor("development_proxy", "Plan-review or Accela activity", "proxy", {"development_activity_proxy"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("planning_cases", "Planning cases where available", "context", {"planning_cases"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("aadt_corridors", "AADT / transportation corridors", "context", {"transportation"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("zoning_context", "Zoning context", "context", {"zoning"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("parcel_context", "Parcel context", "context", {"parcel"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("missing_current_permits", "Missing official current permit data", "constraint", set(), selected_layers, -0.1, "reference_only", "not_executable_yet"),
        ]

    if scenario_type in {"constraint_exposure", "flood_avoidance"}:
        return [
            _factor("floodway", "Floodway exposure", "constraint", {"flood"}, selected_layers, -0.35, "presence_is_bad", "intersection_penalty"),
            _factor("floodplain_100", "100-year floodplain exposure", "constraint", {"flood"}, selected_layers, -0.3, "presence_is_bad", "intersection_penalty"),
            _factor("floodplain_500", "500-year floodplain exposure", "constraint", {"flood"}, selected_layers, -0.15, "presence_is_bad", "intersection_penalty"),
            _factor("school_context", "School district context", "context", {"schools"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("hydrology_context", "Water or hydrology context", "context", {"environmental"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("zoning_limitations", "Zoning limitations", "context", {"zoning"}, selected_layers, 0.0, "reference_only", "reference_context"),
        ]

    if scenario_type == "transportation_access":
        return [
            _factor("aadt_corridors", "AADT / traffic corridor context", "context", {"transportation"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("road_access", "Road access", "opportunity", {"transportation"}, selected_layers, 0.25, "lower_is_better", "proximity_score"),
            _factor("stip_context", "STIP planned project context", "context", {"transportation_projects"}, selected_layers, 0.0, "reference_only", "reference_context"),
        ]

    if scenario_type == "planning_case_context":
        return [
            _factor("planning_cases", "Planning case context", "context", {"planning_cases"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("zoning_context", "Zoning context", "context", {"zoning"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("jurisdiction_context", "Jurisdiction context", "context", {"jurisdiction"}, selected_layers, 0.0, "reference_only", "reference_context"),
        ]

    if scenario_type == "school_impact_context":
        return [
            _factor("school_districts", "School district context", "context", {"schools"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("residential_zoning", "Residential zoning context", "context", {"zoning"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("development_proxy", "Development activity proxy", "proxy", {"development_activity_proxy"}, selected_layers, 0.0, "reference_only", "reference_context"),
        ]

    if scenario_type == "historical_change_context":
        return [
            _factor("historical_layers", "Historical catalog layers", "context", {"parcel", "zoning"}, selected_layers, 0.0, "reference_only", "reference_context"),
            _factor("current_layers", "Current comparison layers", "context", {"parcel", "zoning"}, selected_layers, 0.0, "reference_only", "reference_context"),
        ]

    return [
        _factor(
            "unsupported",
            "Unsupported scenario",
            "context",
            set(),
            selected_layers,
            0.0,
            "reference_only",
            "not_executable_yet",
            needs_review=True,
            notes="AutoMap could not classify this as a supported planning scenario.",
        )
    ]
