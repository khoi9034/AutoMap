"""Data models for AutoMap clarification sessions."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal


QuestionType = Literal[
    "single_choice",
    "multi_choice",
    "text",
    "number",
    "distance",
    "year",
    "date_range",
]

BlockingLevel = Literal["optional", "review_needed", "blocks_recipe", "blocks_publish"]


def utc_now_iso() -> str:
    """Return an ISO timestamp for persisted local workflow metadata."""
    return datetime.now(UTC).isoformat()


@dataclass
class ClarificationQuestion:
    """One deterministic GIS review question."""

    question_id: str
    question_text: str
    question_type: QuestionType
    options: list[dict[str, Any]] = field(default_factory=list)
    default_answer: Any = None
    required: bool = False
    related_intent: str | None = None
    related_layer_key: str | None = None
    related_filter: str | None = None
    blocking_level: BlockingLevel = "review_needed"
    help_text: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClarificationAnswer:
    """One human answer to a clarification question."""

    question_id: str
    answer_value: Any
    answer_label: str | None = None
    answered_by: str = "local_reviewer"
    answered_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ClarificationSession:
    """Stored state for an interactive clarification workflow."""

    session_id: str
    raw_prompt: str
    initial_recipe: dict[str, Any]
    questions: list[dict[str, Any]]
    answers: list[dict[str, Any]] = field(default_factory=list)
    refined_prompt: str | None = None
    refined_request_context: dict[str, Any] = field(default_factory=dict)
    refined_recipe: dict[str, Any] | None = None
    changes_summary: dict[str, Any] = field(default_factory=dict)
    status: str = "open"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
