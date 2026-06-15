"""Models for user-guided analysis refinement."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AnalysisRefinementOptionType(StrEnum):
    """Supported refinement option identifiers."""

    SUMMARY_ONLY = "summary_only"
    SPLIT_BATCHES = "split_batches"
    NARROW_CONSTRAINT = "narrow_constraint"
    ATTRIBUTE_FILTER = "attribute_filter"
    SMALLER_GEOGRAPHY = "smaller_geography"
    OBJECT_ID_ONLY = "object_id_only"
    UNSUPPORTED = "unsupported"


class AnalysisRefinementSafetyLevel(StrEnum):
    """Human-review safety level for one refinement option."""

    SAFE = "safe"
    REVIEW_NEEDED = "review_needed"
    BLOCKED = "blocked"


@dataclass
class AnalysisRefinementOption:
    """One reviewer-selectable refinement option."""

    option_id: str
    option_type: AnalysisRefinementOptionType
    label: str
    description: str
    estimated_count: int | None = None
    expected_output: str = "review guidance"
    safety_level: AnalysisRefinementSafetyLevel = AnalysisRefinementSafetyLevel.REVIEW_NEEDED
    required_user_input: list[str] = field(default_factory=list)
    suggested_parameters: dict[str, Any] = field(default_factory=dict)
    tradeoffs: list[str] = field(default_factory=list)
    recommended: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable option data."""
        return {
            "option_id": self.option_id,
            "option_type": str(self.option_type),
            "label": self.label,
            "description": self.description,
            "estimated_count": self.estimated_count,
            "expected_output": self.expected_output,
            "safety_level": str(self.safety_level),
            "required_user_input": self.required_user_input,
            "suggested_parameters": self.suggested_parameters,
            "tradeoffs": self.tradeoffs,
            "recommended": self.recommended,
        }


@dataclass
class AnalysisRefinementSession:
    """Stored user-guided refinement session."""

    session_id: str
    source_analysis_run_id: str
    raw_prompt: str
    blocked_reason: str
    broad_count: int | None
    optimized_count: int | None
    safety_limit: int
    options: list[dict[str, Any]]
    selected_option: dict[str, Any] | None = None
    selected_parameters: dict[str, Any] = field(default_factory=dict)
    refined_plan: dict[str, Any] = field(default_factory=dict)
    refined_result: dict[str, Any] = field(default_factory=dict)
    status: str = "open"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable session data."""
        return {
            "session_id": self.session_id,
            "source_analysis_run_id": self.source_analysis_run_id,
            "raw_prompt": self.raw_prompt,
            "blocked_reason": self.blocked_reason,
            "broad_count": self.broad_count,
            "optimized_count": self.optimized_count,
            "safety_limit": self.safety_limit,
            "options": self.options,
            "selected_option": self.selected_option,
            "selected_parameters": self.selected_parameters,
            "refined_plan": self.refined_plan,
            "refined_result": self.refined_result,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
