"""Local WebMap draft export helpers."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.layer_semantics import slugify
from app.recipe_engine import build_recipe
from app.webmap_builder import build_webmap_json, validate_webmap_json


def make_safe_filename(title: str) -> str:
    """Create a safe deterministic JSON filename stem from a map title."""
    slug = slugify(title)[:80] or "automap_webmap"
    return f"{slug}.json"


def save_webmap_json(webmap_json: dict[str, Any], output_dir: str | Path = "outputs/webmaps") -> Path:
    """Save a local-only draft WebMap JSON file under outputs/webmaps."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    filename = f"{timestamp}_{make_safe_filename(webmap_json.get('title') or 'automap_webmap')}"
    target = output_path / filename
    target.write_text(json.dumps(webmap_json, indent=2, default=str), encoding="utf-8")
    return target


def export_recipe_and_webmap(prompt: str) -> dict[str, Any]:
    """Build a recipe, create a draft WebMap JSON object, validate it, and save it."""
    recipe = build_recipe(prompt)
    webmap_json = build_webmap_json(recipe)
    validation = validate_webmap_json(webmap_json)
    webmap_path = save_webmap_json(webmap_json)
    return {
        "recipe": recipe,
        "webmap_json": webmap_json,
        "validation": validation,
        "webmap_path": webmap_path,
    }
