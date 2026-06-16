"""Parcel set storage and parcel-centered context recipe builder."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.data_gap_resolver import safe_gap_context_for_recipe
from app.db import _quote_identifier, get_engine
from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import slugify
from app.parcel_input_parser import parse_parcel_input
from app.parcel_matcher import match_parcels_by_address, match_parcels_by_identifier
from app.prompt_parser import parse_prompt
from app.source_usage_intelligence import build_source_coverage, enrich_selected_layers_with_source_usage


DEFAULT_PARCEL_NEARBY_DISTANCE = "0.25 miles"


def _parcel_sets_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.parcel_sets"


def _parcel_context_sessions_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.parcel_context_sessions"


def init_parcel_tables(schema_name: str = "automap") -> None:
    """Create additive AutoMap parcel workspace tables safely."""
    parcel_sets = _parcel_sets_table(schema_name)
    sessions = _parcel_context_sessions_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {parcel_sets} (
                    id serial PRIMARY KEY,
                    parcel_set_id text UNIQUE,
                    raw_input text,
                    input_type text,
                    parsed_identifiers jsonb DEFAULT '[]'::jsonb,
                    matched_parcels jsonb DEFAULT '[]'::jsonb,
                    unmatched_identifiers jsonb DEFAULT '[]'::jsonb,
                    match_status text,
                    source_layer_key text,
                    created_at timestamptz DEFAULT now(),
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {sessions} (
                    id serial PRIMARY KEY,
                    session_id text UNIQUE,
                    parcel_set_id text,
                    raw_prompt text,
                    context_layers jsonb DEFAULT '[]'::jsonb,
                    context_recipe jsonb DEFAULT '{{}}'::jsonb,
                    context_report jsonb DEFAULT '{{}}'::jsonb,
                    warnings jsonb DEFAULT '[]'::jsonb,
                    created_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "parcel_set_id": "text UNIQUE",
            "raw_input": "text",
            "input_type": "text",
            "parsed_identifiers": "jsonb DEFAULT '[]'::jsonb",
            "matched_parcels": "jsonb DEFAULT '[]'::jsonb",
            "unmatched_identifiers": "jsonb DEFAULT '[]'::jsonb",
            "match_status": "text",
            "source_layer_key": "text",
            "created_at": "timestamptz DEFAULT now()",
            "updated_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {parcel_sets} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        for column, column_type in {
            "session_id": "text UNIQUE",
            "parcel_set_id": "text",
            "raw_prompt": "text",
            "context_layers": "jsonb DEFAULT '[]'::jsonb",
            "context_recipe": "jsonb DEFAULT '{}'::jsonb",
            "context_report": "jsonb DEFAULT '{}'::jsonb",
            "warnings": "jsonb DEFAULT '[]'::jsonb",
            "created_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {sessions} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _json_dumps(value: Any) -> str:
    return json.dumps(value, default=str)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _source_layer_key(match: dict[str, Any]) -> str | None:
    return match.get("source_layer_key")


def _record_parcel_set(record: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    init_parcel_tables(schema_name)
    table = _parcel_sets_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    parcel_set_id, raw_input, input_type, parsed_identifiers,
                    matched_parcels, unmatched_identifiers, match_status, source_layer_key
                )
                VALUES (
                    :parcel_set_id, :raw_input, :input_type,
                    CAST(:parsed_identifiers AS jsonb), CAST(:matched_parcels AS jsonb),
                    CAST(:unmatched_identifiers AS jsonb), :match_status, :source_layer_key
                )
                ON CONFLICT (parcel_set_id) DO UPDATE SET
                    raw_input = EXCLUDED.raw_input,
                    input_type = EXCLUDED.input_type,
                    parsed_identifiers = EXCLUDED.parsed_identifiers,
                    matched_parcels = EXCLUDED.matched_parcels,
                    unmatched_identifiers = EXCLUDED.unmatched_identifiers,
                    match_status = EXCLUDED.match_status,
                    source_layer_key = EXCLUDED.source_layer_key,
                    updated_at = now();
                """
            ),
            {
                "parcel_set_id": record["parcel_set_id"],
                "raw_input": record["raw_input"],
                "input_type": record["input_type"],
                "parsed_identifiers": _json_dumps(record.get("parsed_identifiers") or []),
                "matched_parcels": _json_dumps(record.get("matched_parcels") or []),
                "unmatched_identifiers": _json_dumps(record.get("unmatched_identifiers") or []),
                "match_status": record.get("match_status"),
                "source_layer_key": record.get("source_layer_key"),
            },
        )
    return record


def create_parcel_set(
    raw_input: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    persist: bool = True,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Parse and safely match a parcel set without downloading parcel geometry."""
    parsed = parse_parcel_input(raw_input)
    identifiers = list(parsed.get("parsed_identifiers") or [])
    addresses = list(parsed.get("address_candidates") or [])
    all_identifiers = [*identifiers, *addresses]
    if identifiers:
        match = match_parcels_by_identifier(identifiers, layer_catalog=layer_catalog, schema_name=schema_name)
        if addresses:
            address_match = match_parcels_by_address(addresses, layer_catalog=layer_catalog, schema_name=schema_name)
            match["matched_parcels"] = [*(match.get("matched_parcels") or []), *(address_match.get("matched_parcels") or [])]
            match["unmatched_identifiers"] = [
                *(match.get("unmatched_identifiers") or []),
                *(address_match.get("unmatched_identifiers") or []),
            ]
            match["warnings"] = [*(match.get("warnings") or []), *(address_match.get("warnings") or [])]
    elif addresses:
        match = match_parcels_by_address(addresses, layer_catalog=layer_catalog, schema_name=schema_name)
    else:
        match = {
            "source_layer_key": None,
            "matched_count": 0,
            "matched_parcels": [],
            "unmatched_identifiers": all_identifiers,
            "match_status": "needs_review" if parsed.get("parcel_intent") else "unmatched",
            "warnings": parsed.get("warnings") or ["No parcel identifiers or address candidates were parsed."],
            "downloaded_geometry": False,
        }

    matched_parcels = match.get("matched_parcels") or []
    record = {
        "parcel_set_id": f"parcel_set_{uuid4().hex[:12]}",
        "raw_input": raw_input,
        "input_type": parsed.get("input_type") or "unknown",
        "parsed_identifiers": all_identifiers,
        "matched_parcels": matched_parcels,
        "unmatched_identifiers": match.get("unmatched_identifiers") or [],
        "match_status": match.get("match_status") or ("matched" if matched_parcels else "unmatched"),
        "source_layer_key": _source_layer_key(match),
        "matched_count": len(matched_parcels),
        "warnings": [*(parsed.get("warnings") or []), *(match.get("warnings") or [])],
        "field_map": match.get("field_map") or {},
        "downloaded_geometry": False,
        "created_at": _now(),
        "updated_at": _now(),
    }
    return _record_parcel_set(record, schema_name) if persist else record


def _row_dict(row: Any) -> dict[str, Any]:
    data = dict(row)
    for field in ["parsed_identifiers", "matched_parcels", "unmatched_identifiers", "context_layers", "context_recipe", "context_report", "warnings"]:
        if isinstance(data.get(field), str):
            try:
                data[field] = json.loads(data[field])
            except json.JSONDecodeError:
                pass
    return data


def get_parcel_set(parcel_set_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one stored parcel set."""
    init_parcel_tables(schema_name)
    table = _parcel_sets_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(f"SELECT * FROM {table} WHERE parcel_set_id = :parcel_set_id;"),
            {"parcel_set_id": parcel_set_id},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"Parcel set not found: {parcel_set_id}")
    return _row_dict(row)


def list_parcel_sets(schema_name: str = "automap", limit: int = 50) -> list[dict[str, Any]]:
    """List recent parcel sets."""
    init_parcel_tables(schema_name)
    table = _parcel_sets_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT *
                FROM {table}
                ORDER BY updated_at DESC NULLS LAST, created_at DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
    return [_row_dict(row) for row in rows]


def _matches_terms(record: dict[str, Any], terms: list[str]) -> bool:
    blob = " ".join(
        str(value or "").lower()
        for value in [
            record.get("layer_key"),
            record.get("layer_name"),
            record.get("service_name"),
            record.get("category"),
            record.get("canonical_topic"),
            " ".join(str(item) for item in (record.get("aliases") or [])),
            " ".join(str(item) for item in (record.get("planning_use_cases") or [])),
        ]
    )
    return any(term.lower() in blob for term in terms)


def _best_layer(
    catalog: list[dict[str, Any]],
    categories: set[str],
    terms: list[str] | None = None,
) -> dict[str, Any] | None:
    rows = [
        record
        for record in catalog
        if record.get("is_verified")
        and record.get("is_active", True)
        and not record.get("is_group_layer")
        and not record.get("is_historical")
        and (record.get("category") in categories or record.get("canonical_topic") in categories)
        and (not terms or _matches_terms(record, terms))
    ]
    if not rows:
        return None
    return sorted(
        rows,
        key=lambda item: (
            int(item.get("source_priority") or 999),
            0 if str(item.get("source_status") or "") == "active" else 1,
            str(item.get("layer_name") or ""),
        ),
    )[0]


def _topic_layer_specs(requested_topics: list[str], prompt_text: str) -> list[tuple[set[str], list[str], str]]:
    topics = set(requested_topics)
    prompt = prompt_text.lower()
    specs: list[tuple[set[str], list[str], str]] = [
        ({"parcel"}, ["parcel", "tax parcel"], "base_layer"),
        ({"jurisdiction", "boundary"}, ["municipal", "district", "etj"], "jurisdiction_filter"),
    ]
    if topics.intersection({"addresses"}) or "address" in prompt:
        specs.append(({"address"}, ["address"], "reference_layer"))
    if topics.intersection({"zoning"}) or "zoning" in prompt:
        specs.append(({"zoning"}, ["zoning"], "constraint_overlay"))
    if topics.intersection({"flood"}) or "flood" in prompt:
        if "100" in prompt:
            specs.append(({"flood"}, ["100", "flood"], "constraint_overlay"))
        elif "500" in prompt:
            specs.append(({"flood"}, ["500", "flood"], "constraint_overlay"))
        else:
            specs.append(({"flood"}, ["flood"], "constraint_overlay"))
    if topics.intersection({"schools"}) or "school" in prompt:
        specs.append(({"schools"}, ["elementary", "school"], "school_boundary_layer"))
        specs.append(({"schools"}, ["middle", "school"], "school_boundary_layer"))
        specs.append(({"schools"}, ["high", "school"], "school_boundary_layer"))
    if topics.intersection({"transportation", "traffic"}) or any(term in prompt for term in ["road", "roads", "street", "nearby"]):
        specs.append(({"transportation"}, ["road", "centerline"], "transportation_layer"))
    if topics.intersection({"traffic"}) or "aadt" in prompt or "high traffic" in prompt:
        specs.append(({"transportation"}, ["aadt", "traffic"], "transportation_layer"))
    if "stip" in prompt or "planned road" in prompt:
        specs.append(({"transportation_projects"}, ["stip", "project"], "transportation_layer"))
    if topics.intersection({"development"}) or any(term in prompt for term in ["permit", "planning", "development", "activity"]):
        specs.append(({"development_activity_proxy"}, ["accela", "plan review"], "development_activity_layer"))
        specs.append(({"planning_cases"}, ["planning", "case"], "development_activity_layer"))
    return specs


def _select_context_layers(
    requested_topics: list[str],
    prompt_text: str,
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    catalog = layer_catalog if layer_catalog is not None else load_catalog_records()
    selected: list[dict[str, Any]] = []
    keys: set[str] = set()
    for categories, terms, role in _topic_layer_specs(requested_topics, prompt_text):
        layer = _best_layer(catalog, categories, terms)
        if not layer or layer.get("layer_key") in keys:
            continue
        selected.append(
            {
                **layer,
                "role": role,
                "confidence_score": 0.78,
                "match_score": 120,
                "match_reasons": ["selected for parcel context overlay"],
                "why_selected": "Selected as a verified parcel-context layer from the AutoMap catalog.",
                "review_notes": ["Review parcel-context layer coverage before official use."],
            }
        )
        keys.add(layer.get("layer_key"))
    return selected


def _missing_data_for_parcel_prompt(prompt_text: str, selected_layers: list[dict[str, Any]]) -> list[str]:
    prompt = prompt_text.lower()
    missing: list[str] = []
    categories = {layer.get("category") for layer in selected_layers}
    if "permit" in prompt:
        missing.append("current_permits")
    if "planning" in prompt and "planning_cases" not in categories:
        missing.append("current_planning_cases")
    if "development" in prompt and "development_activity_proxy" not in categories:
        missing.append("current_development_pipeline")
    return sorted(set(missing))


def _parcel_extent(parcel_set: dict[str, Any]) -> dict[str, Any]:
    if parcel_set.get("matched_count"):
        return {
            "type": "matched_parcels",
            "value": parcel_set["parcel_set_id"],
            "notes": "Fit to matched parcel geometries after safe geometry retrieval is approved.",
        }
    return {
        "type": "review_needed",
        "value": None,
        "notes": "Parcel extent is unavailable until identifiers are matched.",
    }


def build_parcel_context(
    parcel_set_id: str,
    requested_topics: list[str] | None = None,
    *,
    raw_prompt: str | None = None,
    nearby_distance: str | None = None,
    layer_catalog: list[dict[str, Any]] | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Build parcel-centered context metadata and selected layers."""
    parcel_set = get_parcel_set(parcel_set_id, schema_name)
    prompt_text = raw_prompt or parcel_set.get("raw_input") or ""
    parsed_prompt = parse_prompt(prompt_text)
    topics = list(dict.fromkeys([*(requested_topics or []), *(parsed_prompt.get("topics") or [])]))
    selected_layers = enrich_selected_layers_with_source_usage(
        _select_context_layers(topics, prompt_text, layer_catalog=layer_catalog),
        parsed_prompt,
    )
    missing = _missing_data_for_parcel_prompt(prompt_text, selected_layers)
    data_gap_context = safe_gap_context_for_recipe(missing)
    source_coverage = build_source_coverage(selected_layers, missing, data_gap_context, parsed_prompt)
    warnings = [
        *(parcel_set.get("warnings") or []),
        *(source_coverage.get("warnings") or []),
    ]
    if "near" in prompt_text.lower() or "nearby" in prompt_text.lower():
        if nearby_distance:
            warnings.append(f"Nearby context distance set by reviewer: {nearby_distance}.")
        else:
            warnings.append("Nearby context needs a reviewer-supplied distance before spatial execution.")
    if missing:
        warnings.append("Official current permit/planning/development data gaps remain visible where unresolved.")

    return {
        "parcel_set": parcel_set,
        "context_layers": selected_layers,
        "source_coverage": source_coverage,
        "missing_data_needed": missing,
        "data_gap_resolution_context": data_gap_context,
        "nearby_distance": nearby_distance,
        "warnings": list(dict.fromkeys(str(warning) for warning in warnings if warning)),
    }


def _matched_summary(parcel_set: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for parcel in parcel_set.get("matched_parcels") or []:
        rows.append(
            {
                "pin14": parcel.get("pin14"),
                "pin": parcel.get("pin"),
                "parcel_id": parcel.get("parcel_id"),
                "address": parcel.get("address"),
                "object_id": parcel.get("object_id"),
                "source_layer_key": parcel.get("source_layer_key"),
            }
        )
    return rows


def build_parcel_context_recipe(
    parcel_set_id: str,
    requested_topics: list[str] | None = None,
    *,
    raw_prompt: str | None = None,
    nearby_distance: str | None = None,
    layer_catalog: list[dict[str, Any]] | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Create a reviewable parcel-centered map recipe."""
    context = build_parcel_context(
        parcel_set_id,
        requested_topics,
        raw_prompt=raw_prompt,
        nearby_distance=nearby_distance,
        layer_catalog=layer_catalog,
        schema_name=schema_name,
    )
    parcel_set = context["parcel_set"]
    raw_prompt = raw_prompt or parcel_set.get("raw_input") or "Parcel context map"
    parsed_prompt = parse_prompt(raw_prompt)
    parcel_context = {
        "parcel_set_id": parcel_set_id,
        "input_type": parcel_set.get("input_type"),
        "parsed_identifiers": parcel_set.get("parsed_identifiers") or [],
        "matched_count": parcel_set.get("matched_count") or len(parcel_set.get("matched_parcels") or []),
        "unmatched_identifiers": parcel_set.get("unmatched_identifiers") or [],
        "matched_parcels_summary": _matched_summary(parcel_set),
        "parcel_extent": _parcel_extent(parcel_set),
        "context_layers": context["context_layers"],
        "nearby_distance": nearby_distance,
        "parcel_warnings": context["warnings"],
    }
    review_reasons = [
        *context["warnings"],
        "Parcel context map is a local review draft and not an official map.",
    ]
    if parcel_set.get("match_status") != "matched":
        review_reasons.append("Parcel set matching is partial, unmatched, or needs review.")
    recipe = {
        "map_title": "Parcel Context Map",
        "user_intent": raw_prompt,
        "parsed_request": {
            **parsed_prompt,
            "parcel_context_detected": True,
        },
        "request_intelligence": {
            "detected_intents": ["parcel_context_map", "property_lookup"],
            "primary_intent": "parcel_context_map",
            "secondary_intents": ["property_lookup"],
            "ambiguity_flags": ["nearby_distance_missing"] if ("near" in raw_prompt.lower() and not nearby_distance) else [],
            "clarifying_questions": (
                [
                    {
                        "question": "What distance should count as nearby for parcel context layers?",
                        "reason": "Nearby context requires a reviewed distance threshold.",
                        "examples": ["500 feet", "0.25 miles", "0.5 miles"],
                        "trigger": "nearby",
                    }
                ]
                if ("near" in raw_prompt.lower() and not nearby_distance)
                else []
            ),
            "reasoning_summary": "AutoMap detected a parcel-centered request and prioritized verified Tax Parcels plus requested context overlays.",
            "unsupported_parts": [],
        },
        "analysis_plan": {
            "goal": "Create a parcel-centered context map using verified AutoMap catalog layers.",
            "required_layers": ["parcel"],
            "optional_layers": [layer.get("category") for layer in context["context_layers"] if layer.get("category") != "parcel"],
            "spatial_steps": [
                {
                    "operation": "focus_extent_to_parcel_set",
                    "input": parcel_set_id,
                    "notes": "Only retrieve matched parcel geometry later if the parcel set remains under safety limits.",
                }
            ],
            "attribute_steps": [],
            "assumptions": ["Parcel matching used returnGeometry=false first."],
            "blockers": [] if parcel_set.get("matched_parcels") else ["No parcel records are matched yet."],
            "review_questions": [],
        },
        "parcel_context": parcel_context,
        "source_coverage": context["source_coverage"],
        "data_gap_resolution_context": context["data_gap_resolution_context"],
        "selected_layers": context["context_layers"],
        "rejected_layers": [],
        "filters": [
            {
                "type": "parcel_set",
                "field": None,
                "value": parcel_set_id,
                "notes": "Filter Tax Parcels to the matched parcel set after safe identifier review.",
            }
        ],
        "spatial_operations": [
            {
                "operation": "parcel_context_overlay",
                "input_layers": [layer.get("layer_key") for layer in context["context_layers"]],
                "notes": "Show selected parcel set with requested context overlays.",
            }
        ],
        "symbology_recommendations": [
            {"layer_key": layer.get("layer_key"), "style": "parcel-context review styling"}
            for layer in context["context_layers"]
        ],
        "suggested_extent": _parcel_extent(parcel_set),
        "confidence_score": 0.78 if parcel_set.get("matched_parcels") else 0.45,
        "needs_review": True,
        "review_reasons": list(dict.fromkeys(review_reasons)),
        "missing_data_needed": context["missing_data_needed"],
        "filter_plan": {},
        "validation": {},
        "analysis_execution": {
            "executable": bool(parcel_set.get("matched_parcels")) and (parcel_set.get("matched_count") or 0) <= 100,
            "supported_operations": [
                "selected parcels intersect floodplain",
                "selected parcels by zoning",
                "selected parcels by school district",
                "nearby roads/AADT/STIP context if distance is reviewed",
            ],
            "blocked_reasons": [] if parcel_set.get("matched_parcels") else ["No matched parcels available for parcel-centered analysis."],
            "recommended_execution_plan": [
                "Use matched parcel ObjectIDs only.",
                "Retrieve parcel geometry only after count remains under safety limits.",
                "Run selected overlay checks against requested context layers.",
            ],
            "derived_outputs": [],
        },
        "created_at": _now(),
        "notes": [
            "Parcel context recipe uses verified AutoMap layer catalog metadata only.",
            "Parcel matching used returnGeometry=false and did not download countywide parcel geometry.",
            "No ArcGIS item was published.",
        ],
    }
    return recipe


def build_parcel_context_webmap(parcel_set_id: str, **kwargs: Any) -> dict[str, Any]:
    """Build a local-only WebMap-style shell for parcel context preview."""
    recipe = build_parcel_context_recipe(parcel_set_id, **kwargs)
    return {
        "version": "2.31",
        "authoringApp": "AutoMap",
        "mapTitle": recipe["map_title"],
        "operationalLayers": [
            {
                "id": layer.get("layer_key"),
                "title": layer.get("display_title") or layer.get("layer_name"),
                "url": layer.get("service_url") or layer.get("layer_url"),
                "layerType": "ArcGISMapServiceLayer",
                "visibility": True,
                "opacity": 0.75,
                "autoMapLayerKey": layer.get("layer_key"),
            }
            for layer in recipe.get("selected_layers") or []
        ],
        "autoMapParcelContext": recipe["parcel_context"],
        "draftOnly": True,
    }


def build_nearby_context_layers(
    parcel_set_id: str,
    distance: str | None,
    *,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Return review metadata for nearby context layers without executing geometry."""
    context = build_parcel_context(parcel_set_id, raw_prompt=f"nearby parcel context {distance or ''}", nearby_distance=distance, schema_name=schema_name)
    return {
        "parcel_set_id": parcel_set_id,
        "nearby_distance": distance,
        "context_layers": context["context_layers"],
        "warnings": context["warnings"],
        "executed": False,
    }


def summarize_parcel_context(parcel_set_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Summarize a stored parcel set and context readiness."""
    parcel_set = get_parcel_set(parcel_set_id, schema_name)
    return {
        "parcel_set_id": parcel_set_id,
        "input_type": parcel_set.get("input_type"),
        "match_status": parcel_set.get("match_status"),
        "matched_count": len(parcel_set.get("matched_parcels") or []),
        "unmatched_count": len(parcel_set.get("unmatched_identifiers") or []),
        "source_layer_key": parcel_set.get("source_layer_key"),
        "safe_for_geometry_request": 0 < len(parcel_set.get("matched_parcels") or []) <= 100,
        "downloaded_geometry": False,
    }


def _record_context_session(session: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    init_parcel_tables(schema_name)
    table = _parcel_context_sessions_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    session_id, parcel_set_id, raw_prompt, context_layers,
                    context_recipe, context_report, warnings
                )
                VALUES (
                    :session_id, :parcel_set_id, :raw_prompt,
                    CAST(:context_layers AS jsonb), CAST(:context_recipe AS jsonb),
                    CAST(:context_report AS jsonb), CAST(:warnings AS jsonb)
                )
                ON CONFLICT (session_id) DO UPDATE SET
                    context_layers = EXCLUDED.context_layers,
                    context_recipe = EXCLUDED.context_recipe,
                    context_report = EXCLUDED.context_report,
                    warnings = EXCLUDED.warnings;
                """
            ),
            {
                "session_id": session["session_id"],
                "parcel_set_id": session["parcel_set_id"],
                "raw_prompt": session["raw_prompt"],
                "context_layers": _json_dumps(session.get("context_layers") or []),
                "context_recipe": _json_dumps(session.get("context_recipe") or {}),
                "context_report": _json_dumps(session.get("context_report") or {}),
                "warnings": _json_dumps(session.get("warnings") or []),
            },
        )
    return session


def create_parcel_context_session(
    raw_prompt: str,
    *,
    requested_topics: list[str] | None = None,
    nearby_distance: str | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Create a parcel set and parcel-centered context recipe from a prompt."""
    parcel_set = create_parcel_set(raw_prompt, schema_name=schema_name)
    recipe = build_parcel_context_recipe(
        parcel_set["parcel_set_id"],
        requested_topics=requested_topics,
        raw_prompt=raw_prompt,
        nearby_distance=nearby_distance,
        schema_name=schema_name,
    )
    session = {
        "session_id": f"parcel_context_{uuid4().hex[:12]}",
        "parcel_set_id": parcel_set["parcel_set_id"],
        "raw_prompt": raw_prompt,
        "context_layers": recipe.get("selected_layers") or [],
        "context_recipe": recipe,
        "context_report": summarize_parcel_context(parcel_set["parcel_set_id"], schema_name),
        "warnings": recipe.get("review_reasons") or [],
        "created_at": _now(),
    }
    return _record_context_session(session, schema_name)


def list_parcel_context_sessions(schema_name: str = "automap", limit: int = 50) -> list[dict[str, Any]]:
    """List recent parcel context sessions."""
    init_parcel_tables(schema_name)
    table = _parcel_context_sessions_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT :limit;"),
            {"limit": limit},
        ).mappings()
    return [_row_dict(row) for row in rows]


def parcel_report_slug(parcel_set: dict[str, Any]) -> str:
    """Return a safe slug for parcel report folders."""
    label = parcel_set.get("parcel_set_id") or parcel_set.get("raw_input") or "parcel_context"
    return slugify(str(label))[:80]
