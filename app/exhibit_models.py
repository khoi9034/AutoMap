"""Models and constants for local county exhibit exports."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


SUPPORTED_EXHIBIT_TYPES = {
    "proximity_exhibit",
    "parcel_context_exhibit",
    "flood_exposure_exhibit",
    "zoning_context_exhibit",
    "scenario_exhibit",
    "general_reference_exhibit",
}

REQUIRED_EXHIBIT_FILES = [
    "exhibit.html",
    "exhibit_data.json",
    "composer_map_state.json",
    "report_sections.json",
    "layer_sources.csv",
    "warnings.json",
    "export_manifest.json",
]


@dataclass(frozen=True)
class ExhibitPackage:
    """Local staff-report-style exhibit package written under ignored outputs."""

    exhibit_id: str
    exhibit_folder: Path
    exhibit_title: str
    exhibit_type: str
    files: list[dict[str, str]]
    validation: dict[str, Any]
    summary: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "exhibit_id": self.exhibit_id,
            "exhibit_folder": self.exhibit_folder.as_posix(),
            "exhibit_title": self.exhibit_title,
            "exhibit_type": self.exhibit_type,
            "files": self.files,
            "validation": self.validation,
            "summary": self.summary,
            "draft_only": True,
            "published": False,
        }
