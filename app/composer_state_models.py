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
    "include_layer_table": False,
    "include_warnings": True,
    "include_source_notes": True,
    "include_proximity_summary": True,
    "include_parcel_summary": True,
    "include_statistics": False,
    "include_permit_summary": False,
    "include_planning_summary": False,
    "include_development_proxy_summary": False,
    "include_table_preview": False,
    "include_table_export_summary": False,
}

DEFAULT_EXPORT_OPTIONS = {
    "export_mode": "map_exhibit_only",
    "include_key_findings": True,
    "include_appendix": False,
    "preserve_extent": True,
    "preserve_layer_state": True,
    "wysiwyg": True,
}

FULL_REPORT_EXPORT_MODE = "full_report"
MAP_SUMMARY_EXPORT_MODE = "map_summary"
MAP_EXHIBIT_EXPORT_MODE = "map_exhibit_only"


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


def normalize_export_options(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize print/export mode options for WYSIWYG map exhibits."""
    merged = deepcopy(DEFAULT_EXPORT_OPTIONS)
    for key, value in (options or {}).items():
        if key in merged:
            merged[key] = value
    mode = str(merged.get("export_mode") or MAP_EXHIBIT_EXPORT_MODE)
    if mode not in {MAP_EXHIBIT_EXPORT_MODE, MAP_SUMMARY_EXPORT_MODE, FULL_REPORT_EXPORT_MODE}:
        mode = MAP_EXHIBIT_EXPORT_MODE
    merged["export_mode"] = mode
    if mode == FULL_REPORT_EXPORT_MODE:
        merged["include_appendix"] = True
    elif mode == MAP_EXHIBIT_EXPORT_MODE:
        merged["include_appendix"] = False
    merged["include_key_findings"] = bool(merged.get("include_key_findings"))
    merged["include_appendix"] = bool(merged.get("include_appendix"))
    merged["preserve_extent"] = bool(merged.get("preserve_extent"))
    merged["preserve_layer_state"] = bool(merged.get("preserve_layer_state"))
    merged["wysiwyg"] = bool(merged.get("wysiwyg"))
    return merged


def report_config_for_export_mode(config: dict[str, Any] | None, export_options: dict[str, Any] | None) -> dict[str, bool]:
    """Apply export-mode defaults while preserving explicit frontend section choices."""
    explicit = config or {}
    merged = normalize_report_section_config(config)
    mode = normalize_export_options(export_options).get("export_mode")
    if mode == MAP_EXHIBIT_EXPORT_MODE:
        for key in [
            "include_layer_table",
            "include_statistics",
            "include_table_preview",
            "include_table_export_summary",
            "include_permit_summary",
            "include_planning_summary",
            "include_development_proxy_summary",
        ]:
            if key not in explicit:
                merged[key] = False
    elif mode == FULL_REPORT_EXPORT_MODE:
        merged.update(
            {
                "include_layer_table": True,
                "include_warnings": True,
                "include_source_notes": True,
                "include_statistics": True,
            }
        )
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
