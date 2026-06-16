"""Local report writer for AutoMap proximity results."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _target_name(result: dict[str, Any]) -> str:
    target = result.get("target_feature") or {}
    properties = target.get("properties") or {}
    for key in ["NAME", "Name", "name", "FacilityName", "FACILITY", "SCHOOL", "DISTRICT", "DISTRICT_"]:
        value = properties.get(key)
        if value not in {None, ""}:
            return str(value)
    return str(result.get("target_type") or "Target")


def _markdown(result: dict[str, Any]) -> str:
    warnings = result.get("warnings") or []
    warning_lines = "\n".join(f"- {warning}" for warning in warnings) or "- None"
    distance = result.get("distance_value")
    distance_text = "not available" if distance is None else f"{distance} {result.get('distance_unit', 'miles')}"
    return f"""# AutoMap Proximity Report

**Status:** {result.get('status')}

**Origin input:** {result.get('origin_input')}

**Target type:** {result.get('target_type')}

**Nearest/selected target:** {_target_name(result)}

**Distance:** {distance_text}

**Line type:** {result.get('line_type', 'straight-line')}

**Route status:** {result.get('route_status', 'straight_line_supported')}

## Warnings

{warning_lines}

## Limitations

- This is a local draft proximity output for GIS review.
- Straight-line distance is not a road-network driving route.
- No ArcGIS item was published.
- CFS database cfs_dev was not touched.
"""


def _html(markdown_text: str, result: dict[str, Any]) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>AutoMap Proximity Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #172033; }}
    .badge {{ display: inline-block; padding: 0.25rem 0.5rem; border-radius: 4px; background: #e8f1ff; color: #16457a; }}
    pre {{ background: #f5f7fb; padding: 1rem; border-radius: 6px; white-space: pre-wrap; }}
  </style>
</head>
<body>
  <p class="badge">Draft GIS review output</p>
  <pre>{html.escape(markdown_text)}</pre>
  <script type="application/json" id="automap-proximity-data">{html.escape(json.dumps(result, default=str))}</script>
</body>
</html>
"""


def write_proximity_report(output_dir: str | Path, result: dict[str, Any]) -> dict[str, str]:
    """Write Markdown, HTML, JSON, and manifest files for a proximity result."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    md = _markdown(result)
    html_text = _html(md, result)
    files = {
        "proximity_report.md": path / "proximity_report.md",
        "proximity_report.html": path / "proximity_report.html",
        "proximity_result.json": path / "proximity_result.json",
        "export_manifest.json": path / "export_manifest.json",
    }
    files["proximity_report.md"].write_text(md, encoding="utf-8")
    files["proximity_report.html"].write_text(html_text, encoding="utf-8")
    files["proximity_result.json"].write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    manifest = {
        "project": "AutoMap",
        "output_type": "proximity_report",
        "draft_only": True,
        "published": False,
        "files": {name: file_path.as_posix() for name, file_path in files.items() if name != "export_manifest.json"},
    }
    files["export_manifest.json"].write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {name: file_path.as_posix() for name, file_path in files.items()}
