"""Plain-English request parser for AutoMap map recipes."""

from __future__ import annotations

import re
from typing import Any


GEOGRAPHY_PATTERNS = [
    ("Cabarrus County", "county", [r"\bcabarrus county\b"]),
    ("Concord", "municipality", [r"\bconcord\b"]),
    ("Kannapolis", "municipality", [r"\bkannapolis\b"]),
    ("Harrisburg", "municipality", [r"\bharrisburg\b"]),
    ("Midland", "municipality", [r"\bmidland\b"]),
    ("Mount Pleasant", "municipality", [r"\bmount pleasant\b", r"\bmt\.?\s+pleasant\b"]),
    ("Locust", "municipality", [r"\blocust\b"]),
    ("ETJ", "planning_jurisdiction", [r"\betj\b", r"\bextra territorial jurisdiction\b"]),
    ("municipal limits", "municipal_boundary", [r"\bmunicipal limits\b", r"\bcity limits\b", r"\btown limits\b"]),
    ("countywide", "countywide", [r"\bcountywide\b", r"\bcounty wide\b"]),
]

TOPIC_PATTERNS = [
    (
        "parcel",
        [
            "parcels",
            "parcel",
            "property",
            "properties",
            "tax parcels",
            "tax parcel",
            "parcel id",
            "parcel ids",
            "pin",
            "pins",
            "pin14",
            "pin14s",
            "my parcels",
            "these parcels",
        ],
    ),
    ("zoning", ["zoning", "zone districts", "zoning districts", "commercial zoning", "allowed use", "land use regulation"]),
    ("flood", ["floodplain", "flood plain", "floodway", "flood way", "flood hazard", "flood zone", "flood zones", "fema", "flood"]),
    ("schools", ["school districts", "school district", "school zones", "attendance zones", "schools", "elementary", "middle school", "high school"]),
    ("transportation", ["roads", "road", "streets", "street", "centerlines", "centerline", "corridors", "corridor", "road access", "highway", "highways", "major roads"]),
    ("traffic", ["traffic", "aadt", "annual average daily traffic", "high traffic"]),
    ("transportation_projects", ["stip", "planned road project", "planned road projects", "transportation project", "transportation projects", "road improvement", "road improvements"]),
    ("development", ["development", "development pressure", "growth pressure", "new construction", "buildout", "permit", "permits", "planning case", "planning cases", "planning activity", "subdivision", "subdivisions", "development pipeline", "construction activity"]),
    ("addresses", ["addresses", "address", "address points", "site address"]),
    ("environmental", ["hydrology", "streams", "stream", "creeks", "creek", "water", "watershed"]),
    ("terrain", ["contours", "contour", "elevation", "terrain", "topography"]),
    ("civic", ["voting", "polling", "polling place", "precinct", "precincts", "election"]),
    ("public_facilities", ["facilities", "county facilities", "public facilities", "government buildings"]),
]

TIME_PATTERNS = {
    "recent": [r"\brecent\b", r"\brecently\b", r"\blast\s+\d+\s+(days|weeks|months|years)\b"],
    "current": [r"\bcurrent\b", r"\bnow\b", r"\btoday\b"],
    "historical": [r"\bhistorical\b", r"\bhistory\b", r"\bpast\b", r"\barchive\b", r"\barchived\b"],
}

HISTORICAL_YEAR_RE = re.compile(r"(?<!\d)(2004|2005|2006|2007|2008|2009|2010|2011|2012|2013|2014|2015)(?!\d)")


def _contains_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(phrase.lower())}(?!\w)", text) is not None


def _terms(prompt: str) -> list[str]:
    return [term.strip(".,!?;:()[]{}\"'").lower() for term in prompt.split() if term.strip()]


def _extract_geographies(text: str) -> list[dict[str, str]]:
    geographies: list[dict[str, str]] = []
    for name, geography_type, patterns in GEOGRAPHY_PATTERNS:
        if any(re.search(pattern, text) for pattern in patterns):
            geographies.append({"name": name, "type": geography_type})
    return geographies


def _extract_topics(text: str) -> tuple[list[str], dict[str, Any]]:
    topics: list[str] = []
    details: dict[str, Any] = {
        "flood_frequency": None,
        "school_levels": [],
        "development_terms": [],
        "zoning_modifiers": [],
    }

    for topic, phrases in TOPIC_PATTERNS:
        if any(_contains_phrase(text, phrase) for phrase in phrases):
            topics.append(topic)

    if re.search(r"\b100\s*-?\s*year\b|\b100year\b", text):
        if "flood" not in topics:
            topics.append("flood")
        details["flood_frequency"] = "100_year"
    elif re.search(r"\b500\s*-?\s*year\b|\b500year\b", text):
        if "flood" not in topics:
            topics.append("flood")
        details["flood_frequency"] = "500_year"

    if "schools" in topics:
        if re.search(r"\belementary\b", text):
            details["school_levels"].append("elementary")
        if re.search(r"\bmiddle\b", text):
            details["school_levels"].append("middle")
        if re.search(r"\bhigh\b", text):
            details["school_levels"].append("high")
        if "school district" in text and not details["school_levels"]:
            details["school_levels"] = ["elementary", "middle", "high"]

    if "development" in topics:
        if re.search(r"\bpermits?\b", text):
            details["development_terms"].append("permits")
        if re.search(r"\bplanning cases?\b", text):
            details["development_terms"].append("planning_cases")
        if re.search(r"\bsubdivisions?\b", text):
            details["development_terms"].append("subdivision_activity")
        if re.search(r"\bdevelopment pipeline\b", text):
            details["development_terms"].append("development_pipeline")
        if re.search(r"\bconstruction activity\b|\bnew construction\b", text):
            details["development_terms"].append("construction_activity")

    if "zoning" in topics:
        for modifier in ["commercial", "industrial", "residential"]:
            if re.search(rf"\b{modifier}\b", text):
                details["zoning_modifiers"].append(modifier)

    return topics, details


def _extract_time(text: str) -> tuple[list[str], int | None]:
    time_references: list[str] = []
    for label, patterns in TIME_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            time_references.append(label)

    year_match = HISTORICAL_YEAR_RE.search(text)
    historical_year = int(year_match.group(1)) if year_match else None
    if historical_year is not None and "historical" not in time_references:
        time_references.append("historical")

    if not time_references:
        time_references.append("current")

    return time_references, historical_year


def _requested_output_type(text: str) -> str:
    if re.search(r"\bpdf\b|\bprint\b|\bexport\b", text):
        return "export"
    if re.search(r"\blist\b|\btable\b|\bcsv\b", text):
        return "table"
    return "map_recipe"


def _analysis_intent(text: str) -> str:
    if re.search(r"\bintersect\b|\boverlap\b|\bin the\b|\bwithin\b", text):
        return "overlay_intersection"
    if re.search(r"\bnear\b|\baround\b|\bclose to\b|\bwithin\s+\d+", text):
        return "proximity"
    if re.search(r"\bfilter\b|\bwhere\b|\bshow\b|\bmap\b", text):
        return "filter_display"
    return "display"


def parse_prompt(prompt: str) -> dict[str, Any]:
    """Parse a GIS map request into rule-based request metadata."""
    normalized = prompt.lower()
    topics, topic_details = _extract_topics(normalized)
    time_references, historical_year = _extract_time(normalized)

    return {
        "raw_prompt": prompt,
        "normalized_prompt": normalized,
        "terms": _terms(prompt),
        "geography_terms": _extract_geographies(normalized),
        "topics": topics,
        "topic_details": topic_details,
        "time_references": time_references,
        "historical_year": historical_year,
        "requested_output_type": _requested_output_type(normalized),
        "analysis_intent": _analysis_intent(normalized),
    }
