"""Planning scenario models and constants for AutoMap."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ScenarioType = Literal[
    "commercial_growth_suitability",
    "residential_growth_suitability",
    "development_pressure",
    "constraint_exposure",
    "transportation_access",
    "planning_case_context",
    "flood_avoidance",
    "school_impact_context",
    "historical_change_context",
    "unsupported_scenario",
]

FactorType = Literal["opportunity", "constraint", "context", "proxy"]
FactorDirection = Literal[
    "higher_is_better",
    "lower_is_better",
    "presence_is_good",
    "presence_is_bad",
    "reference_only",
]
ScoringMethod = Literal[
    "attribute_score",
    "proximity_score",
    "intersection_penalty",
    "reference_context",
    "not_executable_yet",
]

EXECUTION_PLAN_ONLY = "scoring_plan_only"
EXECUTION_REFINED = "executable_if_refined"
EXECUTION_BLOCKED = "blocked_by_count"
EXECUTION_SAMPLE = "executed_small_sample"

OFFICIAL_USE_DISCLAIMER = (
    "This AutoMap planning scenario is a transparent draft framework for staff review. "
    "It is not an official planning recommendation, entitlement decision, suitability "
    "finding, permit approval, or capacity determination."
)
CFS_UNTOUCHED_STATEMENT = "CFS repo and database were not accessed or modified by this AutoMap scenario."

SCENARIO_REPORT_REQUIRED_FILES = {
    "scenario_report.html",
    "scenario_report.md",
    "scenario_report.json",
    "scoring_framework.csv",
    "source_coverage.json",
    "export_manifest.json",
}
SCENARIO_REPORT_FORMATS = ["html", "markdown", "json", "csv"]


@dataclass
class ScenarioFactor:
    """One transparent suitability or context factor."""

    factor_key: str
    factor_label: str
    factor_type: FactorType
    layer_keys: list[str] = field(default_factory=list)
    suggested_weight: float = 0.0
    direction: FactorDirection = "reference_only"
    scoring_method: ScoringMethod = "not_executable_yet"
    needs_review: bool = True
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "factor_key": self.factor_key,
            "factor_label": self.factor_label,
            "factor_type": self.factor_type,
            "layer_keys": self.layer_keys,
            "suggested_weight": self.suggested_weight,
            "direction": self.direction,
            "scoring_method": self.scoring_method,
            "needs_review": self.needs_review,
            "notes": self.notes,
        }
