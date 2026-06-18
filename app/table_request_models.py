"""Constants and helpers for table request recipes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4


TABLE_INTENTS = {
    "table_request",
    "data_export",
    "parcel_table",
    "permit_table",
    "planning_case_table",
    "zoning_table",
    "historical_table",
    "attribute_table",
    "map_and_table_request",
    "unsupported_table_request",
}

TABLE_OUTPUT_FORMATS = ["csv", "json", "markdown"]


def new_table_request_id() -> str:
    return f"table_{uuid4().hex[:12]}"


def new_table_export_id() -> str:
    return f"table_export_{uuid4().hex[:12]}"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def table_recipe_shell(raw_prompt: str, table_intent: str, title: str) -> dict[str, Any]:
    return {
        "table_request_id": new_table_request_id(),
        "table_title": title,
        "raw_prompt": raw_prompt,
        "table_intent": table_intent,
        "source_layers": [],
        "selected_fields": [],
        "filters": [],
        "where_clauses": [],
        "geography_filter": None,
        "time_filter": None,
        "historical_year": None,
        "output_formats": TABLE_OUTPUT_FORMATS,
        "estimated_count": None,
        "safety_status": "needs_planning",
        "missing_data_needed": [],
        "warnings": [],
        "preview_rows": [],
        "export_ready": False,
        "blocked_reasons": [],
        "refinement_suggestions": [],
        "query_options": {"returnGeometry": False},
        "created_at": utc_now(),
    }
