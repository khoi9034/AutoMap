"""County GIS ontology used by AutoMap Brain v2."""

from __future__ import annotations

from typing import Any


SUPPORTED_SCOPE = "Cabarrus County, NC"

TYPO_REPLACEMENTS = {
    "zonign": "zoning",
    "aorund": "around",
    "bearny": "nearby",
    "commerical": "commercial",
    "parcles": "parcels",
    "parcle": "parcel",
    "conord": "concord",
    "kannaplis": "kannapolis",
    "harrisburgh": "harrisburg",
}

PHRASE_REPLACEMENTS = {
    "flood plane": "floodplain",
    "flood planes": "floodplains",
    "flood plains": "floodplains",
    "business zones": "commercial zones",
    "business zoning": "commercial zoning",
}

PLACE_ALIASES = {
    "cabarrus county": {"name": "Cabarrus County", "type": "county", "confidence": 0.98},
    "countywide": {"name": "Cabarrus County", "type": "countywide", "confidence": 0.9},
    "concord": {"name": "Concord", "type": "municipality", "confidence": 0.95},
    "kannapolis": {"name": "Kannapolis", "type": "municipality", "confidence": 0.94},
    "harrisburg": {"name": "Harrisburg", "type": "municipality", "confidence": 0.94},
    "midland": {"name": "Midland", "type": "municipality", "confidence": 0.92},
    "mount pleasant": {"name": "Mount Pleasant", "type": "municipality", "confidence": 0.92},
    "mt pleasant": {"name": "Mount Pleasant", "type": "municipality", "confidence": 0.9},
    "locust": {"name": "Locust", "type": "municipality", "confidence": 0.9},
}

OUT_OF_SCOPE_PLACES = {
    "charlotte",
    "mecklenburg",
    "raleigh",
    "wake county",
    "greensboro",
    "durham",
    "union county",
    "iredell",
    "rowan county",
}

DOMAIN_ONTOLOGY: dict[str, dict[str, Any]] = {
    "address_proximity": {
        "synonyms": ["nearest", "closest", "fire station", "facility", "line", "route", "distance", "public safety"],
        "required_parameters": ["origin", "target_type"],
        "likely_layers": ["address", "public_facilities", "transportation"],
        "likely_fields": ["site_address", "facility_name", "road_name"],
        "expected_geometry_type": ["point", "polyline"],
        "default_symbology_role": "route_line",
        "fallback_behavior": "Use straight-line fallback only if bounded road routing is unavailable.",
    },
    "parcels": {
        "synonyms": ["parcel", "parcels", "property", "properties", "tax parcel", "pin", "pin14"],
        "likely_layers": ["parcel"],
        "likely_fields": ["pin", "pin14", "parcel_id", "acreage", "site_address", "municipality"],
        "expected_geometry_type": ["polygon"],
        "default_symbology_role": "parcel_outline",
        "fallback_behavior": "Show parcel outlines only and avoid owner/name search.",
    },
    "zoning": {
        "synonyms": [
            "zoning",
            "zone",
            "zones",
            "commercial zoning",
            "commercial zones",
            "business zoning",
            "retail zoning",
            "general commercial",
            "highway commercial",
            "neighborhood commercial",
            "retail",
        ],
        "required_parameters": ["geography"],
        "likely_layers": ["zoning", "jurisdiction"],
        "likely_fields": ["zoning", "zone", "district", "description", "jurisdiction"],
        "expected_geometry_type": ["polygon"],
        "default_symbology_role": "primary_polygon_highlight",
        "fallback_behavior": "If commercial values are uncertain, show muted zoning context with a warning.",
    },
    "floodplain": {
        "synonyms": ["floodplain", "flood zone", "fema flood", "100-year floodplain", "500-year floodplain", "floodway", "flood risk"],
        "likely_layers": ["flood", "parcel", "jurisdiction"],
        "likely_fields": ["flood_zone", "fld_zone", "zone_subtype"],
        "expected_geometry_type": ["polygon"],
        "default_symbology_role": "floodplain_overlay",
        "fallback_behavior": "Use requested recurrence when available; otherwise label flood context.",
    },
    "transportation": {
        "synonyms": ["roads", "streets", "centerlines", "major roads", "main roads", "highways", "arterials", "corridors", "high traffic roads", "aadt"],
        "likely_layers": ["transportation", "traffic"],
        "likely_fields": ["road_name", "class", "functional_class", "aadt"],
        "expected_geometry_type": ["polyline"],
        "default_symbology_role": "road_context",
        "fallback_behavior": "If major classification is unavailable, show road context with a warning.",
    },
    "development_activity": {
        "synonyms": ["permits", "permit", "planning cases", "planning case", "development", "subdivision", "construction activity", "recent permits"],
        "likely_layers": ["development", "planning_cases", "permit"],
        "likely_fields": ["permit_number", "case_number", "status", "date", "type"],
        "expected_geometry_type": ["point", "polygon"],
        "default_symbology_role": "point_facility",
        "fallback_behavior": "Mark current permit/planning gaps honestly; use proxies only as context.",
    },
    "historical_layers": {
        "synonyms": ["historical", "archive", "old", "past", "2014", "2013"],
        "required_parameters": ["year"],
        "likely_layers": ["parcel", "zoning", "permit"],
        "likely_fields": ["year", "pin", "zoning"],
        "expected_geometry_type": ["polygon", "point"],
        "default_symbology_role": "historical_layer",
        "fallback_behavior": "Prefer matching historical layers; do not relabel current data as historical.",
    },
    "table_requests": {
        "synonyms": ["table", "list", "spreadsheet", "csv", "records", "attribute table", "rows", "columns", "export"],
        "likely_layers": ["parcel", "zoning", "permit", "planning_cases"],
        "likely_fields": ["pin", "acreage", "municipality", "zoning", "status"],
        "expected_geometry_type": ["table"],
        "default_symbology_role": "table_only",
        "fallback_behavior": "Use returnGeometry=false and bounded row counts.",
    },
    "suitability": {
        "synonyms": ["suitability", "opportunity", "growth", "avoid", "outside floodplain", "near high traffic roads"],
        "likely_layers": ["parcel", "zoning", "flood", "transportation", "traffic"],
        "likely_fields": ["zoning", "flood_zone", "aadt"],
        "expected_geometry_type": ["polygon", "polyline"],
        "default_symbology_role": "primary_polygon_highlight",
        "fallback_behavior": "Return a draft scenario context, not an official recommendation.",
    },
}

COMMERCIAL_ZONING_TERMS = [
    "commercial",
    "business",
    "retail",
    "general commercial",
    "highway commercial",
    "neighborhood commercial",
    "local commercial",
    "office",
    "mixed use",
]

MAJOR_ROAD_TERMS = ["major roads", "main roads", "highways", "arterials", "corridors", "high traffic roads", "aadt"]
