"""Shared UI constants and helpers for the local AutoMap web interface."""

from __future__ import annotations

from pathlib import Path

from app.version import AUTOMAP_VERSION


PROJECT_TITLE = "AutoMap: County GIS Request Engine"
SAFETY_BANNER = (
    "AutoMap drafts are for GIS review only. They are not official maps and "
    "local approval is not official publication."
)
EXAMPLE_PROMPTS = [
    "Show parcels in Concord that are in the 100-year floodplain.",
    "Show commercial zoning around Concord.",
    "Show school districts for parcels in Harrisburg.",
    "Show 2014 parcels and zoning.",
    "Map recent permits and planning cases near Kannapolis.",
]
CATALOG_SEARCH_EXAMPLES = ["flood", "zoning", "parcels", "schools", "roads", "addresses"]
DEMO_SCENARIOS = [
    {
        "prompt": "Show parcels in Concord that are in the 100-year floodplain.",
        "expected_layers": ["Tax Parcels", "Municipal District", "FloodPlain100year"],
        "expected_warnings": ["Review parcel/flood intersection before official use."],
        "missing_data_expected": False,
    },
    {
        "prompt": "Show commercial zoning around Concord.",
        "expected_layers": ["Concord Zoning", "Cabarrus County Zoning", "Municipal District"],
        "expected_warnings": ["Commercial zoning filter values require review."],
        "missing_data_expected": False,
    },
    {
        "prompt": "Show school districts for parcels in Harrisburg.",
        "expected_layers": ["Tax Parcels", "Municipal District", "Elementary School District", "Middle School District", "High School District"],
        "expected_warnings": ["School district boundaries require GIS review."],
        "missing_data_expected": False,
    },
    {
        "prompt": "Show 2014 parcels and zoning.",
        "expected_layers": ["Historical 2014 parcel or zoning layers when present"],
        "expected_warnings": ["Historical layers are not selected by default unless requested."],
        "missing_data_expected": False,
    },
    {
        "prompt": "Map recent permits and planning cases near Kannapolis.",
        "expected_layers": ["Municipal District or jurisdiction reference", "available permit or planning fallback if verified"],
        "expected_warnings": ["Recent date fields and planning activity source need review."],
        "missing_data_expected": True,
    },
]


def repo_root() -> Path:
    """Return the AutoMap repository root."""
    return Path(__file__).resolve().parent.parent


def output_file_url(path: str | Path) -> str:
    """Create a local UI URL for a generated output file."""
    return f"/local-file?path={Path(path).as_posix()}"
