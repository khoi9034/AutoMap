"""Rule-based layer semantics for the AutoMap catalog."""

from __future__ import annotations

import re
import unicodedata
from typing import Any


HISTORICAL_YEARS = {str(year) for year in range(2004, 2016)}

SEMANTIC_RULES = [
    {
        "category": "address",
        "keywords": ["address", "addresses", "site address"],
        "aliases": ["address", "addresses", "address points", "site address"],
    },
    {
        "category": "parcel",
        "keywords": ["tax parcel", "tax parcels", "parcel", "parcels"],
        "aliases": ["parcel", "parcels", "tax parcel", "property", "properties", "land records"],
    },
    {
        "category": "cadastral",
        "keywords": ["cadastral"],
        "aliases": ["cadastral", "lot lines", "parcel lines", "property lines"],
    },
    {
        "category": "zoning",
        "keywords": ["zoning"],
        "aliases": ["zoning", "zoning districts", "land use regulation"],
    },
    {
        "category": "jurisdiction",
        "keywords": ["municipal district", "municipaldistrict", "municipal", "municipality"],
        "aliases": ["municipal", "city limits", "town limits", "municipality", "jurisdiction"],
    },
    {
        "category": "jurisdiction",
        "keywords": ["etj", "etj boundary", "extra territorial"],
        "aliases": ["etj", "extra territorial jurisdiction", "planning jurisdiction"],
    },
    {
        "category": "flood",
        "keywords": ["flood", "floodplain", "floodway", "flood hazard"],
        "aliases": ["flood", "floodplain", "flood hazard", "floodway", "100 year flood", "500 year flood"],
    },
    {
        "category": "environmental",
        "keywords": ["hydrology", "stream", "creek", "water", "watershed"],
        "aliases": ["hydrology", "streams", "creeks", "water", "watershed"],
    },
    {
        "category": "schools",
        "keywords": ["school", "schools", "school district"],
        "aliases": [
            "school",
            "schools",
            "elementary school district",
            "middle school district",
            "high school district",
            "attendance zone",
        ],
    },
    {
        "category": "transportation",
        "keywords": ["centerline", "centerlines", "road", "roads", "street", "streets"],
        "aliases": ["roads", "streets", "centerlines", "road centerline", "street centerline"],
    },
    {
        "category": "terrain",
        "keywords": ["contour", "contours", "elevation", "topography"],
        "aliases": ["contours", "elevation", "topography", "terrain"],
    },
    {
        "category": "civic",
        "keywords": ["polling", "voting", "precinct", "election"],
        "aliases": ["polling", "polling place", "voting", "precinct", "election"],
    },
    {
        "category": "public_facilities",
        "keywords": ["county facilities", "facility", "facilities", "government buildings"],
        "aliases": ["county facilities", "government buildings", "public facilities"],
    },
    {
        "category": "boundary",
        "keywords": ["zipcode", "zip code", "postal"],
        "aliases": ["zipcode", "zip code", "postal code"],
    },
]


def slugify(value: Any) -> str:
    """Create a stable lowercase slug for service, layer, and key names."""
    normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", normalized.lower())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug or "unknown"


def service_slug(service_name: str) -> str:
    """Slug the final service path part from names like OpenData/Tax_Parcels."""
    return slugify(str(service_name).split("/")[-1])


def layer_name_slug(layer_name: str) -> str:
    """Slug an ArcGIS layer name for stable catalog keys."""
    return slugify(layer_name)


def build_layer_key(source_key: str, service_name: str, layer_id: int, layer_name: str) -> str:
    """Build stable layer keys for new and legacy Cabarrus OpenData layers."""
    layer_slug = layer_name_slug(layer_name)
    if source_key == "cabarrus_new_opendata":
        return f"cabarrus_new_{service_slug(service_name)}_{layer_id}_{layer_slug}"
    if source_key == "cabarrus_legacy_opendata":
        return f"cabarrus_legacy_opendata_{layer_id}_{layer_slug}"
    return f"{slugify(source_key)}_{service_slug(service_name)}_{layer_id}_{layer_slug}"


def detect_historical_year(*values: Any) -> int | None:
    """Detect legacy historical years from layer/service text."""
    combined = " ".join(str(value or "") for value in values)
    for match in re.findall(r"(?<!\d)(20\d{2})(?!\d)", combined):
        if match in HISTORICAL_YEARS:
            return int(match)
    return None


def infer_layer_semantics(service_name: str, layer_name: str) -> dict[str, Any]:
    """Infer category, aliases, and a canonical topic from service/layer names."""
    combined = f"{service_name} {layer_name}".replace("_", " ").lower()
    for rule in SEMANTIC_RULES:
        if any(keyword in combined for keyword in rule["keywords"]):
            return {
                "category": rule["category"],
                "aliases": rule["aliases"],
                "canonical_topic": rule["category"],
                "planning_use_cases": [rule["category"]],
            }

    return {
        "category": "general",
        "aliases": [layer_name.lower()] if layer_name else [],
        "canonical_topic": "general",
        "planning_use_cases": [],
    }


def date_fields_from_fields(fields: list[dict[str, Any]] | None) -> list[str]:
    """Return date field names from ArcGIS field metadata."""
    date_fields: list[str] = []
    for field in fields or []:
        if field.get("type") == "esriFieldTypeDate" and field.get("name"):
            date_fields.append(field["name"])
    return date_fields


def sort_layer_candidates(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort layer candidates so current verified OpenData layers beat legacy."""
    return sorted(
        records,
        key=lambda item: (
            not bool(item.get("is_verified")),
            bool(item.get("is_historical")),
            int(item.get("source_priority") or 999),
            str(item.get("source_status") or "").startswith("legacy"),
            str(item.get("layer_name") or ""),
        ),
    )
