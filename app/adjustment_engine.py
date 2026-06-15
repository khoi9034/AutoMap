"""Human adjustment loop for AutoMap review packets."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any

import yaml

from app.adjustment_models import (
    ADJUSTED_PACKET_FILES,
    normalize_adjustments,
    validate_adjustment_shape,
)
from app.layer_semantics import slugify
from app.review_packet_builder import (
    PROTECTED_OUTPUT_MARKERS,
    build_layer_review_table,
    build_review_summary,
    build_warning_report,
)
from app.webmap_builder import validate_webmap_json


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            deduped.append(text)
            seen.add(text)
    return deduped


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _layer_identifiers(layer: dict[str, Any], recipe_lookup: dict[str, dict[str, Any]] | None = None) -> set[str]:
    values = {
        layer.get("layer_key"),
        layer.get("layer_name"),
        layer.get("original_layer_name"),
        layer.get("title"),
        layer.get("autoMapOriginalTitle"),
        layer.get("autoMapLayerKey"),
        layer.get("autoMapLayerTitle"),
    }
    recipe_layer = (recipe_lookup or {}).get(layer.get("autoMapLayerKey") or layer.get("layer_key"))
    if recipe_layer:
        values.update({recipe_layer.get("layer_key"), recipe_layer.get("layer_name")})
    return {str(value).strip().lower() for value in values if value not in {None, ""}}


def _target_matches_layer(target: str, layer: dict[str, Any], recipe_lookup: dict[str, dict[str, Any]] | None = None) -> bool:
    target_text = str(target).strip().lower()
    identifiers = _layer_identifiers(layer, recipe_lookup)
    return any(
        target_text == identifier
        or (target_text and target_text in identifier)
        or (identifier and identifier in target_text)
        for identifier in identifiers
    )


def _find_matching_adjustment(
    layer: dict[str, Any],
    layer_adjustments: dict[str, Any],
    recipe_lookup: dict[str, dict[str, Any]] | None = None,
) -> tuple[str | None, dict[str, Any] | None]:
    for target, adjustment in layer_adjustments.items():
        if _target_matches_layer(target, layer, recipe_lookup):
            return target, adjustment
    return None, None


def _recipe_lookup(recipe: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        layer["layer_key"]: layer
        for layer in recipe.get("selected_layers") or []
        if layer.get("layer_key")
    }


def _sort_layers_by_order(layers: list[dict[str, Any]], layer_order: list[Any], recipe_lookup: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    if not layer_order:
        return layers
    order_map: dict[int, int] = {}
    for index, layer in enumerate(layers):
        for order_index, target in enumerate(layer_order):
            if _target_matches_layer(str(target), layer, recipe_lookup):
                order_map[index] = order_index
                break
    indexed = sorted(
        enumerate(layers),
        key=lambda item: (order_map.get(item[0], len(layer_order) + item[0]), item[0]),
    )
    return [layer for _index, layer in indexed]


def _definition_expression(layer: dict[str, Any]) -> str | None:
    layer_definition = layer.get("layerDefinition") or {}
    expression = layer_definition.get("definitionExpression")
    if isinstance(expression, str) and expression.strip():
        return expression.strip()
    return None


def _all_warning_items(warnings: dict[str, list[str]]) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for group, group_warnings in warnings.items():
        for warning in _as_list(group_warnings):
            items.append((group, str(warning)))
    return items


def _warning_matches(targets: list[Any], warning: str) -> bool:
    warning_lower = warning.lower()
    for target in targets:
        target_text = str(target).strip().lower()
        if target_text and (target_text == warning_lower or target_text in warning_lower):
            return True
    return False


def _apply_warning_adjustments(
    base_warnings: dict[str, list[str]],
    adjustments: dict[str, Any],
) -> dict[str, Any]:
    resolve_targets = _as_list(adjustments.get("warnings_to_resolve"))
    keep_targets = _as_list(adjustments.get("warnings_to_keep"))
    active = {group: list(values) for group, values in base_warnings.items()}
    resolved: list[dict[str, Any]] = []

    for group, warning in _all_warning_items(base_warnings):
        if _warning_matches(resolve_targets, warning) and not _warning_matches(keep_targets, warning):
            if warning in active.get(group, []):
                active[group].remove(warning)
            resolved.append(
                {
                    "group": group,
                    "warning": warning,
                    "status": "reviewer_resolved",
                    "resolved_at": datetime.now(UTC).isoformat(),
                }
            )

    unresolved_count = sum(
        len(values)
        for group, values in active.items()
        if group != "publishing_blockers"
    )
    active_publish_blockers = list(active.get("publishing_blockers") or [])
    publish_ready_requested = bool(adjustments.get("publish_ready"))
    publish_ready = publish_ready_requested
    if publish_ready_requested and (unresolved_count or active_publish_blockers):
        publish_ready = False
        active.setdefault("publishing_blockers", []).append(
            "Publishing blocked because unresolved warnings remain."
        )

    return {
        "active": {group: _dedupe(values) for group, values in active.items()},
        "reviewer_resolved": resolved,
        "warnings_to_keep": [str(item) for item in keep_targets],
        "warnings_to_resolve": [str(item) for item in resolve_targets],
        "publish_ready_requested": publish_ready_requested,
        "publish_ready": publish_ready,
    }


def load_adjustment_file(path: str | Path) -> dict[str, Any]:
    """Load a YAML or JSON adjustment file."""
    adjustment_path = Path(path)
    text = adjustment_path.read_text(encoding="utf-8")
    if adjustment_path.suffix.lower() == ".json":
        loaded = json.loads(text)
    else:
        loaded = yaml.safe_load(text) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Adjustment file must contain an object at the top level.")
    return normalize_adjustments(loaded)


def validate_adjustment_file(adjustments: dict[str, Any]) -> dict[str, Any]:
    """Validate an adjustment payload."""
    errors = validate_adjustment_shape(adjustments)
    return {"is_valid": not errors, "errors": errors}


def apply_adjustments_to_recipe(recipe: dict[str, Any], adjustments: dict[str, Any]) -> dict[str, Any]:
    """Apply human edits to a recipe copy."""
    normalized = normalize_adjustments(adjustments)
    adjusted = deepcopy(recipe)
    audit = {
        "applied_at": datetime.now(UTC).isoformat(),
        "map_title_changed": False,
        "map_description_changed": False,
        "suggested_extent_overridden": False,
        "layer_order": list(normalized.get("layer_order") or []),
        "layer_adjustments": [],
        "definition_expression_overrides": [],
        "removed_layers": [],
        "reviewer_notes": list(normalized.get("reviewer_notes") or []),
        "missing_data_notes": list(normalized.get("missing_data_notes") or []),
    }

    if normalized.get("map_title"):
        adjusted["map_title"] = normalized["map_title"]
        audit["map_title_changed"] = True
    if normalized.get("map_description"):
        adjusted["map_description"] = normalized["map_description"]
        audit["map_description_changed"] = True
    if normalized.get("suggested_extent_override"):
        adjusted["suggested_extent"] = {
            "type": "human_override",
            "value": normalized["suggested_extent_override"],
            "notes": "Suggested extent was overridden by human review.",
        }
        audit["suggested_extent_overridden"] = True

    selected_layers = []
    for layer in adjusted.get("selected_layers") or []:
        target, layer_adjustment = _find_matching_adjustment(layer, normalized.get("layer_adjustments") or {})
        if layer_adjustment and layer_adjustment.get("remove_layer"):
            audit["removed_layers"].append(
                {
                    "target": target,
                    "layer_key": layer.get("layer_key"),
                    "layer_name": layer.get("layer_name"),
                    "reason": "Removed by human adjustment.",
                }
            )
            continue
        updated_layer = deepcopy(layer)
        if layer_adjustment:
            if "title" in layer_adjustment:
                updated_layer["original_layer_name"] = layer.get("original_layer_name") or layer.get("layer_name")
                updated_layer["layer_name"] = layer_adjustment["title"]
            if "role" in layer_adjustment:
                updated_layer["role"] = layer_adjustment["role"]
            audit["layer_adjustments"].append(
                {
                    "target": target,
                    "layer_key": layer.get("layer_key"),
                    "applied_fields": sorted(layer_adjustment),
                }
            )
        selected_layers.append(updated_layer)
    adjusted["selected_layers"] = _sort_layers_by_order(selected_layers, normalized.get("layer_order") or [])

    if normalized.get("definition_expression_overrides"):
        filter_plan = deepcopy(adjusted.get("filter_plan") or {})
        for target, expression in normalized["definition_expression_overrides"].items():
            for layer in adjusted.get("selected_layers") or []:
                if _target_matches_layer(target, layer):
                    layer_key = layer.get("layer_key")
                    filter_plan.setdefault(layer_key, {})
                    filter_plan[layer_key]["draft_where_clause"] = expression
                    filter_plan[layer_key]["needs_review"] = True
                    filter_plan[layer_key]["review_reason"] = "Definition expression overridden by human reviewer."
                    audit["definition_expression_overrides"].append(
                        {"target": target, "layer_key": layer_key, "definition_expression": expression}
                    )
        adjusted["filter_plan"] = filter_plan

    symbology_overrides = normalized.get("symbology_overrides") or {}
    if symbology_overrides:
        recommendations = list(adjusted.get("symbology_recommendations") or [])
        for target, notes in symbology_overrides.items():
            recommendations.append(
                {
                    "layer": target,
                    "style": str(notes),
                    "source": "human_adjustment",
                }
            )
        adjusted["symbology_recommendations"] = recommendations

    adjusted["human_adjustment"] = {
        "status": "adjusted",
        "publish_ready_requested": normalized.get("publish_ready"),
        "reviewer_notes": normalized.get("reviewer_notes") or [],
        "missing_data_notes": normalized.get("missing_data_notes") or [],
        "audit": audit,
    }
    return adjusted


def apply_adjustments_to_webmap(webmap_json: dict[str, Any], adjustments: dict[str, Any]) -> dict[str, Any]:
    """Apply human edits to a draft WebMap JSON copy."""
    normalized = normalize_adjustments(adjustments)
    adjusted = deepcopy(webmap_json)
    recipe_lookup: dict[str, dict[str, Any]] = {}
    audit = {
        "applied_at": datetime.now(UTC).isoformat(),
        "layer_adjustments": [],
        "definition_expression_overrides": [],
        "symbology_overrides": [],
        "popup_overrides": [],
        "removed_layers": [],
    }

    if normalized.get("map_title"):
        adjusted["title"] = normalized["map_title"]
    if normalized.get("map_description"):
        adjusted["description"] = normalized["map_description"]
    if normalized.get("suggested_extent_override"):
        adjusted.setdefault("initialState", {}).setdefault("viewpoint", {})["targetGeometry"] = normalized["suggested_extent_override"]

    operational_layers = []
    for layer in adjusted.get("operationalLayers") or []:
        target, layer_adjustment = _find_matching_adjustment(layer, normalized.get("layer_adjustments") or {}, recipe_lookup)
        if layer_adjustment and layer_adjustment.get("remove_layer"):
            audit["removed_layers"].append(
                {
                    "target": target,
                    "layer_key": layer.get("autoMapLayerKey"),
                    "title": layer.get("title"),
                    "reason": "Removed by human adjustment.",
                }
            )
            continue
        updated_layer = deepcopy(layer)
        if layer_adjustment:
            for source_key, webmap_key in [
                ("visibility", "visibility"),
                ("opacity", "opacity"),
                ("title", "title"),
                ("role", "autoMapRole"),
                ("showLegend", "showLegend"),
            ]:
                if source_key in layer_adjustment:
                    if source_key == "title":
                        updated_layer["autoMapOriginalTitle"] = layer.get("autoMapOriginalTitle") or layer.get("title")
                    updated_layer[webmap_key] = layer_adjustment[source_key]
            audit["layer_adjustments"].append(
                {
                    "target": target,
                    "layer_key": layer.get("autoMapLayerKey"),
                    "applied_fields": sorted(layer_adjustment),
                }
            )
        operational_layers.append(updated_layer)

    adjusted["operationalLayers"] = _sort_layers_by_order(operational_layers, normalized.get("layer_order") or [], recipe_lookup)

    for target, expression in (normalized.get("definition_expression_overrides") or {}).items():
        for layer in adjusted.get("operationalLayers") or []:
            if _target_matches_layer(target, layer, recipe_lookup):
                layer.setdefault("layerDefinition", {})["definitionExpression"] = expression
                layer["autoMapDefinitionSource"] = "human_adjustment"
                layer["autoMapAdjustmentNeedsReview"] = True
                audit["definition_expression_overrides"].append(
                    {
                        "target": target,
                        "layer_key": layer.get("autoMapLayerKey"),
                        "definition_expression": expression,
                    }
                )

    for target, notes in (normalized.get("symbology_overrides") or {}).items():
        for layer in adjusted.get("operationalLayers") or []:
            if _target_matches_layer(target, layer, recipe_lookup):
                layer["autoMapSymbologyNotes"] = notes
                audit["symbology_overrides"].append({"target": target, "layer_key": layer.get("autoMapLayerKey")})

    for target, popup_override in (normalized.get("popup_overrides") or {}).items():
        for layer in adjusted.get("operationalLayers") or []:
            if _target_matches_layer(target, layer, recipe_lookup):
                existing = layer.get("popupInfo") or {}
                if isinstance(popup_override, dict):
                    layer["popupInfo"] = {**existing, **popup_override}
                else:
                    layer["popupInfo"] = {**existing, "description": str(popup_override)}
                audit["popup_overrides"].append({"target": target, "layer_key": layer.get("autoMapLayerKey")})

    adjusted["autoMapAdjustment"] = {
        "status": "adjusted",
        "publish_ready_requested": normalized.get("publish_ready"),
        "reviewer_notes": normalized.get("reviewer_notes") or [],
        "missing_data_notes": normalized.get("missing_data_notes") or [],
        "audit": audit,
    }
    adjusted["autoMapPublicationStatus"] = "adjusted_draft_only_not_published"
    adjusted["autoMapValidation"] = validate_webmap_json(adjusted)
    return adjusted


def _build_adjusted_review_html(
    adjusted_recipe: dict[str, Any],
    adjusted_webmap: dict[str, Any],
    adjusted_warnings: dict[str, Any],
    layer_review: list[dict[str, Any]],
) -> str:
    title = adjusted_recipe.get("map_title") or adjusted_webmap.get("title") or "Adjusted AutoMap Draft"
    prompt = adjusted_recipe.get("user_intent") or adjusted_recipe.get("parsed_request", {}).get("raw_prompt") or ""
    notes = adjusted_recipe.get("human_adjustment", {}).get("reviewer_notes") or []
    missing_notes = adjusted_recipe.get("human_adjustment", {}).get("missing_data_notes") or []
    layer_rows = "".join(
        "<tr>"
        f"<td>{escape(str(row.get('title') or ''))}</td>"
        f"<td>{escape(str(row.get('role') or ''))}</td>"
        f"<td>{escape(str(row.get('source_status') or ''))}</td>"
        f"<td>{escape(str(row.get('opacity') or ''))}</td>"
        f"<td>{escape(str(row.get('visibility') or ''))}</td>"
        f"<td><a href=\"{escape(str(row.get('layer_url') or ''))}\" target=\"_blank\" rel=\"noreferrer\">{escape(str(row.get('layer_url') or ''))}</a></td>"
        "</tr>"
        for row in layer_review
    )
    filter_rows = "".join(
        "<tr>"
        f"<td>{escape(str(row.get('title') or ''))}</td>"
        f"<td><code>{escape(str(row.get('definition_expression') or ''))}</code></td>"
        "</tr>"
        for row in layer_review
        if row.get("definition_expression")
    )
    active_warnings = adjusted_warnings.get("active") or {}
    warning_sections = "".join(
        f"<section><h3>{escape(group.replace('_', ' ').title())}</h3>"
        + ("<ul>" + "".join(f"<li>{escape(str(item))}</li>" for item in warnings) + "</ul>" if warnings else "<p>None.</p>")
        + "</section>"
        for group, warnings in active_warnings.items()
    )
    resolved = adjusted_warnings.get("reviewer_resolved") or []
    resolved_html = (
        "<ul>"
        + "".join(f"<li>{escape(item['group'])}: {escape(item['warning'])}</li>" for item in resolved)
        + "</ul>"
        if resolved
        else "<p>No warnings were marked reviewer-resolved.</p>"
    )
    raw_webmap = json.dumps(adjusted_webmap, indent=2, default=str)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(title))} - Adjusted AutoMap Review</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #f7f8fa; color: #17202a; line-height: 1.5; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    header, section {{ background: #fff; border: 1px solid #d8dde6; border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
    h1, h2, h3 {{ margin: 0 0 10px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border-bottom: 1px solid #d8dde6; padding: 8px; text-align: left; vertical-align: top; overflow-wrap: anywhere; }}
    th {{ color: #5f6b7a; font-size: 0.9rem; }}
    code, pre {{ background: #eef2f7; border-radius: 6px; padding: 2px 4px; }}
    pre {{ max-height: 520px; overflow: auto; padding: 12px; }}
    a {{ color: #1f6feb; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(str(title))}</h1>
      <p><strong>Original prompt:</strong> {escape(str(prompt))}</p>
      <p>This is an adjusted local draft. It is not published and is not an official map.</p>
      <p><strong>Publish ready:</strong> {escape(str(adjusted_warnings.get('publish_ready')))}</p>
    </header>
    <section>
      <h2>Reviewer Notes</h2>
      {"<ul>" + "".join(f"<li>{escape(str(note))}</li>" for note in notes) + "</ul>" if notes else "<p>No reviewer notes.</p>"}
    </section>
    <section>
      <h2>Selected Layers</h2>
      <table>
        <thead><tr><th>Layer</th><th>Role</th><th>Source</th><th>Opacity</th><th>Visible</th><th>REST URL</th></tr></thead>
        <tbody>{layer_rows or '<tr><td colspan="6">No layers selected.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Filters And Definition Expressions</h2>
      <table>
        <thead><tr><th>Layer</th><th>Expression</th></tr></thead>
        <tbody>{filter_rows or '<tr><td colspan="2">No definition expressions drafted.</td></tr>'}</tbody>
      </table>
    </section>
    <section>
      <h2>Active Warnings</h2>
      {warning_sections}
    </section>
    <section>
      <h2>Reviewer-Resolved Warning Audit</h2>
      {resolved_html}
    </section>
    <section>
      <h2>Missing Data Notes</h2>
      {"<ul>" + "".join(f"<li>{escape(str(note))}</li>" for note in missing_notes) + "</ul>" if missing_notes else "<p>No missing data notes.</p>"}
    </section>
    <section>
      <h2>Adjusted WebMap JSON</h2>
      <details>
        <summary>Show raw adjusted WebMap JSON</summary>
        <pre>{escape(raw_webmap)}</pre>
      </details>
    </section>
  </main>
</body>
</html>
"""


def _build_adjusted_summary(adjusted_recipe: dict[str, Any], adjusted_webmap: dict[str, Any], adjusted_warnings: dict[str, Any]) -> str:
    summary = build_review_summary(adjusted_recipe, adjusted_webmap)
    notes = adjusted_recipe.get("human_adjustment", {}).get("reviewer_notes") or []
    missing_notes = adjusted_recipe.get("human_adjustment", {}).get("missing_data_notes") or []
    resolved = adjusted_warnings.get("reviewer_resolved") or []
    lines = [
        summary.rstrip(),
        "",
        "## Human Adjustment Audit",
        "",
        f"Publish ready requested: {adjusted_warnings.get('publish_ready_requested')}",
        f"Publish ready after validation: {adjusted_warnings.get('publish_ready')}",
        "",
        "### Reviewer Notes",
        "",
    ]
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("No reviewer notes.")
    lines.extend(["", "### Missing Data Notes", ""])
    lines.extend(f"- {note}" for note in missing_notes) if missing_notes else lines.append("No missing data notes.")
    lines.extend(["", "### Reviewer-Resolved Warnings", ""])
    if resolved:
        lines.extend(f"- {item['group']}: {item['warning']}" for item in resolved)
    else:
        lines.append("No warnings were marked reviewer-resolved.")
    return "\n".join(lines).strip() + "\n"


def _build_adjusted_warnings(adjusted_recipe: dict[str, Any], adjusted_webmap: dict[str, Any], adjustments: dict[str, Any]) -> dict[str, Any]:
    base_warnings = build_warning_report(adjusted_recipe, adjusted_webmap)
    result = _apply_warning_adjustments(base_warnings, adjustments)
    result["missing_data_notes"] = list(adjustments.get("missing_data_notes") or [])
    result["reviewer_notes"] = list(adjustments.get("reviewer_notes") or [])
    return result


def write_adjusted_packet(
    original_packet_folder: str | Path,
    adjusted_recipe: dict[str, Any],
    adjusted_webmap: dict[str, Any],
    adjustments: dict[str, Any],
) -> Path:
    """Write adjusted packet files without modifying the original packet."""
    original_path = Path(original_packet_folder)
    root = Path("outputs/review_packets_adjusted")
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    adjusted_path = root / f"{original_path.name}_adjusted_{timestamp}"
    adjusted_path.mkdir(parents=True, exist_ok=False)

    original_recipe = _load_json(original_path / "recipe.json")
    original_webmap = _load_json(original_path / "webmap.json")
    adjusted_warnings = _build_adjusted_warnings(adjusted_recipe, adjusted_webmap, adjustments)
    layer_review = build_layer_review_table(adjusted_recipe, adjusted_webmap)
    summary = _build_adjusted_summary(adjusted_recipe, adjusted_webmap, adjusted_warnings)
    review_html = _build_adjusted_review_html(adjusted_recipe, adjusted_webmap, adjusted_warnings, layer_review)

    applied_adjustments = {
        "adjustments": adjustments,
        "recipe_audit": adjusted_recipe.get("human_adjustment", {}).get("audit", {}),
        "webmap_audit": adjusted_webmap.get("autoMapAdjustment", {}).get("audit", {}),
        "removed_layers": [
            *adjusted_recipe.get("human_adjustment", {}).get("audit", {}).get("removed_layers", []),
            *adjusted_webmap.get("autoMapAdjustment", {}).get("audit", {}).get("removed_layers", []),
        ],
        "definition_expression_overrides": [
            *adjusted_recipe.get("human_adjustment", {}).get("audit", {}).get("definition_expression_overrides", []),
            *adjusted_webmap.get("autoMapAdjustment", {}).get("audit", {}).get("definition_expression_overrides", []),
        ],
        "created_at": datetime.now(UTC).isoformat(),
        "publication_status": "adjusted_draft_only_not_published",
    }

    _write_json(adjusted_path / "original_recipe.json", original_recipe)
    _write_json(adjusted_path / "original_webmap.json", original_webmap)
    _write_json(adjusted_path / "adjusted_recipe.json", adjusted_recipe)
    _write_json(adjusted_path / "adjusted_webmap.json", adjusted_webmap)
    _write_json(adjusted_path / "applied_adjustments.json", applied_adjustments)
    (adjusted_path / "adjusted_review_summary.md").write_text(summary, encoding="utf-8")
    _write_json(adjusted_path / "adjusted_warnings.json", adjusted_warnings)
    _write_json(adjusted_path / "adjusted_layer_review.json", layer_review)
    (adjusted_path / "adjusted_review.html").write_text(review_html, encoding="utf-8")
    return adjusted_path


def apply_adjustments_to_review_packet(packet_folder: str | Path, adjustment_file: str | Path) -> Path:
    """Apply a human adjustment file to an existing review packet."""
    packet_path = Path(packet_folder)
    adjustments = load_adjustment_file(adjustment_file)
    validation = validate_adjustment_file(adjustments)
    if not validation["is_valid"]:
        raise ValueError("; ".join(validation["errors"]))

    recipe = _load_json(packet_path / "recipe.json")
    webmap_json = _load_json(packet_path / "webmap.json")
    adjusted_recipe = apply_adjustments_to_recipe(recipe, adjustments)
    adjusted_webmap = apply_adjustments_to_webmap(webmap_json, adjustments)
    return write_adjusted_packet(packet_path, adjusted_recipe, adjusted_webmap, adjustments)


def _packet_text(packet_path: Path) -> str:
    chunks: list[str] = []
    for file_name in ADJUSTED_PACKET_FILES:
        path = packet_path / file_name
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks).lower()


def _protected_marker(packet_path: Path) -> str | None:
    combined = _packet_text(packet_path)
    for marker in sorted(PROTECTED_OUTPUT_MARKERS):
        if marker in combined:
            return marker
    return None


def validate_adjusted_packet(packet_folder: str | Path) -> dict[str, Any]:
    """Validate an adjusted review packet folder."""
    packet_path = Path(packet_folder)
    errors: list[str] = []
    warnings: list[str] = []

    if not packet_path.exists() or not packet_path.is_dir():
        return {
            "is_valid": False,
            "errors": [f"Adjusted packet folder not found: {packet_path}"],
            "warnings": [],
            "packet_path": str(packet_path),
        }

    missing_files = sorted(file_name for file_name in ADJUSTED_PACKET_FILES if not (packet_path / file_name).exists())
    if missing_files:
        errors.append(f"Missing required adjusted packet files: {', '.join(missing_files)}")

    adjusted_webmap: dict[str, Any] = {}
    applied_adjustments: dict[str, Any] = {}
    adjusted_warnings: dict[str, Any] = {}
    if not missing_files:
        try:
            adjusted_webmap = _load_json(packet_path / "adjusted_webmap.json")
            applied_adjustments = _load_json(packet_path / "applied_adjustments.json")
            adjusted_warnings = _load_json(packet_path / "adjusted_warnings.json")
            _load_json(packet_path / "adjusted_recipe.json")
            _load_json(packet_path / "adjusted_layer_review.json")
        except json.JSONDecodeError as exc:
            errors.append(f"Adjusted packet JSON is invalid: {exc}")

    if adjusted_webmap:
        webmap_validation = validate_webmap_json(adjusted_webmap)
        errors.extend(webmap_validation.get("errors", []))
        warnings.extend(webmap_validation.get("warnings", []))
        for index, layer in enumerate(adjusted_webmap.get("operationalLayers") or []):
            if not layer.get("url"):
                errors.append(f"Operational layer {layer.get('title') or index} is missing URL.")

    removed_layers = applied_adjustments.get("removed_layers") or []
    requested_removals = [
        target
        for target, adjustment in (applied_adjustments.get("adjustments", {}).get("layer_adjustments") or {}).items()
        if isinstance(adjustment, dict) and adjustment.get("remove_layer")
    ]
    if requested_removals and not removed_layers:
        errors.append("Removed layers were requested but not documented.")

    requested_expression_overrides = applied_adjustments.get("adjustments", {}).get("definition_expression_overrides") or {}
    recorded_expression_overrides = applied_adjustments.get("definition_expression_overrides") or []
    if requested_expression_overrides and not recorded_expression_overrides:
        errors.append("Definition expression overrides were requested but not recorded.")

    if adjusted_warnings.get("publish_ready") is True:
        active = adjusted_warnings.get("active") or {}
        unresolved_count = sum(len(_as_list(values)) for values in active.values())
        if unresolved_count:
            errors.append("publish_ready cannot be true while unresolved warnings remain.")

    marker = _protected_marker(packet_path)
    if marker:
        errors.append(f"Generated adjusted packet contains protected or secret marker: {marker}")

    return {
        "is_valid": not errors,
        "errors": _dedupe(errors),
        "warnings": _dedupe(warnings),
        "packet_path": str(packet_path),
        "required_files_present": not missing_files,
        "operational_layer_count": len(adjusted_webmap.get("operationalLayers") or []),
        "publish_ready": adjusted_warnings.get("publish_ready"),
    }


def create_adjustment_template(review_packet_folder: str | Path) -> Path:
    """Create a YAML adjustment template without mutating the review packet."""
    packet_path = Path(review_packet_folder)
    recipe = _load_json(packet_path / "recipe.json")
    webmap_json = _load_json(packet_path / "webmap.json")
    webmap_layers = [
        layer
        for layer in webmap_json.get("operationalLayers") or []
        if layer.get("title") or layer.get("autoMapLayerKey")
    ]
    layer_titles = [layer.get("title") or layer.get("autoMapLayerKey") for layer in webmap_layers]
    warnings = build_warning_report(recipe, webmap_json)
    first_warning = None
    for group_warnings in warnings.values():
        if group_warnings:
            first_warning = group_warnings[0]
            break
    template = {
        "map_title": recipe.get("map_title"),
        "map_description": "Human-reviewed draft. Edit this description before any future publishing phase.",
        "suggested_extent_override": None,
        "layer_order": layer_titles,
        "layer_adjustments": {
            (layer.get("title") or layer.get("autoMapLayerKey")): {
                "visibility": bool(layer.get("visibility", True)),
                "opacity": layer.get("opacity", 0.8),
                "title": layer.get("title") or layer.get("autoMapLayerKey"),
                "role": layer.get("autoMapRole") or "reference_layer",
                "showLegend": bool(layer.get("showLegend", True)),
                "remove_layer": False,
            }
            for layer in webmap_layers
        },
        "definition_expression_overrides": {},
        "symbology_overrides": {},
        "popup_overrides": {},
        "reviewer_notes": [
            "Confirm selected layers, filters, and symbology before official use."
        ],
        "warnings_to_resolve": [],
        "warnings_to_keep": [first_warning] if first_warning else [],
        "missing_data_notes": [],
        "publish_ready": False,
    }
    root = Path("outputs/adjustment_templates")
    root.mkdir(parents=True, exist_ok=True)
    template_path = root / f"{packet_path.name}_adjustments.template.yaml"
    template_path.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")
    return template_path
