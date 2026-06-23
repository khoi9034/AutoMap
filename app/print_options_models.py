"""Print/export option helpers for local draft exhibits."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


MAP_SHEET_EXPORT_MODE = "map_sheet"
MAP_EXHIBIT_EXPORT_MODE = "map_exhibit_only"
MAP_PLUS_SUMMARY_EXPORT_MODE = "map_plus_summary"
FULL_REPORT_EXPORT_MODE = "full_report"
LEGACY_MAP_SUMMARY_EXPORT_MODE = "map_summary"

PRINT_EXPORT_MODES = {
    MAP_SHEET_EXPORT_MODE,
    MAP_EXHIBIT_EXPORT_MODE,
    MAP_PLUS_SUMMARY_EXPORT_MODE,
    FULL_REPORT_EXPORT_MODE,
}

DEFAULT_PRINT_EXPORT_OPTIONS = {
    "export_mode": MAP_SHEET_EXPORT_MODE,
    "include_map_summary": False,
    "include_key_findings": False,
    "include_layer_table": False,
    "include_warnings": False,
    "include_source_notes": False,
    "include_statistics": False,
    "include_parcel_summary": False,
    "include_proximity_summary": False,
    "include_permit_summary": False,
    "include_planning_summary": False,
    "include_development_proxy_summary": False,
    "include_appendix": False,
    "include_draft_disclaimer": True,
    "sheet_size_preset": "letter",
    "sheet_width": 8.5,
    "sheet_height": 11.0,
    "sheet_units": "inches",
    "sheet_orientation": "landscape",
    "sheet_dpi": 300,
    "sheet_margin": "narrow",
    "map_frame_fill": "fit_page",
    "scale_mode": "fit_extent",
    "fixed_scale": "4800",
    "custom_scale": 4800,
    "include_title": True,
    "include_subtitle": True,
    "include_legend": True,
    "include_scale_bar": True,
    "include_north_arrow": True,
    "include_source_note": True,
    "include_draft_watermark": True,
    "include_scope_note": True,
    "include_real_publish_note": True,
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
    "sheetSizePreset": "sheet_size_preset",
    "sheetWidth": "sheet_width",
    "sheetHeight": "sheet_height",
    "sheetUnits": "sheet_units",
    "sheetOrientation": "sheet_orientation",
    "sheetDpi": "sheet_dpi",
    "sheetMargin": "sheet_margin",
    "mapFrameFill": "map_frame_fill",
    "scaleMode": "scale_mode",
    "fixedScale": "fixed_scale",
    "customScale": "custom_scale",
    "includeTitle": "include_title",
    "includeSubtitle": "include_subtitle",
    "includeLegend": "include_legend",
    "includeScaleBar": "include_scale_bar",
    "includeNorthArrow": "include_north_arrow",
    "includeSourceNote": "include_source_note",
    "includeDraftWatermark": "include_draft_watermark",
    "includeScopeNote": "include_scope_note",
    "includeRealPublishNote": "include_real_publish_note",
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
    "map_sheet": "Map sheet",
    "title": "Title",
    "subtitle": "Subtitle",
    "legend": "Legend",
    "scale_bar": "Scale bar",
    "north_arrow": "North arrow",
    "source_note": "Source note",
    "draft_watermark": "Draft watermark",
}

BOOL_OPTION_KEYS = {
    key
    for key in DEFAULT_PRINT_EXPORT_OPTIONS
    if key.startswith("include_") or key in {"preserve_extent", "preserve_layer_state", "wysiwyg"}
}

SHEET_PRESETS = {"letter", "tabloid", "arch_d", "arch_e", "square_12", "custom"}
SHEET_ORIENTATIONS = {"portrait", "landscape"}
SHEET_DPI_VALUES = {150, 300}
SHEET_MARGINS = {"none", "narrow", "standard"}
MAP_FRAME_FILLS = {"fit_width", "fit_page", "fixed_scale"}
SCALE_MODES = {"fit_extent", "fixed_scale"}
FIXED_SCALES = {"2400", "4800", "12000", "24000", "custom"}


def _normalize_mode(mode: Any) -> str:
    text = str(mode or MAP_SHEET_EXPORT_MODE)
    if text == LEGACY_MAP_SUMMARY_EXPORT_MODE:
        return MAP_PLUS_SUMMARY_EXPORT_MODE
    if text == MAP_EXHIBIT_EXPORT_MODE:
        return MAP_SHEET_EXPORT_MODE
    if text not in PRINT_EXPORT_MODES:
        return MAP_SHEET_EXPORT_MODE
    return text


def _bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() not in {"", "0", "false", "no", "off"}
    return bool(value)


def _clamped_float(value: Any, default: float, *, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(parsed, minimum), maximum)


def _normalize_sheet_options(options: dict[str, Any]) -> None:
    if str(options.get("sheet_size_preset")) not in SHEET_PRESETS:
        options["sheet_size_preset"] = DEFAULT_PRINT_EXPORT_OPTIONS["sheet_size_preset"]
    options["sheet_width"] = _clamped_float(options.get("sheet_width"), 8.5, minimum=4, maximum=60)
    options["sheet_height"] = _clamped_float(options.get("sheet_height"), 11.0, minimum=4, maximum=60)
    options["sheet_units"] = "inches"
    if str(options.get("sheet_orientation")) not in SHEET_ORIENTATIONS:
        options["sheet_orientation"] = DEFAULT_PRINT_EXPORT_OPTIONS["sheet_orientation"]
    try:
        dpi = int(options.get("sheet_dpi"))
    except (TypeError, ValueError):
        dpi = int(DEFAULT_PRINT_EXPORT_OPTIONS["sheet_dpi"])
    options["sheet_dpi"] = dpi if dpi in SHEET_DPI_VALUES else int(DEFAULT_PRINT_EXPORT_OPTIONS["sheet_dpi"])
    if str(options.get("sheet_margin")) not in SHEET_MARGINS:
        options["sheet_margin"] = DEFAULT_PRINT_EXPORT_OPTIONS["sheet_margin"]
    if str(options.get("map_frame_fill")) not in MAP_FRAME_FILLS:
        options["map_frame_fill"] = DEFAULT_PRINT_EXPORT_OPTIONS["map_frame_fill"]
    if str(options.get("scale_mode")) not in SCALE_MODES:
        options["scale_mode"] = DEFAULT_PRINT_EXPORT_OPTIONS["scale_mode"]
    if str(options.get("fixed_scale")) not in FIXED_SCALES:
        options["fixed_scale"] = DEFAULT_PRINT_EXPORT_OPTIONS["fixed_scale"]
    try:
        custom_scale = int(options.get("custom_scale"))
    except (TypeError, ValueError):
        custom_scale = int(DEFAULT_PRINT_EXPORT_OPTIONS["custom_scale"])
    options["custom_scale"] = min(max(custom_scale, 100), 250000)


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

    if mode == MAP_SHEET_EXPORT_MODE:
        for key in [
            "include_map_summary",
            "include_key_findings",
            "include_layer_table",
            "include_warnings",
            "include_source_notes",
            "include_statistics",
            "include_parcel_summary",
            "include_proximity_summary",
            "include_permit_summary",
            "include_planning_summary",
            "include_development_proxy_summary",
            "include_appendix",
        ]:
            if key not in provided_keys:
                merged[key] = False
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
        if key in BOOL_OPTION_KEYS:
            merged[key] = _bool(value)
    _normalize_sheet_options(merged)
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
        ("export_mode", "map_sheet"),
        ("include_title", "title"),
        ("include_subtitle", "subtitle"),
        ("include_legend", "legend"),
        ("include_scale_bar", "scale_bar"),
        ("include_north_arrow", "north_arrow"),
        ("include_source_note", "source_note"),
        ("include_draft_watermark", "draft_watermark"),
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
    sections: list[dict[str, str]] = []
    for option_key, section_id in mapping:
        if option_key == "export_mode":
            if normalized.get("export_mode") == MAP_SHEET_EXPORT_MODE:
                sections.append({"section_id": section_id, "label": SECTION_LABELS[section_id]})
            continue
        if normalized.get(option_key):
            sections.append({"section_id": section_id, "label": SECTION_LABELS[section_id]})
    return sections


def export_manifest_metadata(options: dict[str, Any] | None, *, locked_map_state_used: bool) -> dict[str, Any]:
    """Build export manifest metadata for local draft packages."""
    normalized = normalize_print_options(options)
    return {
        "exportMode": normalized["export_mode"],
        "includedSections": included_sections_from_options(normalized),
        "sheetSize": {
            "preset": normalized["sheet_size_preset"],
            "width": normalized["sheet_width"],
            "height": normalized["sheet_height"],
            "units": normalized["sheet_units"],
            "orientation": normalized["sheet_orientation"],
            "dpi": normalized["sheet_dpi"],
            "margin": normalized["sheet_margin"],
            "mapFrameFill": normalized["map_frame_fill"],
        },
        "mapScale": {
            "scaleMode": normalized["scale_mode"],
            "fixedScale": normalized["fixed_scale"],
            "customScale": normalized["custom_scale"],
        },
        "mapFurniture": {
            "title": normalized["include_title"],
            "subtitle": normalized["include_subtitle"],
            "legend": normalized["include_legend"],
            "scaleBar": normalized["include_scale_bar"],
            "northArrow": normalized["include_north_arrow"],
            "sourceNote": normalized["include_source_note"],
            "draftWatermark": normalized["include_draft_watermark"],
            "scopeNote": normalized["include_scope_note"],
            "realPublishNote": normalized["include_real_publish_note"],
        },
        "lockedMapStateUsed": bool(locked_map_state_used),
        "generatedAt": datetime.now(UTC).replace(microsecond=0).isoformat(),
    }
