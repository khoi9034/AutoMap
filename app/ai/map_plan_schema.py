"""Strict MapPlan schema primitives for the optional AI planner."""

from __future__ import annotations

from app.automap_brain.ontology import REQUEST_TYPES


OUTPUT_MODES = {"map", "table", "route", "report", "map_and_table"}
SPATIAL_OPERATIONS = {
    "intersect",
    "within",
    "contains",
    "near",
    "closest_by_road",
    "closest_by_distance",
    "avoid",
    "clip_to_aoi",
    "summarize",
    "filter",
    "no_operation_context_only",
}
LAYER_ROLES = {
    "primary_result",
    "supporting_context",
    "boundary_context",
    "transportation_context",
    "route_overlay",
    "generated_marker",
    "diagnostics_only",
}
ALLOWED_DOMAINS = {
    "addresses",
    "address_proximity",
    "parcels",
    "zoning",
    "floodplain",
    "transportation",
    "roads",
    "facilities",
    "development_activity",
    "historical_layers",
    "table_requests",
    "boundaries",
    "jurisdiction",
    "suitability",
}


MAP_PLAN_SCHEMA: dict[str, object] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "version",
        "request_type",
        "confidence",
        "normalized_prompt",
        "cabarrus_scope_check",
        "user_intent_summary",
        "geography",
        "aoi",
        "output_mode",
        "target_layers",
        "context_layers",
        "spatial_operations",
        "filters",
        "result_expectation",
        "cartography_roles",
        "legend_expectation",
        "fallback_strategy",
        "clarifying_question",
        "safety_notes",
    ],
    "properties": {
        "version": {"type": "string"},
        "request_type": {"type": "string", "enum": sorted(REQUEST_TYPES)},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "normalized_prompt": {"type": "string"},
        "cabarrus_scope_check": {"type": "string", "enum": ["in_scope", "out_of_scope", "uncertain"]},
        "user_intent_summary": {"type": "string"},
        "geography": {"type": "object"},
        "aoi": {"type": "object"},
        "output_mode": {"type": "string", "enum": sorted(OUTPUT_MODES)},
        "target_layers": {"type": "array"},
        "context_layers": {"type": "array"},
        "spatial_operations": {"type": "array", "items": {"type": "string", "enum": sorted(SPATIAL_OPERATIONS)}},
        "filters": {"type": "array"},
        "result_expectation": {"type": "string"},
        "cartography_roles": {"type": "array"},
        "legend_expectation": {"type": "array"},
        "fallback_strategy": {"type": "string"},
        "clarifying_question": {"type": ["string", "null"]},
        "safety_notes": {"type": "array", "items": {"type": "string"}},
    },
}

