"""Prompt-to-map-recipe engine for AutoMap."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.data_gap_registry import upsert_data_gaps_from_recipe
from app.filter_planner import build_filter_plan, validate_filter_plan
from app.layer_matcher import match_layers
from app.prompt_parser import parse_prompt
from app.recipe_models import rejected_layer_from_match, selected_layer_from_match


def _title_from_prompt(parsed_request: dict[str, Any]) -> str:
    topics = parsed_request.get("topics") or ["map"]
    geographies = [geo["name"] for geo in parsed_request.get("geography_terms", [])]
    topic_title = ", ".join(topic.replace("_", " ").title() for topic in topics[:3])
    if geographies:
        return f"{topic_title} in {', '.join(geographies)}"
    return topic_title


def _filters(parsed_request: dict[str, Any]) -> list[dict[str, Any]]:
    filters: list[dict[str, Any]] = []
    for geography in parsed_request.get("geography_terms", []):
        if geography["type"] not in {"county", "countywide"}:
            filters.append(
                {
                    "type": "geography",
                    "field": None,
                    "value": geography["name"],
                    "notes": "Use verified jurisdiction/boundary layer to filter or clip results.",
                }
            )

    historical_year = parsed_request.get("historical_year")
    if historical_year is not None:
        filters.append(
            {
                "type": "time",
                "field": "historical_year",
                "value": historical_year,
                "notes": "Select historical catalog layers for the requested year.",
            }
        )
    elif "recent" in parsed_request.get("time_references", []):
        filters.append(
            {
                "type": "time",
                "field": None,
                "value": "recent",
                "notes": "Needs human review to define recent date range and date field.",
            }
        )

    if "commercial" in parsed_request.get("topic_details", {}).get("zoning_modifiers", []):
        filters.append(
            {
                "type": "attribute",
                "field": None,
                "value": "commercial zoning",
                "notes": "Needs review to identify the zoning class field and commercial codes.",
            }
        )

    return filters


def _spatial_operations(parsed_request: dict[str, Any], selected_layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    layer_by_category = {layer["category"]: layer for layer in selected_layers}
    operations: list[dict[str, Any]] = []
    geographies = parsed_request.get("geography_terms", [])

    if geographies and any(geo["type"] not in {"county", "countywide"} for geo in geographies):
        operations.append(
            {
                "operation": "filter_or_clip_to_geography",
                "input_layers": [layer["layer_key"] for layer in selected_layers if layer["role"] in {"base_layer", "constraint_overlay", "school_boundary_layer", "development_activity_layer"}],
                "boundary_layers": [layer["layer_key"] for layer in selected_layers if layer["role"] == "jurisdiction_filter"],
                "notes": "Use selected jurisdiction layer to limit the map to the requested place.",
            }
        )

    if "parcel" in layer_by_category and "flood" in layer_by_category:
        operations.append(
            {
                "operation": "intersect",
                "input_layers": [layer_by_category["parcel"]["layer_key"], layer_by_category["flood"]["layer_key"]],
                "output": "affected_parcels",
                "notes": "Highlight parcels intersecting the selected floodplain/floodway layer.",
            }
        )

    if parsed_request.get("analysis_intent") == "proximity":
        operations.append(
            {
                "operation": "proximity_search",
                "input_layers": [layer["layer_key"] for layer in selected_layers],
                "distance": None,
                "notes": "Needs review because the prompt does not provide a distance threshold.",
            }
        )

    return operations


def _symbology(selected_layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recommendations: list[dict[str, Any]] = []
    for layer in selected_layers:
        category = layer["category"]
        if category == "parcel":
            style = "thin gray parcel outlines; highlight selected parcels with amber fill"
        elif category == "flood":
            style = "blue transparent polygon overlay"
        elif category == "zoning":
            style = "categorized zoning fills with muted transparency"
        elif category == "schools":
            style = "distinct boundary colors by school level"
        elif category == "jurisdiction":
            style = "bold dashed municipal boundary"
        else:
            style = "simple reference styling"
        recommendations.append({"layer_key": layer["layer_key"], "style": style})
    return recommendations


def _suggested_extent(parsed_request: dict[str, Any]) -> dict[str, Any]:
    geographies = parsed_request.get("geography_terms", [])
    if geographies:
        return {
            "type": "geography",
            "value": geographies[0]["name"],
            "notes": "Fit map extent to selected geography after boundary layer review.",
        }
    return {"type": "countywide", "value": "Cabarrus County", "notes": "Default countywide extent."}


def _review_flags(parsed_request: dict[str, Any], matching: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if matching["missing_data_needed"]:
        flags.append("Missing requested data from verified layer catalog.")
    if "recent" in parsed_request.get("time_references", []):
        flags.append("Recent time range and date field need review.")
    if parsed_request.get("analysis_intent") == "proximity":
        flags.append("Proximity distance needs review.")
    if "commercial" in parsed_request.get("topic_details", {}).get("zoning_modifiers", []):
        flags.append("Commercial zoning field/code needs review.")
    if matching["confidence_score"] < 0.65:
        flags.append("Overall match confidence is below review threshold.")
    return flags


def build_recipe(
    prompt: str,
    layer_catalog: list[dict[str, Any]] | None = None,
    include_filter_intelligence: bool = True,
    persist_data_gaps: bool = True,
) -> dict[str, Any]:
    """Build a structured map recipe from a plain-English GIS request."""
    parsed_request = parse_prompt(prompt)
    matching = match_layers(parsed_request, layer_catalog)
    selected_layers = [selected_layer_from_match(layer) for layer in matching["selected_layers"]]
    rejected_layers = [rejected_layer_from_match(layer) for layer in matching["rejected_layers"]]
    review_flags = _review_flags(parsed_request, matching)

    recipe = {
        "map_title": _title_from_prompt(parsed_request),
        "user_intent": parsed_request["raw_prompt"],
        "parsed_request": parsed_request,
        "selected_layers": selected_layers,
        "rejected_layers": rejected_layers,
        "filters": _filters(parsed_request),
        "spatial_operations": _spatial_operations(parsed_request, selected_layers),
        "symbology_recommendations": _symbology(selected_layers),
        "suggested_extent": _suggested_extent(parsed_request),
        "confidence_score": matching["confidence_score"],
        "needs_review": bool(review_flags),
        "review_reasons": review_flags,
        "missing_data_needed": matching["missing_data_needed"],
        "filter_plan": {},
        "validation": {},
        "created_at": datetime.now(UTC).isoformat(),
        "notes": [
            "Recipe uses verified AutoMap layer catalog metadata only.",
            "No feature geometries were downloaded and no ArcGIS web map was created.",
        ],
    }

    if include_filter_intelligence:
        recipe["filter_plan"] = build_filter_plan(recipe, catalog_records=layer_catalog)
        validation = validate_filter_plan(recipe)
        recipe["validation"] = validation
        if validation["warnings"]:
            recipe["review_reasons"] = sorted(set([*recipe["review_reasons"], *validation["warnings"]]))
            recipe["needs_review"] = True

    if persist_data_gaps and recipe["missing_data_needed"]:
        upsert_data_gaps_from_recipe(recipe)

    return recipe
