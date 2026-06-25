"""AutoMap Brain Kernel ontology primitives.

This module wraps the existing county GIS domain ontology with explicit
kernel-level request types, output modes, spatial relationships, and layer
roles. The values are deterministic and intentionally Cabarrus-scoped.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.automap_brain.domain_ontology import (
    DOMAIN_ONTOLOGY,
    MAJOR_ROAD_TERMS,
    OUT_OF_SCOPE_PLACES,
    PLACE_ALIASES,
    SUPPORTED_SCOPE,
    TYPO_REPLACEMENTS,
)


REQUEST_TYPES = {
    "proximity",
    "floodplain_screening",
    "zoning_context",
    "parcel_screening",
    "table_request",
    "development_activity",
    "suitability",
    "historical_lookup",
    "general_map",
    "unsupported_area",
    "unsupported_request",
}

OUTPUT_MODES = {"map", "table", "route", "report", "scenario", "map_and_table"}

SPATIAL_RELATIONSHIPS = {
    "intersects",
    "within",
    "contains",
    "near",
    "around",
    "avoids",
    "closest_by_road",
    "closest_by_distance",
    "clipped_to_aoi",
    "context_only",
}

LAYER_ROLES = {
    "primary_result",
    "primary_polygon_highlight",
    "affected_parcels",
    "context_polygon_muted",
    "boundary_outline",
    "floodplain_overlay",
    "major_road",
    "road_context",
    "route_line",
    "origin_marker",
    "target_marker",
    "facility_point",
    "table_source",
    "diagnostics_only",
}


def kernel_ontology() -> dict[str, Any]:
    """Return a JSON-serializable ontology snapshot for diagnostics/tests."""
    return {
        "scope": SUPPORTED_SCOPE,
        "request_types": sorted(REQUEST_TYPES),
        "output_modes": sorted(OUTPUT_MODES),
        "spatial_relationships": sorted(SPATIAL_RELATIONSHIPS),
        "layer_roles": sorted(LAYER_ROLES),
        "domains": deepcopy(DOMAIN_ONTOLOGY),
        "place_aliases": deepcopy(PLACE_ALIASES),
        "out_of_scope_places": sorted(OUT_OF_SCOPE_PLACES),
        "typo_replacements": deepcopy(TYPO_REPLACEMENTS),
        "major_road_terms": list(MAJOR_ROAD_TERMS),
    }


def domain_meta(domain: str) -> dict[str, Any]:
    """Return ontology metadata for one domain without exposing mutability."""
    return deepcopy(DOMAIN_ONTOLOGY.get(domain) or {})
