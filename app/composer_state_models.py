"""Models and helpers for saved Map Composer state."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


DEFAULT_SCALE_BAR_CONFIG = {
    "enabled": True,
    "position": "bottom-center",
    "width_percent": 65,
    "style": "enterprise_centered",
    "units": "imperial",
}

DEFAULT_NORTH_ARROW_CONFIG = {
    "enabled": True,
    "position": "top-right",
    "style": "compact_enterprise",
}

DEFAULT_REPORT_SECTION_CONFIG = {
    "include_map_summary": True,
    "include_layer_table": True,
    "include_warnings": True,
    "include_source_notes": True,
    "include_proximity_summary": True,
    "include_parcel_summary": True,
    "include_statistics": True,
    "include_permit_summary": False,
    "include_planning_summary": False,
    "include_development_proxy_summary": False,
}


def utc_timestamp() -> str:
    """Return a compact ISO timestamp for map state updates."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_report_section_config(config: dict[str, Any] | None = None) -> dict[str, bool]:
    """Merge frontend report options with safe defaults."""
    merged = deepcopy(DEFAULT_REPORT_SECTION_CONFIG)
    for key, value in (config or {}).items():
        if key in merged:
            merged[key] = bool(value)
    return merged


def default_scale_bar_config(layout: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the canonical scale bar state from map layout metadata."""
    layout = layout or {}
    config = deepcopy(DEFAULT_SCALE_BAR_CONFIG)
    config["enabled"] = bool(layout.get("scale_bar_enabled", config["enabled"]))
    config["position"] = str(layout.get("scale_bar_position") or config["position"])
    config["width_percent"] = int(layout.get("scale_bar_width_percent") or config["width_percent"])
    config["style"] = str(layout.get("scale_bar_style") or config["style"])
    return config


def default_north_arrow_config(layout: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the canonical north arrow state from map layout metadata."""
    layout = layout or {}
    config = deepcopy(DEFAULT_NORTH_ARROW_CONFIG)
    config["enabled"] = bool(layout.get("north_arrow_enabled", config["enabled"]))
    return config
