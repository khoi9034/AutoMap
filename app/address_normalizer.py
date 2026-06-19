"""Conservative address normalization helpers for verified public lookups."""

from __future__ import annotations

import re
from typing import Any


DIRECTION_ALIASES = {
    "n": "n",
    "north": "n",
    "s": "s",
    "south": "s",
    "e": "e",
    "east": "e",
    "w": "w",
    "west": "w",
    "ne": "ne",
    "northeast": "ne",
    "nw": "nw",
    "northwest": "nw",
    "se": "se",
    "southeast": "se",
    "sw": "sw",
    "southwest": "sw",
}

SUFFIX_PAIRS = {
    "ave": "avenue",
    "st": "street",
    "rd": "road",
    "dr": "drive",
    "ln": "lane",
    "blvd": "boulevard",
    "ct": "court",
    "cir": "circle",
    "pkwy": "parkway",
    "hwy": "highway",
    "pl": "place",
    "ter": "terrace",
    "trl": "trail",
}
SUFFIX_ALIASES = {short: short for short in SUFFIX_PAIRS}
SUFFIX_ALIASES.update({long: short for short, long in SUFFIX_PAIRS.items()})


def normalize_address_text(value: str) -> str:
    """Normalize punctuation, casing, and spacing without inventing content."""
    cleaned = str(value or "").strip().lower()
    cleaned = re.sub(r"[.,;:#]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def normalize_for_compare(value: str) -> str:
    """Return an uppercase alphanumeric comparison key for address strings."""
    return re.sub(r"[^A-Z0-9]", "", str(value or "").upper())


def suffix_variants(suffix: str | None) -> list[str]:
    """Return short/long suffix variants for a parsed suffix."""
    if not suffix:
        return []
    canonical = SUFFIX_ALIASES.get(suffix.lower(), suffix.lower())
    variants = [canonical]
    long = SUFFIX_PAIRS.get(canonical)
    if long:
        variants.append(long)
    return _dedupe(variants)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        clean = normalize_address_text(value)
        if clean and clean not in seen:
            seen.add(clean)
            output.append(clean)
    return output


def _strip_prompt_labels(value: str) -> str:
    text = normalize_address_text(value)
    text = re.sub(r"^(?:my\s+)?(?:home|address)\s+", "", text)
    text = re.sub(r"^(?:origin|from)\s+", "", text)
    text = re.split(r"\b(?:owner|owned by|property owner|owner name)\b", text, maxsplit=1)[0]
    return text.strip()


def parse_address(value: str) -> dict[str, Any]:
    """Parse a simple public street address into safe matching parts."""
    cleaned = _strip_prompt_labels(value)
    zip_code: str | None = None
    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b$", cleaned)
    if zip_match:
        zip_code = zip_match.group(1)
        cleaned = cleaned[: zip_match.start()].strip(" ,")

    city: str | None = None
    if "," in cleaned:
        address_part, city_part = cleaned.split(",", 1)
        cleaned = address_part.strip()
        city = city_part.strip() or None

    tokens = cleaned.split()
    house_number: str | None = None
    street_tokens: list[str] = []
    suffix: str | None = None
    direction: str | None = None
    unit: str | None = None

    if tokens and re.fullmatch(r"\d+[a-z]?", tokens[0]):
        house_number = tokens.pop(0)

    if len(tokens) >= 2 and tokens[-2] in {"apt", "unit", "ste", "suite"}:
        unit = " ".join(tokens[-2:])
        tokens = tokens[:-2]

    if tokens and tokens[-1] in DIRECTION_ALIASES:
        direction = DIRECTION_ALIASES[tokens.pop(-1)]
    if tokens and tokens[-1] in SUFFIX_ALIASES:
        suffix = SUFFIX_ALIASES[tokens.pop(-1)]
    if tokens and tokens[0] in DIRECTION_ALIASES and direction is None:
        direction = DIRECTION_ALIASES[tokens.pop(0)]
    street_tokens = tokens

    street_name_core = " ".join(street_tokens) or None
    suffixes = suffix_variants(suffix)
    normalized_variants = build_address_variants(
        house_number=house_number,
        street_name_core=street_name_core,
        suffix=suffix,
        direction=direction,
    )
    address_like = bool(house_number and street_name_core and (suffix or len(street_tokens) >= 1))
    return {
        "raw_input": value,
        "normalized": cleaned,
        "house_number": house_number,
        "street_name_core": street_name_core,
        "suffix": suffix,
        "suffix_variants": suffixes,
        "direction": direction,
        "city": city,
        "zip": zip_code,
        "unit": unit,
        "address_like": address_like,
        "normalized_variants": normalized_variants,
        "comparison_variants": [normalize_for_compare(item) for item in normalized_variants],
    }


def build_address_variants(
    *,
    house_number: str | None,
    street_name_core: str | None,
    suffix: str | None = None,
    direction: str | None = None,
) -> list[str]:
    """Build normalized address text variants from parsed parts."""
    if not house_number or not street_name_core:
        return []
    variants: list[str] = []
    suffixes = suffix_variants(suffix) or ([suffix] if suffix else [""])
    for suffix_value in suffixes:
        parts = [house_number, street_name_core]
        if suffix_value:
            parts.append(suffix_value)
        if direction:
            variants.append(" ".join([*parts, direction]))
            variants.append(" ".join([house_number, direction, street_name_core, *([suffix_value] if suffix_value else [])]))
        else:
            variants.append(" ".join(parts))
    return _dedupe(variants)


def looks_like_street_address(value: str) -> bool:
    """Return true when a string looks like a user-supplied street address."""
    parsed = parse_address(value)
    if parsed.get("address_like"):
        return True
    text = normalize_address_text(value)
    return bool(re.search(r"\b\d{1,7}\b", text) and any(f" {suffix}" in f" {text} " for suffix in SUFFIX_ALIASES))
