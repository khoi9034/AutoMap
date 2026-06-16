"""Public nearest-facility facade for AutoMap proximity workflows."""

from __future__ import annotations

from typing import Any

from app.proximity_engine import run_nearest_facility


def find_nearest_facility(origin_input: str, target_type: str, **kwargs: Any) -> dict[str, Any]:
    """Run a bounded nearest facility search."""
    return run_nearest_facility(origin_input, target_type=target_type, **kwargs)
