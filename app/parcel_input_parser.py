"""Parse parcel IDs, PINs, PIN14s, addresses, and pasted parcel lists."""

from __future__ import annotations

import csv
import re
from io import StringIO
from typing import Iterable

from app.parcel_identifier_models import ParcelIdentifier, ParcelParseResult


PIN14_RE = re.compile(r"(?<!\d)(\d{14})(?!\d)")
PIN_DASH_RE = re.compile(r"\b\d{3,6}-\d{2,4}-\d{3,8}\b")
PIN_LABEL_RE = re.compile(r"\b(?:pin14|pin|parcel(?:\s+id)?|parcel)\s*[:#]?\s*([A-Za-z0-9][A-Za-z0-9\-]{3,32})\b", re.I)
ADDRESS_RE = re.compile(
    r"\b\d{1,7}\s+[A-Za-z0-9.' -]+?\s+"
    r"(?:st|street|rd|road|ave|avenue|blvd|boulevard|dr|drive|ln|lane|ct|court|cir|circle|hwy|highway|pkwy|parkway|pl|place|way|ter|terrace|trl|trail)"
    r"(?:\s+[NSEW])?\b",
    re.I,
)
PARCEL_INTENT_RE = re.compile(r"\b(my parcels|these parcels|parcel list|pin14s|pins|parcel ids?|property ids?)\b", re.I)
OWNER_LOOKUP_RE = re.compile(r"\b(owner|owned by|property owner|owner name)\b", re.I)


def _normalize_identifier(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).upper()


def _split_pasted_values(raw_input: str) -> Iterable[str]:
    """Split loose comma/newline/CSV pasted values without treating spaces as separators."""
    values: list[str] = []
    try:
        reader = csv.reader(StringIO(raw_input))
        for row in reader:
            values.extend(item.strip() for item in row if item.strip())
    except csv.Error:
        values.extend(item.strip() for item in re.split(r"[\n,;]+", raw_input) if item.strip())
    for value in values:
        cleaned = value.strip().strip('"').strip("'").strip()
        if cleaned:
            yield cleaned


def _add_identifier(
    identifiers: list[ParcelIdentifier],
    *,
    identifier_type: str,
    value: str,
    source_text: str | None = None,
    confidence: float = 0.85,
    needs_review: bool = False,
    notes: list[str] | None = None,
) -> None:
    normalized = _normalize_identifier(value)
    if any(existing.normalized_value == normalized and existing.identifier_type == identifier_type for existing in identifiers):
        return
    identifiers.append(
        ParcelIdentifier(
            identifier_type=identifier_type,
            value=value.strip(),
            normalized_value=normalized,
            source_text=source_text or value.strip(),
            confidence=confidence,
            needs_review=needs_review,
            notes=notes or [],
        )
    )


def _infer_input_type(identifiers: list[ParcelIdentifier], addresses: list[ParcelIdentifier]) -> str:
    types = {identifier.identifier_type for identifier in identifiers}
    if addresses:
        types.add("address")
    if not types:
        return "unknown"
    if len(types) > 1:
        return "mixed"
    only = next(iter(types))
    if only in {"pin", "pin14", "parcel_id", "address"}:
        return only
    return "unknown"


def parse_parcel_input(raw_input: str) -> dict:
    """Extract parcel-centered identifiers from raw text.

    This parser is intentionally conservative. It never assumes owner-name search
    is appropriate and never invents parcel fields.
    """
    raw_input = raw_input or ""
    identifiers: list[ParcelIdentifier] = []
    address_candidates: list[ParcelIdentifier] = []
    warnings: list[str] = []

    for match in PIN14_RE.finditer(raw_input):
        _add_identifier(identifiers, identifier_type="pin14", value=match.group(1), source_text=match.group(0), confidence=0.98)

    for match in PIN_DASH_RE.finditer(raw_input):
        _add_identifier(identifiers, identifier_type="pin", value=match.group(0), source_text=match.group(0), confidence=0.9)

    for match in PIN_LABEL_RE.finditer(raw_input):
        value = match.group(1)
        if PIN14_RE.fullmatch(value):
            identifier_type = "pin14"
        elif "-" in value:
            identifier_type = "pin"
        else:
            identifier_type = "parcel_id"
        _add_identifier(
            identifiers,
            identifier_type=identifier_type,
            value=value,
            source_text=match.group(0),
            confidence=0.84,
        )

    for value in _split_pasted_values(raw_input):
        if PIN14_RE.fullmatch(value):
            _add_identifier(identifiers, identifier_type="pin14", value=value, confidence=0.97)
        elif PIN_DASH_RE.fullmatch(value):
            _add_identifier(identifiers, identifier_type="pin", value=value, confidence=0.9)
        elif re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9\-]{4,32}", value) and any(char.isdigit() for char in value):
            if not ADDRESS_RE.search(value):
                _add_identifier(
                    identifiers,
                    identifier_type="parcel_id",
                    value=value,
                    confidence=0.68,
                    needs_review=True,
                    notes=["Generic parcel-like token; confirm the identifier field before matching."],
                )

    for match in ADDRESS_RE.finditer(raw_input):
        _add_identifier(
            address_candidates,
            identifier_type="address",
            value=match.group(0),
            source_text=match.group(0),
            confidence=0.82,
            needs_review=True,
            notes=["Address matching depends on verified public parcel or address fields."],
        )

    owner_lookup_requested = bool(OWNER_LOOKUP_RE.search(raw_input))
    privacy_sensitive = owner_lookup_requested
    if owner_lookup_requested:
        warnings.append(
            "Owner-name lookup requested. AutoMap will not search by owner unless a verified public field is reviewed."
        )

    parcel_intent = bool(PARCEL_INTENT_RE.search(raw_input)) or bool(identifiers) or bool(address_candidates)
    needs_review = privacy_sensitive or any(identifier.needs_review for identifier in [*identifiers, *address_candidates])
    if parcel_intent and not identifiers and not address_candidates:
        needs_review = True
        warnings.append("Parcel-centered intent was detected, but no parcel identifiers or addresses were parsed.")

    result = ParcelParseResult(
        raw_input=raw_input,
        input_type=_infer_input_type(identifiers, address_candidates),
        parsed_identifiers=identifiers,
        address_candidates=address_candidates,
        parcel_intent=parcel_intent,
        owner_lookup_requested=owner_lookup_requested,
        privacy_sensitive=privacy_sensitive,
        needs_review=needs_review,
        warnings=warnings,
    )
    return result.to_dict()
