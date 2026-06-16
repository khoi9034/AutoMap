"""Scenario workbench models and constants for AutoMap."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.scenario_models import OFFICIAL_USE_DISCLAIMER


WorkbenchStatus = Literal["draft", "needs_review", "ready_for_recipe"]
VariantSafetyLevel = Literal["safe", "review_needed", "blocked"]

VARIANT_OFFICIAL_USE_DISCLAIMER = OFFICIAL_USE_DISCLAIMER
SCENARIO_WORKBENCH_NOTICE = (
    "Scenario scores are planning-support drafts, not official recommendations. "
    "No geometry scoring is executed unless a separate bounded analysis passes safety checks."
)
PROXY_CONTEXT_NOTICE = "Proxy and reference sources are context only unless reviewed."
MISSING_DATA_NOTICE = "Missing official data remains unresolved and is not scored as if present."


@dataclass
class ScenarioVariantRequest:
    """Reviewer-supplied tuning inputs for one scenario variant."""

    variant_name: str = "Scenario variant"
    variant_description: str = ""
    weight_overrides: dict[str, float] = field(default_factory=dict)
    enabled_factors: list[str] = field(default_factory=list)
    disabled_factors: list[str] = field(default_factory=list)
    direction_overrides: dict[str, str] = field(default_factory=dict)
    reviewer_notes: dict[str, str] = field(default_factory=dict)
    reviewer_assumptions: list[str] = field(default_factory=list)

    @classmethod
    def from_mapping(cls, value: dict[str, Any] | None) -> "ScenarioVariantRequest":
        data = dict(value or {})
        return cls(
            variant_name=str(data.get("variant_name") or "Scenario variant"),
            variant_description=str(data.get("variant_description") or ""),
            weight_overrides={str(k): float(v) for k, v in (data.get("weight_overrides") or {}).items()},
            enabled_factors=[str(item) for item in (data.get("enabled_factors") or [])],
            disabled_factors=[str(item) for item in (data.get("disabled_factors") or [])],
            direction_overrides={str(k): str(v) for k, v in (data.get("direction_overrides") or {}).items()},
            reviewer_notes={str(k): str(v) for k, v in (data.get("reviewer_notes") or {}).items()},
            reviewer_assumptions=[str(item) for item in (data.get("reviewer_assumptions") or [])],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "variant_name": self.variant_name,
            "variant_description": self.variant_description,
            "weight_overrides": self.weight_overrides,
            "enabled_factors": self.enabled_factors,
            "disabled_factors": self.disabled_factors,
            "direction_overrides": self.direction_overrides,
            "reviewer_notes": self.reviewer_notes,
            "reviewer_assumptions": self.reviewer_assumptions,
        }
