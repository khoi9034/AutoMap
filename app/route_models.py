"""Route draft models and safety defaults for AutoMap proximity maps."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


RouteMode = Literal[
    "road_network",
    "straight_line_fallback",
    "unavailable",
    "road_network_route",
    "road_following_draft",
    "straight_line_reference",
    "route_unavailable",
]


MAX_ROAD_FEATURES = 1000
HARD_MAX_ROAD_FEATURES = 2500
MAX_ROUTE_EXTENT_WIDTH_DEGREES = 0.35
MAX_ROUTE_EXTENT_HEIGHT_DEGREES = 0.35

ROAD_FOLLOWING_DRAFT_WARNING = (
    "Draft route based on public road centerlines. Not official navigation."
)
STRAIGHT_LINE_FALLBACK_WARNING = (
    "Road route unavailable; showing straight-line reference only."
)
ADDRESS_LAYER_HIDDEN_WARNING = "Full address layer hidden to reduce clutter."


@dataclass(slots=True)
class RouteDraftResult:
    """A bounded route-draft attempt result."""

    route_mode: RouteMode
    route_label: str
    route_warning: str
    route_geojson: dict[str, Any] | None = None
    straight_line_geojson: dict[str, Any] | None = None
    route_distance_miles: float | None = None
    road_feature_count: int | None = None
    target_layer_key: str | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
