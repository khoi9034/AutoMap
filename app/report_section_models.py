"""Optional report section assembly for composer exports."""

from __future__ import annotations

from typing import Any

from app.composer_state_models import normalize_report_section_config


def build_report_sections(
    map_state: dict[str, Any] | None,
    statistics: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build configured report sections from a saved composer map state."""
    state = map_state or {}
    stats = statistics or {}
    options = normalize_report_section_config(config or state.get("report_section_config"))
    sections: list[dict[str, Any]] = []

    if options["include_map_summary"]:
        sections.append(
            {
                "section_key": "map_summary",
                "title": "Map Summary",
                "items": {
                    "title": state.get("map_title"),
                    "subtitle": state.get("map_subtitle"),
                    "request_type": state.get("request_type"),
                    "prompt": state.get("raw_prompt"),
                },
            }
        )
    if options["include_layer_table"]:
        sections.append(
            {
                "section_key": "selected_layers",
                "title": "Selected Layers",
                "visible_layers": state.get("visible_layers") or [],
                "hidden_layers": state.get("hidden_layers") or [],
                "derived_overlays": state.get("derived_overlays") or [],
            }
        )
    if options["include_warnings"]:
        sections.append(
            {
                "section_key": "warnings",
                "title": "Warnings and Limitations",
                "items": state.get("warnings") or [],
            }
        )
    if options["include_source_notes"]:
        sections.append(
            {
                "section_key": "source_notes",
                "title": "Source Notes",
                "items": {
                    "draft_only": "Local draft output. No ArcGIS item was published.",
                    "proxy_sources": "Proxy/reference sources remain context only unless reviewed.",
                },
            }
        )
    if options["include_proximity_summary"] and state.get("proximity_summary"):
        sections.append(
            {
                "section_key": "proximity_summary",
                "title": "Proximity / Distance Summary",
                "items": state.get("proximity_summary"),
            }
        )
    if options["include_parcel_summary"] and state.get("parcel_context"):
        sections.append(
            {
                "section_key": "parcel_summary",
                "title": "Parcel Summary",
                "items": state.get("parcel_context"),
            }
        )
    if options["include_statistics"]:
        sections.append(
            {
                "section_key": "analysis_statistics",
                "title": "Available Statistics",
                "items": stats,
            }
        )
    if options["include_permit_summary"]:
        sections.append({"section_key": "permit_summary", "title": "Permit Summary", "items": stats.get("permit_summary")})
    if options["include_planning_summary"]:
        sections.append(
            {"section_key": "planning_cases_summary", "title": "Planning Cases Summary", "items": stats.get("planning_cases_summary")}
        )
    if options["include_development_proxy_summary"]:
        sections.append(
            {
                "section_key": "development_proxy_summary",
                "title": "Development Proxy Summary",
                "items": stats.get("development_proxy_summary"),
            }
        )

    return {"config": options, "sections": sections}
