"""Shared UI constants and helpers for the local AutoMap web interface."""

from __future__ import annotations

from pathlib import Path


PROJECT_TITLE = "AutoMap: County GIS Request Engine"
SAFETY_BANNER = (
    "AutoMap drafts are for GIS review only. They are not official maps and "
    "are not published unless explicitly approved."
)
EXAMPLE_PROMPTS = [
    "Show parcels in Concord that are in the 100-year floodplain.",
    "Show commercial zoning around Concord.",
    "Show school districts for parcels in Harrisburg.",
    "Show 2014 parcels and zoning.",
    "Map recent permits and planning cases near Kannapolis.",
]
CATALOG_SEARCH_EXAMPLES = ["flood", "zoning", "parcels", "schools", "roads", "addresses"]


def repo_root() -> Path:
    """Return the AutoMap repository root."""
    return Path(__file__).resolve().parent.parent


def output_file_url(path: str | Path) -> str:
    """Create a local UI URL for a generated output file."""
    return f"/local-file?path={Path(path).as_posix()}"
