"""Route draft facade that never performs real network routing in v3.1."""

from __future__ import annotations

from typing import Any

from app.proximity_engine import run_route_draft


def build_route_draft(origin_input: str, destination_input: str, **kwargs: Any) -> dict[str, Any]:
    """Build a straight-line route draft and network-route warning."""
    return run_route_draft(origin_input, destination_input, **kwargs)
