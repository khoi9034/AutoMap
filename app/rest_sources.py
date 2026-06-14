"""REST source configuration for ArcGIS catalog inspection."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


REST_SOURCES_PATH = Path("data/rest_sources.seed.json")
REQUIRED_SOURCE_KEYS = {
    "source_key",
    "source_type",
    "base_url",
    "priority",
    "status",
}
SUPPORTED_SOURCE_TYPES = {"arcgis_folder", "arcgis_mapserver"}


def load_rest_sources(path: Path | str = REST_SOURCES_PATH) -> list[dict]:
    """Load and validate REST source seed configuration."""
    source_path = Path(path)
    sources = json.loads(source_path.read_text(encoding="utf-8"))
    validate_rest_sources(sources)
    return sorted(sources, key=lambda item: item["priority"])


def validate_rest_sources(sources: list[dict]) -> None:
    """Validate seed source entries before any live REST calls are made."""
    if not isinstance(sources, list) or not sources:
        raise ValueError("REST source configuration must be a non-empty list.")

    seen_keys: set[str] = set()
    for source in sources:
        missing = REQUIRED_SOURCE_KEYS.difference(source)
        if missing:
            raise ValueError(f"REST source is missing required keys: {sorted(missing)}")

        source_key = source["source_key"]
        if source_key in seen_keys:
            raise ValueError(f"Duplicate REST source_key: {source_key}")
        seen_keys.add(source_key)

        if source["source_type"] not in SUPPORTED_SOURCE_TYPES:
            raise ValueError(f"Unsupported REST source_type: {source['source_type']}")

        parsed_url = urlparse(source["base_url"])
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise ValueError(f"Invalid REST source base_url: {source['base_url']}")

        if not isinstance(source["priority"], int) or source["priority"] < 1:
            raise ValueError("REST source priority must be a positive integer.")

