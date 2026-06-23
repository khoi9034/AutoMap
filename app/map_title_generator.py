"""Deterministic title rules for concise AutoMap draft maps."""

from __future__ import annotations

import re
from typing import Any


GENERIC_TITLES = {
    "",
    "addresses",
    "address",
    "tax parcels",
    "parcels",
    "autoMap draft map".lower(),
    "automap draft map",
    "map",
}


def _title_case(value: str) -> str:
    keep_upper = {"EMS", "ETJ", "PIN", "PIN14", "AADT", "STIP", "FEMA"}
    suffixes = {"ave": "Ave", "avenue": "Ave", "st": "St", "street": "St", "rd": "Rd", "road": "Rd", "dr": "Dr"}
    words: list[str] = []
    for raw in re.split(r"\s+", value.strip()):
        token = raw.strip(", ")
        if not token:
            continue
        upper = token.upper()
        lower = token.lower()
        if upper in keep_upper:
            words.append(upper)
        elif lower in suffixes:
            words.append(suffixes[lower])
        else:
            words.append(token[:1].upper() + token[1:].lower())
    return " ".join(words)


def display_origin_label(result: dict[str, Any]) -> str:
    origin = str(result.get("origin_input") or "").strip()
    return _title_case(origin) if origin else "Origin"


def target_display_label(result: dict[str, Any]) -> str:
    target_type = str(result.get("target_type") or "")
    classification = str(result.get("target_classification") or "")
    if target_type == "nearest_fire_ems_station" or classification == "mixed_fire_ems":
        return "Nearest Fire/EMS Station"
    if target_type == "nearest_fire_station":
        return "Nearest Fire Station"
    if target_type == "nearest_school":
        return "Nearest School"
    if target_type == "nearest_elementary_school":
        return "Nearest Elementary School"
    if target_type == "nearest_middle_school":
        return "Nearest Middle School"
    if target_type == "nearest_high_school":
        return "Nearest High School"
    if target_type == "nearest_library":
        return "Nearest Library"
    if target_type == "nearest_ems_station":
        return "Nearest EMS Station"
    return "Nearest Facility"


def route_mode_label(result: dict[str, Any]) -> str:
    route_mode = str(result.get("route_mode") or ("straight_line_fallback" if result.get("line_geojson_path") else "")).lower()
    if route_mode in {"road_network", "road_network_route", "road_following_draft"}:
        return "Road-following draft route"
    if route_mode in {"straight_line_fallback", "straight_line_reference"}:
        return "Straight-line fallback"
    if route_mode in {"unavailable", "route_unavailable"}:
        return "Route unavailable"
    return "Route draft"


def map_layout_subtitle(result: dict[str, Any] | None) -> str:
    if not result:
        return "Draft preview only."
    route_mode = str(result.get("route_mode") or ("straight_line_fallback" if result.get("line_geojson_path") else "")).lower()
    if route_mode in {"road_network", "road_network_route", "road_following_draft"}:
        return "Road-following draft route. Not official navigation."
    if route_mode in {"straight_line_fallback", "straight_line_reference"}:
        return "Straight-line fallback. Road route unavailable."
    return "Draft preview only."


def generate_proximity_title(result: dict[str, Any]) -> str:
    return _limit_title(f"{target_display_label(result)} from {display_origin_label(result)}")


def _geography_from_prompt(prompt: str) -> str | None:
    lowered = prompt.lower()
    for name in ("Concord", "Harrisburg", "Kannapolis", "Cabarrus County"):
        if name.lower() in lowered:
            return name
    return None


def _limit_title(title: str, max_length: int = 72) -> str:
    cleaned = re.sub(r"\s+", " ", title).strip(" -")
    if len(cleaned) <= max_length:
        return cleaned
    return cleaned[: max_length - 3].rstrip(" ,-/") + "..."


def _prompt_title(prompt: str) -> str | None:
    lowered = prompt.lower()
    geography = _geography_from_prompt(prompt)
    if "commercial" in lowered and "zoning" in lowered:
        return _limit_title(f"Commercial Zoning Around {geography}" if geography else "Commercial Zoning Context")
    if ("school district" in lowered or "school districts" in lowered) and geography:
        return _limit_title(f"School Districts for {geography} Parcels")
    if "parcel" in lowered and ("floodplain" in lowered or "flood" in lowered) and geography:
        return _limit_title(f"Parcels in {geography} Floodplain")
    if "fire station" in lowered and "route" in lowered:
        return "Fire Station Route"
    return None


def generate_map_title(
    raw_prompt: str,
    *,
    recipe: dict[str, Any] | None = None,
    proximity_result: dict[str, Any] | None = None,
    fallback: str | None = None,
) -> str:
    """Return a concise user-facing map title without internal layer-name fallbacks."""
    if proximity_result and proximity_result.get("status") == "ok":
        return generate_proximity_title(proximity_result)

    prompt_title = _prompt_title(raw_prompt)
    if prompt_title:
        return prompt_title

    candidate = str((recipe or {}).get("map_title") or fallback or "").strip()
    if candidate.lower() not in GENERIC_TITLES:
        return _limit_title(candidate)

    return "AutoMap Draft Preview"
