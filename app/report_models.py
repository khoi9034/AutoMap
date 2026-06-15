"""Models for local AutoMap report/export packages."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SUPPORTED_REPORT_FORMATS = ["html", "markdown", "json", "csv"]
REQUIRED_REPORT_FILES = {
    "report_summary.md",
    "report_summary.html",
    "report_data.json",
    "layer_table.csv",
    "warning_report.json",
    "export_manifest.json",
}


@dataclass
class ReportSource:
    """Normalized source packet inputs for report generation."""

    packet_path: Path
    packet_type: str
    recipe: dict[str, Any]
    webmap: dict[str, Any]
    warnings: dict[str, Any] = field(default_factory=dict)
    layer_review: list[dict[str, Any]] = field(default_factory=list)
    adjustments: dict[str, Any] = field(default_factory=dict)
    approval_receipt: dict[str, Any] = field(default_factory=dict)
    approval_file: dict[str, Any] = field(default_factory=dict)
    publish_receipt: dict[str, Any] = field(default_factory=dict)
    smoke_test_receipt: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportPackage:
    """Created report package paths and summary metadata."""

    report_id: str
    report_path: Path
    report_title: str
    packet_type: str
    packet_path: str
    files: dict[str, str]
    validation: dict[str, Any] | None = None
