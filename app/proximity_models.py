"""Models and constants for safe proximity workflows."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


PROXIMITY_REQUEST_TYPES = {
    "nearest_school",
    "nearest_elementary_school",
    "nearest_middle_school",
    "nearest_high_school",
    "nearest_fire_station",
    "nearest_ems_station",
    "nearest_library",
    "nearest_county_facility",
    "nearest_polling_place",
    "containing_fire_district",
    "containing_school_district",
    "custom_destination_address",
    "route_to_address",
    "unsupported_proximity_request",
}

DISTANCE_RINGS_MILES = [0.5, 1, 2, 5, 10]
DEFAULT_MAX_ORIGIN_FEATURES = 25
MAX_TARGET_CANDIDATES = 100
HARD_MAX_TARGET_CANDIDATES = 250
PROXIMITY_OUTPUT_ROOT = "outputs/proximity"
ROUTE_WARNING = "Road-network routing requires an approved routing/network service."


@dataclass
class ProximityRequest:
    """Normalized proximity request metadata."""

    proximity_request_id: str
    raw_prompt: str
    origin_input: str
    origin_type: str
    target_type: str
    target_layer_key: str | None = None
    destination_input: str | None = None
    request_json: dict[str, Any] = field(default_factory=dict)
    status: str = "created"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProximityResult:
    """Stored result metadata for a nearest-facility or route draft workflow."""

    proximity_result_id: str
    proximity_request_id: str
    origin_feature: dict[str, Any] | None
    target_feature: dict[str, Any] | None
    distance_value: float | None
    distance_unit: str = "miles"
    line_geojson_path: str | None = None
    result_json: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    status: str = "needs_review"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
