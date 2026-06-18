"""Safety limits for AutoMap table requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MAX_PREVIEW_ROWS = 100
MAX_EXPORT_ROWS = 2000
HARD_MAX_EXPORT_ROWS = 5000
MAX_FIELDS = 50


@dataclass(frozen=True)
class TableSafetyDecision:
    safety_status: str
    export_ready: bool
    blocked_reasons: list[str]
    refinement_suggestions: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "safety_status": self.safety_status,
            "export_ready": self.export_ready,
            "blocked_reasons": self.blocked_reasons,
            "refinement_suggestions": self.refinement_suggestions,
            "limits": {
                "max_preview_rows": MAX_PREVIEW_ROWS,
                "max_export_rows": MAX_EXPORT_ROWS,
                "hard_max_export_rows": HARD_MAX_EXPORT_ROWS,
                "max_fields": MAX_FIELDS,
            },
        }


def evaluate_table_safety(estimated_count: int | None, field_count: int) -> TableSafetyDecision:
    """Return bounded export safety decision for a table recipe."""
    count = int(estimated_count or 0)
    blocked: list[str] = []
    suggestions = [
        "Use a smaller geography.",
        "Add a specific year or date range.",
        "Choose a specific layer or record type.",
        "Limit to selected parcels or a smaller batch.",
    ]
    if field_count > MAX_FIELDS:
        blocked.append(f"Requested field count {field_count} exceeds max_fields={MAX_FIELDS}.")
    if count > HARD_MAX_EXPORT_ROWS:
        blocked.append(f"Estimated row count {count} exceeds hard_max_export_rows={HARD_MAX_EXPORT_ROWS}.")
        return TableSafetyDecision("blocked_by_count", False, blocked, suggestions)
    if count > MAX_EXPORT_ROWS:
        blocked.append(f"Estimated row count {count} exceeds max_export_rows={MAX_EXPORT_ROWS}; preview only until refined.")
        return TableSafetyDecision("preview_only_needs_refinement", False, blocked, suggestions)
    if blocked:
        return TableSafetyDecision("blocked_by_fields", False, blocked, suggestions)
    return TableSafetyDecision("export_ready", True, [], [])
