"""Prompt-to-map-recipe engine for AutoMap."""

from __future__ import annotations

from datetime import UTC, datetime
from time import perf_counter
from pathlib import Path
from typing import Any

from app.data_gap_registry import upsert_data_gaps_from_recipe
from app.data_gap_resolver import safe_gap_context_for_recipe
from app.default_suggester import build_learned_context
from app.filter_planner import build_filter_plan, validate_filter_plan
from app.geometry_utils import buffer_extent, geojson_extent
from app.layer_matcher import match_layers
from app.automap_brain.map_recipe_builder import attach_brain_recipe_metadata
from app.automap_brain.request_parser import build_request_plan
from app.parcel_context_engine import create_parcel_set, fetch_selected_parcels
from app.parcel_input_parser import parse_parcel_input
from app.prompt_parser import parse_prompt
from app.proximity_engine import build_proximity_context
from app.recipe_models import rejected_layer_from_match, selected_layer_from_match
from app.request_intelligence import build_request_intelligence
from app.source_usage_intelligence import build_source_coverage, enrich_selected_layers_with_source_usage
from app.ui_models import output_file_url, repo_root


PARCEL_NOT_MATCHED_WARNING = (
    "This parcel ID was not matched. AutoMap cannot zoom to or analyze the parcel until a valid "
    "parcel/PIN/address is provided."
)
ADDRESS_NOT_MATCHED_WARNING = (
    "Address not found in Cabarrus County records. AutoMap's live address lookup currently supports "
    "Cabarrus County, NC only. Try a Cabarrus County address, parcel/PIN, or planning request."
)


def _elapsed_ms(start: float) -> int:
    return int(round((perf_counter() - start) * 1000))


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


def _spatial_operations(
    parsed_request: dict[str, Any],
    selected_layers: list[dict[str, Any]],
    analysis_plan: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
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

    existing_operations = {operation["operation"] for operation in operations}
    for planned_step in (analysis_plan or {}).get("spatial_steps") or []:
        operation_name = planned_step.get("operation")
        if operation_name and operation_name not in existing_operations:
            operations.append(planned_step)
            existing_operations.add(operation_name)

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


def _local_output_path(path: str | None) -> Path | None:
    if not path:
        return None
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return repo_root() / candidate


def _selected_parcel_derived_output(parcel_context: dict[str, Any]) -> dict[str, Any] | None:
    path = parcel_context.get("selected_parcel_geojson_path") or parcel_context.get("geometry_output_path")
    if not path:
        return None
    return {
        "type": "selected_parcels_geojson",
        "path": path,
        "url": output_file_url(path),
        "title": "Selected Parcel",
        "layer_key": f"derived_selected_parcel_{parcel_context.get('parcel_set_id') or 'parcel_context'}",
        "analysis_run_id": None,
        "review_notes": [
            "Selected parcel GeoJSON is a local draft output and was not published.",
            "Layer is shown as reference; map extent is focused on selected parcel.",
        ],
    }


def _base_unmatched_parcel_context(parsed: dict[str, Any], *, reason: str = PARCEL_NOT_MATCHED_WARNING) -> dict[str, Any]:
    identifiers = [*(parsed.get("parsed_identifiers") or []), *(parsed.get("address_candidates") or [])]
    input_type = parsed.get("input_type")
    is_address = input_type == "address" and bool(parsed.get("address_candidates")) and not parsed.get("parsed_identifiers")
    if is_address and reason == PARCEL_NOT_MATCHED_WARNING:
        reason = ADDRESS_NOT_MATCHED_WARNING
    blocked_status = "blocked_until_address_matched" if is_address else "blocked_until_parcel_matched"
    return {
        "parcel_set_id": None,
        "input_type": input_type,
        "origin_type": "address" if is_address else input_type,
        "request_type": "address_context" if is_address else "parcel_context",
        "parsed_identifiers": identifiers,
        "address_candidates": parsed.get("address_candidates") or [],
        "match_status": "needs_review",
        "origin_match_status": "needs_review",
        "matched_count": 0,
        "unmatched_identifiers": identifiers,
        "candidate_matches": [],
        "matched_parcels_summary": [],
        "can_focus_map": False,
        "can_fetch_geometry": False,
        "reason_if_not_focusable": reason,
        "preview_status": blocked_status,
        "analysis_status": blocked_status,
        "focus_mode": "address" if is_address else "parcel",
        "parcel_extent": {
            "type": blocked_status,
            "value": None,
            "notes": reason,
        },
        "parcel_buffer_extent": None,
        "selected_parcel_geojson_path": None,
        "context_layers": [],
        "nearby_distance": None,
        "parcel_warnings": [reason, *(parsed.get("warnings") or [])],
    }


def _matched_parcel_context_from_set(
    parcel_set: dict[str, Any],
    *,
    raw_prompt: str,
    fetch_geometry: bool,
) -> dict[str, Any]:
    matched_count = int(parcel_set.get("matched_count") or len(parcel_set.get("matched_parcels") or []))
    match_status = str(parcel_set.get("match_status") or ("matched" if matched_count else "unmatched"))
    input_type = parcel_set.get("input_type")
    is_address = input_type == "address"
    warnings = [str(item) for item in parcel_set.get("warnings") or [] if item]
    can_fetch_geometry = match_status == "matched" and 0 < matched_count <= 100
    geometry_result: dict[str, Any] = {}
    if can_fetch_geometry and fetch_geometry:
        try:
            geometry_result = fetch_selected_parcels(str(parcel_set["parcel_set_id"]))
            warnings.extend(str(item) for item in geometry_result.get("warnings") or [] if item)
        except Exception as exc:
            warnings.append(f"Selected parcel geometry could not be fetched safely: {exc}")

    geometry_path = geometry_result.get("geometry_output_path") or parcel_set.get("geometry_output_path")
    extent = None
    buffered = None
    output_path = _local_output_path(str(geometry_path) if geometry_path else None)
    if output_path and output_path.exists():
        extent = geojson_extent(output_path)
        buffered = buffer_extent(extent)

    can_focus_map = bool(extent and buffered)
    if matched_count < 1:
        reason = ADDRESS_NOT_MATCHED_WARNING if is_address else PARCEL_NOT_MATCHED_WARNING
    elif match_status != "matched":
        reason = "Parcel match needs review before AutoMap can focus the map or fetch selected parcel geometry."
    elif not can_fetch_geometry:
        reason = "Matched parcel count exceeds selected parcel geometry safety limits; split the parcel set."
    elif not can_focus_map:
        reason = "Parcel matched, but selected parcel geometry is not available for focused preview yet."
    else:
        reason = None

    if reason:
        warnings.append(reason)

    return {
        "parcel_set_id": parcel_set.get("parcel_set_id"),
        "input_type": input_type,
        "origin_type": "address" if is_address else input_type,
        "request_type": "address_context" if is_address else "parcel_context",
        "raw_input": parcel_set.get("raw_input") or raw_prompt,
        "parsed_identifiers": parcel_set.get("parsed_identifiers") or [],
        "match_status": match_status,
        "origin_match_status": match_status,
        "matched_count": matched_count,
        "unmatched_identifiers": parcel_set.get("unmatched_identifiers") or [],
        "candidate_matches": parcel_set.get("candidate_matches") or [],
        "matched_parcels_summary": parcel_set.get("matched_parcels") or [],
        "can_focus_map": can_focus_map,
        "can_fetch_geometry": can_fetch_geometry,
        "reason_if_not_focusable": reason,
        "preview_status": "ready_for_address_focus" if is_address and can_focus_map else "ready_for_parcel_focus" if can_focus_map else "blocked_until_address_matched" if is_address else "blocked_until_parcel_matched",
        "analysis_status": "available_if_explicitly_requested" if can_focus_map else "blocked_until_address_matched" if is_address else "blocked_until_parcel_matched",
        "focus_mode": "address" if is_address else "parcel",
        "parcel_extent": extent
        or {
            "type": "blocked_until_address_matched" if is_address else "blocked_until_parcel_matched",
            "value": None,
            "notes": reason or "Parcel extent is unavailable.",
        },
        "parcel_buffer_extent": buffered,
        "selected_parcel_geojson_path": geometry_path,
        "geometry_output_path": geometry_path,
        "geometry_receipt": geometry_result.get("receipt") or parcel_set.get("geometry_receipt") or {},
        "context_layers": [],
        "nearby_distance": None,
        "parcel_warnings": sorted({warning for warning in warnings if warning}),
    }


def _parcel_context_from_prompt(
    prompt: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    match_parcel_context: bool = False,
    fetch_geometry: bool = True,
) -> dict[str, Any] | None:
    parsed = parse_parcel_input(prompt)
    if not parsed.get("parcel_intent"):
        return None
    proximity_context = build_proximity_context(prompt)
    if (
        parsed.get("input_type") == "address"
        and parsed.get("address_candidates")
        and not parsed.get("parsed_identifiers")
        and proximity_context.get("proximity_detected")
    ):
        return None
    if not match_parcel_context:
        return _base_unmatched_parcel_context(
            parsed,
            reason=(
                "Address-centered request detected; match the address before creating a focused preview."
                if parsed.get("input_type") == "address"
                else "Parcel-centered request detected; match the parcel before creating a focused preview."
            ),
        )
    try:
        parcel_set = create_parcel_set(prompt, layer_catalog=layer_catalog, persist=True)
    except Exception as exc:
        context = _base_unmatched_parcel_context(parsed, reason=f"Parcel matching could not complete safely: {exc}")
        context["match_status"] = "needs_review"
        return context
    return _matched_parcel_context_from_set(parcel_set, raw_prompt=prompt, fetch_geometry=fetch_geometry)


def _review_flags(
    parsed_request: dict[str, Any],
    matching: dict[str, Any],
    request_intelligence: dict[str, Any] | None = None,
    analysis_plan: dict[str, Any] | None = None,
    data_gap_context: dict[str, Any] | None = None,
    source_coverage: dict[str, Any] | None = None,
) -> list[str]:
    flags: list[str] = []
    if matching["missing_data_needed"]:
        flags.append("Missing requested data from verified layer catalog.")
    for gap_key, context in (data_gap_context or {}).items():
        if context.get("candidates"):
            flags.append(f"Data gap candidate sources available for review: {gap_key}.")
            if context.get("status") == "partially_supported":
                flags.append(
                    f"Verified proxy or limited-coverage source exists for {gap_key}; "
                    "do not treat it as official countywide approval or capacity."
                )
    for warning in (source_coverage or {}).get("warnings") or []:
        flags.append(str(warning))
    if "recent" in parsed_request.get("time_references", []):
        flags.append("Recent time range and date field need review.")
    if parsed_request.get("analysis_intent") == "proximity":
        flags.append("Proximity distance needs review.")
    if "commercial" in parsed_request.get("topic_details", {}).get("zoning_modifiers", []):
        flags.append("Commercial zoning field/code needs review.")
    if matching["confidence_score"] < 0.65:
        flags.append("Overall match confidence is below review threshold.")
    for flag in (request_intelligence or {}).get("ambiguity_flags") or []:
        flags.append(f"Ambiguity needs review: {flag}.")
    for part in (request_intelligence or {}).get("unsupported_parts") or []:
        flags.append(f"Unsupported or missing request part: {part}.")
    scenario_context = (request_intelligence or {}).get("scenario_context") or {}
    if scenario_context.get("scenario_detected"):
        flags.append(
            f"Scenario workflow recommended: {scenario_context.get('scenario_type')} "
            "should be reviewed as a planning framework, not an official recommendation."
        )
    for question in (analysis_plan or {}).get("review_questions") or []:
        if isinstance(question, dict) and question.get("question"):
            flags.append(f"Clarifying question: {question['question']}")
    return flags


def build_recipe(
    prompt: str,
    layer_catalog: list[dict[str, Any]] | None = None,
    include_filter_intelligence: bool = True,
    persist_data_gaps: bool = True,
    match_parcel_context: bool | None = None,
    fetch_parcel_geometry: bool = True,
) -> dict[str, Any]:
    """Build a structured map recipe from a plain-English GIS request."""
    total_start = perf_counter()
    timing = {
        "parse_ms": 0,
        "intelligence_ms": 0,
        "layer_match_ms": 0,
        "field_filter_ms": 0,
        "parcel_context_ms": 0,
        "analysis_planning_ms": 0,
        "total_ms": 0,
    }
    stage_start = perf_counter()
    parsed_request = parse_prompt(prompt)
    timing["parse_ms"] = _elapsed_ms(stage_start)

    stage_start = perf_counter()
    should_match_parcel_context = layer_catalog is None if match_parcel_context is None else match_parcel_context
    parcel_context = _parcel_context_from_prompt(
        prompt,
        layer_catalog=layer_catalog,
        match_parcel_context=should_match_parcel_context,
        fetch_geometry=fetch_parcel_geometry,
    )
    timing["parcel_context_ms"] = _elapsed_ms(stage_start)

    stage_start = perf_counter()
    initial_intelligence = build_request_intelligence(prompt, parsed_request)
    timing["intelligence_ms"] += _elapsed_ms(stage_start)
    request_plan = build_request_plan(prompt, parsed_request)

    stage_start = perf_counter()
    matching = match_layers(parsed_request, layer_catalog, request_intelligence=initial_intelligence)
    timing["layer_match_ms"] = _elapsed_ms(stage_start)

    data_gap_context = safe_gap_context_for_recipe(matching["missing_data_needed"])
    selected_layers = enrich_selected_layers_with_source_usage(
        [selected_layer_from_match(layer) for layer in matching["selected_layers"]],
        parsed_request,
    )
    rejected_layers = [rejected_layer_from_match(layer) for layer in matching["rejected_layers"]]
    source_coverage = build_source_coverage(
        selected_layers,
        matching["missing_data_needed"],
        data_gap_context,
        parsed_request,
    )
    stage_start = perf_counter()
    intelligence_bundle = build_request_intelligence(
        prompt,
        parsed_request,
        missing_data=matching["missing_data_needed"],
        selected_layers=selected_layers,
    )
    timing["intelligence_ms"] += _elapsed_ms(stage_start)
    request_intelligence = intelligence_bundle["request_intelligence"]
    analysis_plan = intelligence_bundle["analysis_plan"]
    learned_context = build_learned_context(prompt, request_intelligence, analysis_plan)
    review_flags = _review_flags(parsed_request, matching, request_intelligence, analysis_plan, data_gap_context, source_coverage)

    recipe = {
        "map_title": _title_from_prompt(parsed_request),
        "request_type": request_plan["request_type"],
        "user_intent": parsed_request["raw_prompt"],
        "parsed_request": parsed_request,
        "request_plan": request_plan,
        "request_intelligence": request_intelligence,
        "analysis_plan": analysis_plan,
        "learned_context": learned_context,
        "data_gap_resolution_context": data_gap_context,
        "source_coverage": source_coverage,
        "selected_layers": selected_layers,
        "rejected_layers": rejected_layers,
        "filters": _filters(parsed_request),
        "spatial_operations": _spatial_operations(parsed_request, selected_layers, analysis_plan),
        "symbology_recommendations": _symbology(selected_layers),
        "suggested_extent": _suggested_extent(parsed_request),
        "confidence_score": matching["confidence_score"],
        "needs_review": bool(review_flags),
        "review_reasons": review_flags,
        "missing_data_needed": matching["missing_data_needed"],
        "filter_plan": {},
        "validation": {},
        "analysis_execution": {},
        "recipe_timing": timing,
        "created_at": datetime.now(UTC).isoformat(),
        "notes": [
            "Recipe uses verified AutoMap layer catalog metadata only.",
            "No feature geometries were downloaded and no ArcGIS web map was created.",
        ],
    }

    if parcel_context:
        recipe["parcel_context"] = parcel_context
        recipe["review_reasons"] = sorted(
            set(
                [
            *recipe["review_reasons"],
                    parcel_context.get("reason_if_not_focusable")
                    or "Parcel-centered request detected; focused preview requires a matched parcel.",
                    *parcel_context.get("parcel_warnings", []),
                ]
            )
        )
        recipe["needs_review"] = True
        recipe["preview_status"] = parcel_context.get("preview_status")
        if parcel_context.get("can_focus_map") and parcel_context.get("parcel_buffer_extent"):
            recipe["suggested_extent"] = parcel_context["parcel_buffer_extent"]
            recipe["focus_mode"] = "parcel"
        elif recipe["suggested_extent"]["type"] == "countywide":
            recipe["suggested_extent"] = parcel_context["parcel_extent"]

    if include_filter_intelligence:
        stage_start = perf_counter()
        recipe["filter_plan"] = build_filter_plan(recipe, catalog_records=layer_catalog)
        validation = validate_filter_plan(recipe)
        recipe["validation"] = validation
        if validation["warnings"]:
            recipe["review_reasons"] = sorted(set([*recipe["review_reasons"], *validation["warnings"]]))
            recipe["needs_review"] = True
        timing["field_filter_ms"] = _elapsed_ms(stage_start)

    brain_start = perf_counter()
    recipe = attach_brain_recipe_metadata(recipe, layer_catalog)
    timing["brain_v2_ms"] = _elapsed_ms(brain_start)

    try:
        from app.analysis_executor import analysis_execution_for_recipe

        stage_start = perf_counter()
        recipe["analysis_execution"] = analysis_execution_for_recipe(recipe, layer_catalog)
        timing["analysis_planning_ms"] = _elapsed_ms(stage_start)
    except Exception as exc:
        recipe["analysis_execution"] = {
            "executable": False,
            "supported_operations": [],
            "blocked_reasons": [f"Analysis planning unavailable: {exc}"],
            "estimated_query_counts": {},
            "recommended_execution_plan": [],
            "analysis_run_id": None,
            "derived_outputs": [],
        }

    if parcel_context:
        derived_output = _selected_parcel_derived_output(parcel_context)
        if derived_output:
            recipe.setdefault("analysis_execution", {}).setdefault("derived_outputs", [])
            recipe["analysis_execution"]["derived_outputs"].append(derived_output)
        if parcel_context.get("can_focus_map"):
            recipe["analysis_execution"].update(
                {
                    "analysis_status": "not_needed_for_basic_context_map",
                    "operation_type": "parcel_context_preview",
                    "executable": False,
                    "supported_operations": [],
                    "blocked_reasons": [],
                    "recommended_execution_plan": [
                        "Preview the selected parcel and context layers first.",
                        "Run analysis only if the reviewer asks for intersection, proximity, or summary execution.",
                    ],
                }
            )
        else:
            block_status = parcel_context.get("analysis_status") or "blocked_until_parcel_matched"
            operation_type = "address_context_preview_blocked" if parcel_context.get("origin_type") == "address" else "parcel_context_preview_blocked"
            recipe["analysis_execution"].update(
                {
                    "analysis_status": block_status,
                    "operation_type": operation_type,
                    "executable": False,
                    "supported_operations": [],
                    "blocked_reasons": [
                        parcel_context.get("reason_if_not_focusable")
                        or (ADDRESS_NOT_MATCHED_WARNING if parcel_context.get("origin_type") == "address" else PARCEL_NOT_MATCHED_WARNING)
                    ],
                    "recommended_execution_plan": [
                        "Correct the address/PIN/parcel identifier.",
                        "Match the address or parcel in AutoMap.",
                        "Fetch selected parcel or origin geometry only after a safe match count is confirmed.",
                    ],
                }
            )

    if persist_data_gaps and recipe["missing_data_needed"]:
        upsert_data_gaps_from_recipe(recipe)

    timing["total_ms"] = _elapsed_ms(total_start)
    recipe["recipe_timing"] = timing
    return recipe
