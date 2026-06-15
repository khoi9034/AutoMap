"""Reviewer approval gate for AutoMap adjusted packets."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from html import escape
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text
import yaml

from app.approval_models import (
    APPROVED_PACKET_FILES,
    normalize_approval,
    validate_approval_shape,
)
from app.db import _quote_identifier, get_engine
from app.layer_semantics import slugify
from app.review_packet_builder import PROTECTED_OUTPUT_MARKERS, build_layer_review_table


APPROVAL_HISTORY_COLUMNS = {
    "source_adjusted_packet": "text",
    "approved_packet_path": "text",
    "reviewer_name": "text",
    "reviewer_role": "text",
    "decision": "text",
    "publish_ready_requested": "boolean",
    "final_publish_ready": "boolean",
    "block_reasons": "jsonb DEFAULT '[]'::jsonb",
    "reviewer_notes": "jsonb DEFAULT '[]'::jsonb",
    "approval_receipt": "jsonb DEFAULT '{}'::jsonb",
    "created_at": "timestamptz DEFAULT now()",
}


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
        text_value = str(value).strip()
        if text_value and text_value not in seen:
            deduped.append(text_value)
            seen.add(text_value)
    return deduped


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _qualified_table(schema_name: str, table_name: str = "review_approval_history") -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def ensure_review_approval_history_table(schema_name: str = "automap") -> None:
    """Create or safely update automap.review_approval_history."""
    schema = _quote_identifier(schema_name)
    table = _qualified_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY
                );
                """
            )
        )
        for column, column_type in APPROVAL_HISTORY_COLUMNS.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(
            text(
                f"""
                CREATE INDEX IF NOT EXISTS review_approval_history_created_at_idx
                ON {table} (created_at DESC);
                """
            )
        )


def record_approval_history(
    approval_receipt: dict[str, Any],
    approved_packet_path: str | Path | None,
    schema_name: str = "automap",
) -> int:
    """Insert one local approval history row."""
    ensure_review_approval_history_table(schema_name)
    table = _qualified_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    source_adjusted_packet, approved_packet_path, reviewer_name,
                    reviewer_role, decision, publish_ready_requested,
                    final_publish_ready, block_reasons, reviewer_notes,
                    approval_receipt, created_at
                )
                VALUES (
                    :source_adjusted_packet, :approved_packet_path, :reviewer_name,
                    :reviewer_role, :decision, :publish_ready_requested,
                    :final_publish_ready, CAST(:block_reasons AS jsonb),
                    CAST(:reviewer_notes AS jsonb), CAST(:approval_receipt AS jsonb),
                    :created_at
                );
                """
            ),
            {
                "source_adjusted_packet": approval_receipt.get("source_adjusted_packet"),
                "approved_packet_path": str(approved_packet_path) if approved_packet_path else None,
                "reviewer_name": approval_receipt.get("reviewer_name"),
                "reviewer_role": approval_receipt.get("reviewer_role"),
                "decision": approval_receipt.get("decision"),
                "publish_ready_requested": approval_receipt.get("publish_ready_requested"),
                "final_publish_ready": approval_receipt.get("final_publish_ready"),
                "block_reasons": json.dumps(approval_receipt.get("block_reasons") or []),
                "reviewer_notes": json.dumps(approval_receipt.get("reviewer_notes") or []),
                "approval_receipt": json.dumps(approval_receipt, default=str),
                "created_at": datetime.now(UTC),
            },
        )
    return 1


def list_approval_history(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """Return recent local approval history rows."""
    ensure_review_approval_history_table(schema_name)
    table = _qualified_table(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT id, source_adjusted_packet, approved_packet_path,
                       reviewer_name, reviewer_role, decision,
                       publish_ready_requested, final_publish_ready,
                       block_reasons, reviewer_notes, created_at
                FROM {table}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return [dict(row) for row in rows]


def _active_warning_items(adjusted_warnings: dict[str, Any]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for group, warnings in (adjusted_warnings.get("active") or {}).items():
        for warning in _as_list(warnings):
            text_value = str(warning)
            items.append(
                {
                    "warning_id": _warning_id(group, text_value),
                    "group": str(group),
                    "warning": text_value,
                }
            )
    return items


def _warning_id(group: str, warning: str) -> str:
    return slugify(f"{group}_{warning}")[:120] or "warning"


def _resolution_matches(resolution: dict[str, Any], warning_item: dict[str, str]) -> bool:
    target = slugify(str(resolution.get("warning_id") or ""))
    if not target:
        return False
    candidates = {
        warning_item["warning_id"],
        slugify(warning_item["warning"]),
        slugify(warning_item["group"]),
    }
    return any(target == candidate or target in candidate or candidate in target for candidate in candidates)


def _missing_decision_matches(decision: dict[str, Any], missing_item: Any) -> bool:
    target = slugify(str(decision.get("item") or ""))
    candidate = slugify(str(missing_item))
    return bool(target and candidate and (target == candidate or target in candidate or candidate in target))


def _protected_marker_in_value(value: Any) -> str | None:
    strings: list[str] = []
    if isinstance(value, dict):
        for item in value.values():
            marker = _protected_marker_in_value(item)
            if marker:
                return marker
    elif isinstance(value, list):
        for item in value:
            marker = _protected_marker_in_value(item)
            if marker:
                return marker
    elif isinstance(value, str):
        strings.append(value)
    for text_value in strings:
        lowered = text_value.lower()
        for marker in sorted(PROTECTED_OUTPUT_MARKERS):
            if marker in lowered:
                return marker
    return None


def load_approval_file(path: str | Path) -> dict[str, Any]:
    """Load a YAML or JSON approval file."""
    approval_path = Path(path)
    text_value = approval_path.read_text(encoding="utf-8")
    if approval_path.suffix.lower() == ".json":
        loaded = json.loads(text_value)
    else:
        loaded = yaml.safe_load(text_value) or {}
    if not isinstance(loaded, dict):
        raise ValueError("Approval file must contain an object at the top level.")
    return normalize_approval(loaded)


def validate_approval_file(approval: dict[str, Any]) -> dict[str, Any]:
    """Validate an approval payload."""
    normalized = normalize_approval(approval)
    errors = validate_approval_shape(normalized)
    return {"is_valid": not errors, "errors": errors}


def _required_adjusted_files(adjusted_packet_path: Path) -> list[str]:
    required = ["adjusted_recipe.json", "adjusted_webmap.json", "applied_adjustments.json", "adjusted_warnings.json"]
    return [file_name for file_name in required if not (adjusted_packet_path / file_name).exists()]


def create_approval_template(adjusted_packet_folder: str | Path) -> Path:
    """Create a YAML approval template without mutating the adjusted packet."""
    adjusted_path = Path(adjusted_packet_folder)
    if not (adjusted_path / "adjusted_webmap.json").exists():
        raise ValueError("Only adjusted packets can receive approval templates.")
    adjusted_recipe = _load_json(adjusted_path / "adjusted_recipe.json")
    adjusted_warnings = _load_json(adjusted_path / "adjusted_warnings.json")
    warning_items = _active_warning_items(adjusted_warnings)
    missing_items = adjusted_recipe.get("missing_data_needed") or []
    template = {
        "reviewer_name": "Reviewer Name",
        "reviewer_role": "GIS Reviewer",
        "decision": "approved",
        "publish_ready_requested": True,
        "reviewer_notes": [
            "Reviewed selected layers, filters, warnings, missing data, and local preview map."
        ],
        "warning_resolutions": [
            {
                "warning_id": item["warning_id"],
                "action": "accepted",
                "note": f"Reviewed locally: {item['warning']}",
            }
            for item in warning_items
        ],
        "accepted_risks": [
            "This is local approval for draft publishing readiness only; it is not official map approval."
        ],
        "missing_data_decisions": [
            {
                "item": str(item),
                "action": "accepted",
                "note": "Reviewer accepted this missing-data limitation for the local draft.",
            }
            for item in missing_items
        ],
    }
    root = Path("outputs/approval_templates")
    root.mkdir(parents=True, exist_ok=True)
    template_path = root / f"{adjusted_path.name}_approval.template.yaml"
    template_path.write_text(yaml.safe_dump(template, sort_keys=False), encoding="utf-8")
    return template_path


def evaluate_publish_readiness(
    adjusted_recipe: dict[str, Any],
    adjusted_warnings: dict[str, Any],
    approval: dict[str, Any],
    required_files_missing: list[str] | None = None,
) -> dict[str, Any]:
    """Evaluate whether reviewer approval can mark a packet publish-ready."""
    normalized = normalize_approval(approval)
    block_reasons: list[str] = []
    resolved_warnings: list[dict[str, Any]] = []
    accepted_warnings: list[dict[str, Any]] = []
    kept_warnings: list[dict[str, Any]] = []

    if normalized["decision"] != "approved":
        block_reasons.append("Reviewer decision is not approved.")
    if not normalized["publish_ready_requested"]:
        block_reasons.append("publish_ready_requested is false.")
    for file_name in required_files_missing or []:
        block_reasons.append(f"Required adjusted packet file is missing: {file_name}")

    warning_items = _active_warning_items(adjusted_warnings)
    for item in warning_items:
        resolution = next(
            (
                candidate
                for candidate in normalized.get("warning_resolutions") or []
                if isinstance(candidate, dict) and _resolution_matches(candidate, item)
            ),
            None,
        )
        if not resolution:
            block_reasons.append(f"Unresolved warning requires reviewer decision: {item['warning_id']}")
            continue
        action = str(resolution.get("action") or "").strip().lower()
        resolved_item = {**item, "action": action, "note": str(resolution.get("note") or "")}
        if action == "resolved":
            resolved_warnings.append(resolved_item)
        elif action == "accepted":
            accepted_warnings.append(resolved_item)
        elif action == "keep":
            if not str(resolution.get("note") or "").strip():
                block_reasons.append(f"Kept warning requires reviewer note: {item['warning_id']}")
            kept_warnings.append(resolved_item)
        else:
            block_reasons.append(f"Unsupported warning action for {item['warning_id']}: {action}")

    missing_data = adjusted_recipe.get("missing_data_needed") or []
    missing_data_decisions = [
        item
        for item in normalized.get("missing_data_decisions") or []
        if isinstance(item, dict)
    ]
    for missing_item in missing_data:
        if not any(_missing_decision_matches(decision, missing_item) for decision in missing_data_decisions):
            block_reasons.append(f"Missing data requires reviewer decision: {missing_item}")

    final_publish_ready = not block_reasons
    return {
        "final_publish_ready": final_publish_ready,
        "block_reasons": _dedupe(block_reasons),
        "resolved_warnings": resolved_warnings,
        "accepted_warnings": accepted_warnings,
        "kept_non_blocking_warnings": kept_warnings,
        "accepted_risks": [str(item) for item in normalized.get("accepted_risks") or []],
        "missing_data_decisions": missing_data_decisions,
        "reviewer_notes": [str(item) for item in normalized.get("reviewer_notes") or []],
    }


def _approval_receipt(
    source_adjusted_packet: Path,
    approval: dict[str, Any],
    readiness: dict[str, Any],
) -> dict[str, Any]:
    normalized = normalize_approval(approval)
    return {
        "reviewer_name": normalized.get("reviewer_name"),
        "reviewer_role": normalized.get("reviewer_role"),
        "decision": normalized.get("decision"),
        "publish_ready_requested": normalized.get("publish_ready_requested"),
        "final_publish_ready": readiness["final_publish_ready"],
        "approved_at": datetime.now(UTC).isoformat(),
        "source_adjusted_packet": str(source_adjusted_packet),
        "block_reasons": readiness["block_reasons"],
        "resolved_warnings": readiness["resolved_warnings"],
        "accepted_warnings": readiness["accepted_warnings"],
        "kept_non_blocking_warnings": readiness["kept_non_blocking_warnings"],
        "accepted_risks": readiness["accepted_risks"],
        "missing_data_decisions": readiness["missing_data_decisions"],
        "reviewer_notes": readiness["reviewer_notes"],
        "local_approval_only": True,
        "no_arcgis_item_created": True,
        "cfs_database_not_touched": True,
    }


def _approved_warnings(adjusted_warnings: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    return {
        "active": {} if readiness["final_publish_ready"] else adjusted_warnings.get("active", {}),
        "resolved_warnings": readiness["resolved_warnings"],
        "accepted_warnings": readiness["accepted_warnings"],
        "kept_non_blocking_warnings": readiness["kept_non_blocking_warnings"],
        "block_reasons": readiness["block_reasons"],
        "final_publish_ready": readiness["final_publish_ready"],
    }


def _approval_summary(approved_recipe: dict[str, Any], approved_webmap: dict[str, Any], receipt: dict[str, Any]) -> str:
    lines = [
        f"# {approved_recipe.get('map_title') or approved_webmap.get('title') or 'Approved AutoMap Draft'}",
        "",
        "This is a locally approved AutoMap draft packet. It is not an official map.",
        "",
        f"Reviewer: {receipt.get('reviewer_name') or ''}",
        f"Reviewer role: {receipt.get('reviewer_role') or ''}",
        f"Decision: {receipt.get('decision')}",
        f"Final publish ready: {receipt.get('final_publish_ready')}",
        "",
        "## Block Reasons",
        "",
    ]
    block_reasons = receipt.get("block_reasons") or []
    if block_reasons:
        lines.extend(f"- {reason}" for reason in block_reasons)
    else:
        lines.append("No block reasons remain.")
    lines.extend(["", "## Reviewer Notes", ""])
    notes = receipt.get("reviewer_notes") or []
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("No reviewer notes.")
    lines.extend(["", "## Local Approval Boundary", "", "- No ArcGIS item was created.", "- Protected external database was not touched."])
    return "\n".join(lines).strip() + "\n"


def _approval_html(approved_recipe: dict[str, Any], receipt: dict[str, Any], layer_review: list[dict[str, Any]]) -> str:
    title = approved_recipe.get("map_title") or "Approved AutoMap Draft"
    layer_rows = "".join(
        "<tr>"
        f"<td>{escape(str(row.get('title') or ''))}</td>"
        f"<td>{escape(str(row.get('role') or ''))}</td>"
        f"<td>{escape(str(row.get('source_status') or ''))}</td>"
        f"<td>{escape(str(row.get('layer_url') or ''))}</td>"
        "</tr>"
        for row in layer_review
    )
    block_items = "".join(f"<li>{escape(str(reason))}</li>" for reason in receipt.get("block_reasons") or [])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(str(title))} - AutoMap Approval</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #f7f8fa; color: #17202a; line-height: 1.5; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    header, section {{ background: #fff; border: 1px solid #d8dde6; border-radius: 8px; padding: 18px; margin-bottom: 16px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th, td {{ border-bottom: 1px solid #d8dde6; padding: 8px; text-align: left; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(str(title))}</h1>
      <p><strong>Decision:</strong> {escape(str(receipt.get('decision')))}</p>
      <p><strong>Final publish ready:</strong> {escape(str(receipt.get('final_publish_ready')))}</p>
      <p>This is local approval only. No ArcGIS item was created.</p>
    </header>
    <section>
      <h2>Block Reasons</h2>
      {"<ul>" + block_items + "</ul>" if block_items else "<p>No block reasons remain.</p>"}
    </section>
    <section>
      <h2>Layers</h2>
      <table>
        <thead><tr><th>Layer</th><th>Role</th><th>Source</th><th>URL</th></tr></thead>
        <tbody>{layer_rows or '<tr><td colspan="4">No layers found.</td></tr>'}</tbody>
      </table>
    </section>
  </main>
</body>
</html>
"""


def write_approved_packet(original_adjusted_packet_folder: str | Path, approval_result: dict[str, Any]) -> Path:
    """Write an approved packet without mutating the adjusted packet."""
    adjusted_path = Path(original_adjusted_packet_folder)
    root = Path("outputs/review_packets_approved")
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
    approved_path = root / f"{adjusted_path.name}_approved_{timestamp}"
    approved_path.mkdir(parents=True, exist_ok=False)

    approved_recipe = approval_result["approved_recipe"]
    approved_webmap = approval_result["approved_webmap"]
    receipt = approval_result["approval_receipt"]
    approved_warnings = approval_result["approved_warnings"]
    approval_file = approval_result["approval_file"]
    layer_review = build_layer_review_table(approved_recipe, approved_webmap)
    summary = _approval_summary(approved_recipe, approved_webmap, receipt)
    html = _approval_html(approved_recipe, receipt, layer_review)

    _write_json(approved_path / "approved_recipe.json", approved_recipe)
    _write_json(approved_path / "approved_webmap.json", approved_webmap)
    _write_json(approved_path / "approval_file.json", approval_file)
    _write_json(approved_path / "approval_receipt.json", receipt)
    _write_json(approved_path / "approved_warnings.json", approved_warnings)
    _write_json(approved_path / "approved_layer_review.json", layer_review)
    (approved_path / "approved_review_summary.md").write_text(summary, encoding="utf-8")
    (approved_path / "approved_review.html").write_text(html, encoding="utf-8")
    return approved_path


def apply_approval_to_adjusted_packet(adjusted_packet_folder: str | Path, approval_file: str | Path) -> Path:
    """Apply reviewer approval to an adjusted packet and create a separate approved packet."""
    adjusted_path = Path(adjusted_packet_folder)
    if not (adjusted_path / "adjusted_webmap.json").exists():
        raise ValueError("Only adjusted packets can be approved.")
    approval = load_approval_file(approval_file)
    validation = validate_approval_file(approval)
    if not validation["is_valid"]:
        raise ValueError("; ".join(validation["errors"]))

    adjusted_recipe = _load_json(adjusted_path / "adjusted_recipe.json")
    adjusted_webmap = _load_json(adjusted_path / "adjusted_webmap.json")
    adjusted_warnings = _load_json(adjusted_path / "adjusted_warnings.json")
    missing_files = _required_adjusted_files(adjusted_path)
    readiness = evaluate_publish_readiness(adjusted_recipe, adjusted_warnings, approval, missing_files)
    receipt = _approval_receipt(adjusted_path, approval, readiness)

    approved_recipe = deepcopy(adjusted_recipe)
    approved_webmap = deepcopy(adjusted_webmap)
    approved_recipe["reviewer_approval"] = {
        "decision": approval["decision"],
        "final_publish_ready": readiness["final_publish_ready"],
        "approved_at": receipt["approved_at"],
        "local_approval_only": True,
    }
    approved_webmap["autoMapApproval"] = {
        "decision": approval["decision"],
        "finalPublishReady": readiness["final_publish_ready"],
        "approvedAt": receipt["approved_at"],
        "localApprovalOnly": True,
    }
    approved_webmap["autoMapPublicationStatus"] = (
        "reviewer_approved_local_draft"
        if readiness["final_publish_ready"]
        else "reviewer_approval_blocked"
    )

    approval_result = {
        "approved_recipe": approved_recipe,
        "approved_webmap": approved_webmap,
        "approval_file": approval,
        "approval_receipt": receipt,
        "approved_warnings": _approved_warnings(adjusted_warnings, readiness),
    }
    approved_path = write_approved_packet(adjusted_path, approval_result)
    try:
        record_approval_history(receipt, approved_path)
    except Exception:
        # Packet creation is the primary local artifact; history can be retried.
        pass
    return approved_path


def _packet_text(packet_path: Path) -> str:
    chunks: list[str] = []
    for file_name in APPROVED_PACKET_FILES:
        path = packet_path / file_name
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8"))
    return "\n".join(chunks).lower()


def validate_approved_packet(approved_packet_folder: str | Path) -> dict[str, Any]:
    """Validate a generated approved packet."""
    packet_path = Path(approved_packet_folder)
    errors: list[str] = []
    warnings: list[str] = []
    if not packet_path.exists() or not packet_path.is_dir():
        return {
            "is_valid": False,
            "errors": [f"Approved packet folder not found: {packet_path}"],
            "warnings": [],
            "packet_path": str(packet_path),
        }
    missing_files = sorted(file_name for file_name in APPROVED_PACKET_FILES if not (packet_path / file_name).exists())
    if missing_files:
        errors.append(f"Missing required approved packet files: {', '.join(missing_files)}")

    receipt: dict[str, Any] = {}
    approved_webmap: dict[str, Any] = {}
    if not missing_files:
        try:
            _load_json(packet_path / "approved_recipe.json")
            approved_webmap = _load_json(packet_path / "approved_webmap.json")
            _load_json(packet_path / "approval_file.json")
            receipt = _load_json(packet_path / "approval_receipt.json")
            _load_json(packet_path / "approved_warnings.json")
            _load_json(packet_path / "approved_layer_review.json")
        except json.JSONDecodeError as exc:
            errors.append(f"Approved packet JSON is invalid: {exc}")

    if approved_webmap and not approved_webmap.get("operationalLayers"):
        warnings.append("approved_webmap.json has no operationalLayers.")
    for index, layer in enumerate(approved_webmap.get("operationalLayers") or []):
        if not layer.get("url"):
            errors.append(f"Operational layer {layer.get('title') or index} is missing URL.")

    if receipt and receipt.get("final_publish_ready") is True and receipt.get("block_reasons"):
        errors.append("approval_receipt final_publish_ready cannot be true while block_reasons remain.")

    marker = _protected_marker_in_value(
        {
            "approved_recipe": _load_json(packet_path / "approved_recipe.json") if (packet_path / "approved_recipe.json").exists() else {},
            "approved_webmap": approved_webmap,
            "approved_warnings": _load_json(packet_path / "approved_warnings.json") if (packet_path / "approved_warnings.json").exists() else {},
            "approval_receipt": receipt,
        }
    )
    if marker:
        errors.append(f"Approved packet contains protected or secret marker: {marker}")

    return {
        "is_valid": not errors,
        "errors": _dedupe(errors),
        "warnings": _dedupe(warnings),
        "packet_path": str(packet_path),
        "required_files_present": not missing_files,
        "final_publish_ready": receipt.get("final_publish_ready"),
        "block_reasons": receipt.get("block_reasons") or [],
        "operational_layer_count": len(approved_webmap.get("operationalLayers") or []),
    }
