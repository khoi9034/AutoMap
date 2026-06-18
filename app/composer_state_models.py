"""Models and helpers for saved Map Composer state."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.print_options_models import (
    DEFAULT_PRINT_EXPORT_OPTIONS,
    MAP_EXHIBIT_EXPORT_MODE,
    MAP_PLUS_SUMMARY_EXPORT_MODE,
    normalize_print_options,
    report_config_from_print_options,
)

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
    "include_layer_table": False,
    "include_warnings": True,
    "include_source_notes": False,
    "include_proximity_summary": True,
    "include_parcel_summary": True,
    "include_statistics": False,
    "include_permit_summary": False,
    "include_planning_summary": False,
    "include_development_proxy_summary": False,
    "include_table_preview": False,
    "include_table_export_summary": False,
}

DEFAULT_EXPORT_OPTIONS = DEFAULT_PRINT_EXPORT_OPTIONS
MAP_SUMMARY_EXPORT_MODE = MAP_PLUS_SUMMARY_EXPORT_MODE


def utc_timestamp() -> str:
    """Return a compact ISO timestamp for map state updates."""
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_report_section_config(config: dict[str, Any] | None = None) -> dict[str, bool]:
    """Merge frontend report options with safe defaults."""
    merged = dict(DEFAULT_REPORT_SECTION_CONFIG)
    for key, value in (config or {}).items():
        if key in merged:
            merged[key] = bool(value)
    return merged


def normalize_export_options(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize print/export mode options for WYSIWYG map exhibits."""
    return normalize_print_options(options)


def report_config_for_export_mode(config: dict[str, Any] | None, export_options: dict[str, Any] | None) -> dict[str, bool]:
    """Apply export-mode defaults while preserving explicit frontend section choices."""
    merged = report_config_from_print_options(export_options, config)
    if normalize_export_options(export_options).get("export_mode") == MAP_EXHIBIT_EXPORT_MODE:
        merged["include_table_preview"] = False
        merged["include_table_export_summary"] = False
    return merged


def default_scale_bar_config(layout: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the canonical scale bar state from map layout metadata."""
    layout = layout or {}
    config = dict(DEFAULT_SCALE_BAR_CONFIG)
    config["enabled"] = bool(layout.get("scale_bar_enabled", config["enabled"]))
    config["position"] = str(layout.get("scale_bar_position") or config["position"])
    config["width_percent"] = int(layout.get("scale_bar_width_percent") or config["width_percent"])
    config["style"] = str(layout.get("scale_bar_style") or config["style"])
    return config


def default_north_arrow_config(layout: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build the canonical north arrow state from map layout metadata."""
    layout = layout or {}
    config = dict(DEFAULT_NORTH_ARROW_CONFIG)
    config["enabled"] = bool(layout.get("north_arrow_enabled", config["enabled"]))
    return config
