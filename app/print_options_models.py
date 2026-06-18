"""Print/export option helpers for local draft exhibits."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


MAP_EXHIBIT_EXPORT_MODE = "map_exhibit_only"
MAP_PLUS_SUMMARY_EXPORT_MODE = "map_plus_summary"
FULL_REPORT_EXPORT_MODE = "full_report"
LEGACY_MAP_SUMMARY_EXPORT_MODE = "map_summary"

PRINT_EXPORT_MODES = {
    MAP_EXHIBIT_EXPORT_MODE,
    MAP_PLUS_SUMMARY_EXPORT_MODE,
    FULL_REPORT_EXPORT_MODE,
}

DEFAULT_PRINT_EXPORT_OPTIONS = {
    "export_mode": MAP_EXHIBIT_EXPORT_MODE,
    "include_map_summary": True,
    "include_key_findings": True,
    "include_layer_table": False,
    "include_warnings": True,
    "include_source_notes": False,
    "include_statistics": False,
    "include_parcel_summary": False,
    "include_proximity_summary": True,
    "include_permit_summary": False,
    "include_planning_summary": False,
    "include_development_proxy_summary": False,
    "include_appendix": False,
    "include_draft_disclaimer": True,
    "preserve_extent": True,
    "preserve_layer_state": True,
    "wysiwyg": True,
}

CAMEL_TO_SNAKE = {
    "exportMode": "export_mode",
    "includeMapSummary": "include_map_summary",
    "includeKeyFindings": "include_key_findings",
    "includeLayerTable": "include_layer_table",
    "includeWarnings": "include_warnings",
    "includeSourceNotes": "include_source_notes",
    "includeStatistics": "include_statistics",
    "includeParcelSummary": "include_parcel_summary",
    "includeProximitySummary": "include_proximity_summary",
    "includePermitSummary": "include_permit_summary",
    "includePlanningSummary": "include_planning_summary",
    "includeDevelopmentProxySummary": "include_development_proxy_summary",
    "includeAppendix": "include_appendix",
    "includeDraftDisclaimer": "include_draft_disclaimer",
}

REPORT_CONFIG_KEYS = {
    "include_map_summary",
    "include_layer_table",
    "include_warnings",
    "include_source_notes",
    "include_proximity_summary",
    "include_parcel_summary",
    "include_statistics",
    "include_permit_summary",
    "include_planning_summary",
    "include_development_proxy_summary",
}

SECTION_LABELS = {
    "map_summary": "Map summary",
    "key_findings": "Key findings",
    "proximity_summary": "Proximity summary",
    "parcel_summary": "Parcel summary",
    "statistics": "Statistics",
    "layer_source_table": "Layer source table",
    "warnings": "Warnings and limitations",
    "source_notes": "Source notes",
    "permit_summary": "Permit summary",
    "planning_summary": "Planning summary",
    "development_proxy_summary": "Development proxy summary",
    "appendix": "Appendix",
    "draft_disclaimer": "Draft disclaimer",
}


def _normalize_mode(mode: Any) -> str:
    text = str(mode or MAP_EXHIBIT_EXPORT_MODE)
    if text == LEGACY_MAP_SUMMARY_EXPORT_MODE:
        return MAP_PLUS_SUMMARY_EXPORT_MODE
    if text not in PRINT_EXPORT_MODES:
        return MAP_EXHIBIT_EXPORT_MODE
    return text


def normalize_print_options(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Normalize frontend print options while accepting camelCase or snake_case."""
    merged = deepcopy(DEFAULT_PRINT_EXPORT_OPTIONS)
    provided_keys: set[str] = set()
    for key, value in (options or {}).items():
        normalized_key = CAMEL_TO_SNAKE.get(str(key), str(key))
        if normalized_key in merged:
            provided_keys.add(normalized_key)
            merged[normalized_key] = value

    mode = _normalize_mode(merged.get("export_mode"))
    merged["export_mode"] = mode

    if mode == MAP_EXHIBIT_EXPORT_MODE:
        if "include_layer_table" not in provided_keys:
            merged["include_layer_table"] = False
        if "include_statistics" not in provided_keys:
            merged["include_statistics"] = False
        if "include_appendix" not in provided_keys:
            merged["include_appendix"] = False
        merged["include_source_notes"] = bool(merged.get("include_source_notes"))
    elif mode == MAP_PLUS_SUMMARY_EXPORT_MODE:
        if "include_map_summary" not in provided_keys:
            merged["include_map_summary"] = True
        if "include_key_findings" not in provided_keys:
            merged["include_key_findings"] = True
        if "include_appendix" not in provided_keys:
            merged["include_appendix"] = False
    elif mode == FULL_REPORT_EXPORT_MODE:
        for key in [
            "include_map_summary",
            "include_key_findings",
            "include_layer_table",
            "include_warnings",
            "include_source_notes",
            "include_statistics",
            "include_appendix",
        ]:
            if key not in provided_keys:
                merged[key] = True

    for key, value in list(merged.items()):
        if key == "export_mode":
            continue
        if key.startswith("include_") or key in {"preserve_extent", "preserve_layer_state", "wysiwyg"}:
            merged[key] = bool(value)
    return merged


def report_config_from_print_options(
    print_options: dict[str, Any] | None,
    current_config: dict[str, Any] | None = None,
) -> dict[str, bool]:
    """Build report section config from normalized print options."""
    options = normalize_print_options(print_options)
    config = {key: bool(options.get(key)) for key in REPORT_CONFIG_KEYS}
    for key, value in (current_config or {}).items():
        if key in config:
            config[key] = bool(value)
    return config


def included_sections_from_options(options: dict[str, Any] | None = None) -> list[dict[str, str]]:
    """Return user-facing included section metadata for export manifests."""
    normalized = normalize_print_options(options)
    mapping = [
        ("include_map_summary", "map_summary"),
        ("include_key_findings", "key_findings"),
        ("include_proximity_summary", "proximity_summary"),
        ("include_parcel_summary", "parcel_summary"),
        ("include_statistics", "statistics"),
        ("include_layer_table", "layer_source_table"),
        ("include_warnings", "warnings"),
        ("include_source_notes", "source_notes"),
        ("include_permit_summary", "permit_summary"),
        ("include_planning_summary", "planning_summary"),
        ("include_development_proxy_summary", "development_proxy_summary"),
        ("include_appendix", "appendix"),
        ("include_draft_disclaimer", "draft_disclaimer"),
    ]
    return [
        {"section_id": section_id, "label": SECTION_LABELS[section_id]}
        for option_key, section_id in mapping
        if normalized.get(option_key)
    ]


def export_manifest_metadata(options: dict[str, Any] | None, *, locked_map_state_used: bool) -> dict[str, Any]:
    """Build export manifest metadata for local draft packages."""
    normalized = normalize_print_options(options)
    return {
        "exportMode": normalized["export_mode"],
        "includedSections": included_sections_from_options(normalized),
        "lockedMapStateUsed": bool(locked_map_state_used),
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
