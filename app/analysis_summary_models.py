"""Models for analysis summary analytics and local report exports."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class AnalysisSummaryType(StrEnum):
    """Supported analysis summary sections."""

    COUNT_SUMMARY = "count_summary"
    GROUPED_ATTRIBUTE_SUMMARY = "grouped_attribute_summary"
    CHUNK_SUMMARY = "chunk_summary"
    CONSTRAINT_SUMMARY = "constraint_summary"
    SAFETY_SUMMARY = "safety_summary"
    MISSING_DATA_SUMMARY = "missing_data_summary"
    REFINEMENT_SUMMARY = "refinement_summary"
    UNSUPPORTED_SUMMARY = "unsupported_summary"


ANALYSIS_REPORT_FORMATS = ["html", "markdown", "json", "csv"]
ANALYSIS_REPORT_REQUIRED_FILES = {
    "analysis_report.html",
    "analysis_report.md",
    "analysis_report.json",
    "summary_tables.json",
    "layer_summary.csv",
    "warning_summary.json",
    "export_manifest.json",
}

DRAFT_ONLY_ANALYSIS_REPORT_DISCLAIMER = (
    "This AutoMap analysis report is a local draft review export. It uses counts and summary metadata, "
    "does not publish to ArcGIS, and is not an official GIS layer or official map."
)
CFS_UNTOUCHED_ANALYSIS_STATEMENT = "CFS repo and database were not accessed or modified by this AutoMap analysis report."


@dataclass
class AnalysisSummarySection:
    """One named summary section for an analysis report."""

    summary_type: AnalysisSummaryType
    title: str
    status: str = "ok"
    rows: list[dict[str, Any]] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable section data."""
        return {
            "summary_type": str(self.summary_type),
            "title": self.title,
            "status": self.status,
            "rows": self.rows,
            "notes": self.notes,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisSummaryReport:
    """Normalized analysis summary data before files are exported."""

    report_id: str
    report_title: str
    source_type: str
    source_analysis_run_id: str | None = None
    source_refinement_session_id: str | None = None
    raw_prompt: str = ""
    analysis_status: str = ""
    operation_type: str = ""
    strategy_used: str | None = None
    broad_count: int | None = None
    optimized_count: int | None = None
    safety_limit: int | None = None
    geometry_downloaded: bool = False
    geojson_created: bool = False
    selected_refinement_option: str | None = None
    selected_layers: list[dict[str, Any]] = field(default_factory=list)
    definition_expressions: list[dict[str, Any]] = field(default_factory=list)
    warnings: dict[str, list[str]] = field(default_factory=dict)
    missing_data: list[str] = field(default_factory=list)
    narrowing_suggestions: list[str] = field(default_factory=list)
    grouped_summaries: list[dict[str, Any]] = field(default_factory=list)
    sections: list[AnalysisSummarySection] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    draft_only_disclaimer: str = DRAFT_ONLY_ANALYSIS_REPORT_DISCLAIMER
    cfs_untouched_statement: str = CFS_UNTOUCHED_ANALYSIS_STATEMENT

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-serializable report data."""
        return {
            "report_id": self.report_id,
            "report_title": self.report_title,
            "source_type": self.source_type,
            "source_analysis_run_id": self.source_analysis_run_id,
            "source_refinement_session_id": self.source_refinement_session_id,
            "raw_prompt": self.raw_prompt,
            "analysis_status": self.analysis_status,
            "operation_type": self.operation_type,
            "strategy_used": self.strategy_used,
            "broad_count": self.broad_count,
            "optimized_count": self.optimized_count,
            "safety_limit": self.safety_limit,
            "geometry_downloaded": self.geometry_downloaded,
            "geojson_created": self.geojson_created,
            "selected_refinement_option": self.selected_refinement_option,
            "selected_layers": self.selected_layers,
            "definition_expressions": self.definition_expressions,
            "warnings": self.warnings,
            "missing_data": self.missing_data,
            "narrowing_suggestions": self.narrowing_suggestions,
            "grouped_summaries": self.grouped_summaries,
            "sections": [section.to_dict() for section in self.sections],
            "generated_at": self.generated_at,
            "draft_only_disclaimer": self.draft_only_disclaimer,
            "cfs_untouched_statement": self.cfs_untouched_statement,
            "supported_export_formats": ANALYSIS_REPORT_FORMATS,
        }


@dataclass
class AnalysisReportPackage:
    """Created analysis report package paths and metadata."""

    report_id: str
    report_path: Path
    report_title: str
    source_type: str
    source_analysis_run_id: str | None = None
    source_refinement_session_id: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    validation: dict[str, Any] | None = None
