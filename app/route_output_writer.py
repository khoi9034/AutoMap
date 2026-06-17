"""Helpers for writing local route draft GeoJSON outputs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.local_output_server import local_geojson_url, make_local_output_file_id
from app.ui_models import output_file_url, repo_root


def write_route_geojson(
    result: dict[str, Any],
    output_folder: Path,
    file_name: str,
    geojson: dict[str, Any] | None,
    *,
    key_prefix: str,
) -> None:
    """Write one route GeoJSON file under the approved proximity output folder."""
    if not geojson:
        return
    output_path = repo_root() / output_folder
    output_path.mkdir(parents=True, exist_ok=True)
    full_path = output_path / file_name
    full_path.write_text(json.dumps(geojson, indent=2, default=str), encoding="utf-8")
    relative_path = (output_folder / file_name).as_posix()
    result[f"{key_prefix}_geojson_path"] = relative_path
    try:
        result[f"{key_prefix}_geojson_url"] = local_geojson_url(relative_path, output_type="proximity")
        result[f"{key_prefix}_geojson_file_id"] = make_local_output_file_id(relative_path, output_type="proximity")
    except ValueError:
        result[f"{key_prefix}_geojson_url"] = output_file_url(relative_path)

