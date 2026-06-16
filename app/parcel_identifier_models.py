"""Parcel identifier models for AutoMap parcel-centered workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass
class ParcelIdentifier:
    """One parsed parcel, PIN/PIN14, or address-like input token."""

    identifier_type: str
    value: str
    normalized_value: str
    source_text: str | None = None
    confidence: float = 0.8
    needs_review: bool = False
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParcelParseResult:
    """Structured result from the parcel input parser."""

    raw_input: str
    input_type: str
    parsed_identifiers: list[ParcelIdentifier] = field(default_factory=list)
    address_candidates: list[ParcelIdentifier] = field(default_factory=list)
    parcel_intent: bool = False
    owner_lookup_requested: bool = False
    privacy_sensitive: bool = False
    needs_review: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["parsed_identifiers"] = [identifier.to_dict() for identifier in self.parsed_identifiers]
        data["address_candidates"] = [identifier.to_dict() for identifier in self.address_candidates]
        return data


@dataclass
class ParcelSetRecord:
    """Stored AutoMap parcel set record."""

    parcel_set_id: str
    raw_input: str
    input_type: str
    parsed_identifiers: list[dict[str, Any]]
    matched_parcels: list[dict[str, Any]]
    unmatched_identifiers: list[dict[str, Any]]
    match_status: str
    source_layer_key: str | None
    created_at: str | None = None
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParcelContextSessionRecord:
    """Stored parcel context session record."""

    session_id: str
    parcel_set_id: str
    raw_prompt: str
    context_layers: list[dict[str, Any]]
    context_recipe: dict[str, Any]
    context_report: dict[str, Any]
    warnings: list[str]
    created_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    """Return a stable UTC timestamp for local parcel workflow records."""
    return datetime.now(UTC).isoformat()
