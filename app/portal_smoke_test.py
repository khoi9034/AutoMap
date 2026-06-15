"""Guarded one-item Portal publish smoke test for AutoMap."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.arcgis_publisher import (
    _credential_missing_or_placeholder,
    _dedupe,
    _load_packet_payload,
    _packet_type,
    connect_to_arcgis,
    load_arcgis_publish_settings,
    publish_webmap_draft,
    validate_publish_packet,
)
from app.portal_item_verifier import build_verification_receipt, verify_portal_item


SMOKE_RECEIPT_NAME = "smoke_test_receipt.json"
MANUAL_CLEANUP_NOTE = (
    "Manual cleanup required: inspect the private draft Web Map item in Portal "
    "and delete it manually when smoke testing is complete."
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, default=str), encoding="utf-8")


def _base_result(approved_packet_folder: str | Path, *, dry_run: bool) -> dict[str, Any]:
    started_at = datetime.now(UTC).isoformat()
    return {
        "smoke_test_started_at": started_at,
        "smoke_test_completed_at": None,
        "dry_run": dry_run,
        "real_publish_attempted": False,
        "blocked": False,
        "block_reasons": [],
        "item_created": False,
        "item_id": None,
        "item_url": None,
        "portal_url": None,
        "target_folder": None,
        "item_title": None,
        "verified_private": False,
        "verified_not_public": False,
        "verified_not_org_shared": False,
        "verified_webmap_type": False,
        "verified_layer_urls": False,
        "verification_errors": [],
        "manual_cleanup_note": MANUAL_CLEANUP_NOTE,
        "cfs_untouched_statement": "Protected external database was not touched.",
        "approved_packet_path": str(approved_packet_folder),
    }


def _complete(result: dict[str, Any]) -> dict[str, Any]:
    result["smoke_test_completed_at"] = datetime.now(UTC).isoformat()
    return result


def validate_smoke_test_prerequisites(approved_packet_folder: str | Path) -> dict[str, Any]:
    """Validate local packet prerequisites without connecting to ArcGIS."""
    packet_path = Path(approved_packet_folder)
    validation = validate_publish_packet(packet_path, require_approved=True)
    errors = [str(error) for error in validation.get("errors") or []]
    if not packet_path.exists() or not packet_path.is_dir():
        errors.append(f"Approved packet folder not found: {packet_path}")
    elif _packet_type(packet_path) != "approved":
        errors.append("Portal smoke test requires an approved packet folder.")
    return {
        "is_valid": not errors,
        "errors": _dedupe(errors),
        "validation": validation,
        "packet_path": str(packet_path),
    }


def _env_block_reasons(confirm_publish: bool) -> tuple[list[str], Any | None]:
    try:
        settings = load_arcgis_publish_settings()
    except ValueError as exc:
        return [str(exc)], None
    reasons: list[str] = []
    if not confirm_publish:
        reasons.append("Portal smoke test real publish requires --confirm-publish.")
    if not settings.allow_real_publish:
        reasons.append("AUTOMAP_ALLOW_REAL_PUBLISH must be true for portal smoke testing.")
    if settings.dry_run:
        reasons.append("AUTOMAP_PUBLISH_DRY_RUN must be false for portal smoke testing.")
    if not settings.portal_url:
        reasons.append("ARCGIS_PORTAL_URL must be configured.")
    if _credential_missing_or_placeholder(settings.username):
        reasons.append("ARCGIS_USERNAME must be configured.")
    if _credential_missing_or_placeholder(settings.password):
        reasons.append("ARCGIS_PASSWORD must be configured.")
    if not settings.target_folder or not settings.target_folder.strip():
        reasons.append("ARCGIS_TARGET_FOLDER must be configured.")
    return _dedupe(reasons), settings


def publish_one_private_draft_item(approved_packet_folder: str | Path) -> dict[str, Any]:
    """Publish exactly one private draft item via the guarded publisher."""
    return publish_webmap_draft(approved_packet_folder, dry_run=False, confirm_publish=True)


def verify_smoke_test_item(item_id: str, approved_packet_folder: str | Path) -> dict[str, Any]:
    """Verify the smoke-test-created item."""
    return verify_portal_item(item_id, approved_packet_folder)


def write_smoke_test_receipt(approved_packet_folder: str | Path, result: dict[str, Any]) -> Path:
    """Write smoke_test_receipt.json inside the approved packet folder."""
    packet_path = Path(approved_packet_folder)
    receipt_path = packet_path / SMOKE_RECEIPT_NAME
    safe_result = dict(result)
    safe_result.pop("password", None)
    safe_result.pop("token", None)
    safe_result.pop("credentials", None)
    _write_json(receipt_path, safe_result)
    return receipt_path


def _blocked_result(
    approved_packet_folder: str | Path,
    *,
    dry_run: bool,
    reasons: list[str],
    settings: Any | None = None,
) -> dict[str, Any]:
    result = _base_result(approved_packet_folder, dry_run=dry_run)
    result.update(
        {
            "blocked": True,
            "block_reasons": _dedupe(reasons),
            "portal_url": getattr(settings, "portal_url", None),
            "target_folder": getattr(settings, "target_folder", None),
        }
    )
    return _complete(result)


def run_publish_smoke_test(
    approved_packet_folder: str | Path,
    confirm_publish: bool = False,
) -> dict[str, Any]:
    """Run a dry-run or real one-item portal publish smoke test."""
    packet_path = Path(approved_packet_folder)
    dry_run = not confirm_publish
    result = _base_result(packet_path, dry_run=dry_run)
    prerequisites = validate_smoke_test_prerequisites(packet_path)
    settings = None
    settings_reasons: list[str] = []
    try:
        settings = load_arcgis_publish_settings()
    except ValueError as exc:
        settings_reasons.append(str(exc))

    result["portal_url"] = getattr(settings, "portal_url", None)
    result["target_folder"] = getattr(settings, "target_folder", None)
    if prerequisites["errors"]:
        blocked = _blocked_result(
            packet_path,
            dry_run=dry_run,
            reasons=[*prerequisites["errors"], *settings_reasons],
            settings=settings,
        )
        if packet_path.exists() and packet_path.is_dir():
            write_smoke_test_receipt(packet_path, blocked)
        return blocked

    payload = _load_packet_payload(packet_path, "approved")
    result["item_title"] = (
        payload.get("recipe", {}).get("map_title")
        or payload.get("webmap", {}).get("title")
        or "AutoMap Draft"
    )

    if dry_run:
        dry_result = publish_webmap_draft(packet_path, dry_run=True, confirm_publish=False)
        result.update(
            {
                "blocked": dry_result.get("status") == "blocked",
                "block_reasons": dry_result.get("block_reasons") or dry_result.get("validation", {}).get("errors") or [],
                "item_created": False,
                "item_id": None,
                "item_url": None,
                "real_publish_attempted": False,
                "item_title": dry_result.get("item_title") or dry_result.get("title") or result["item_title"],
            }
        )
        completed = _complete(result)
        write_smoke_test_receipt(packet_path, completed)
        return completed

    env_reasons, settings = _env_block_reasons(confirm_publish)
    result["portal_url"] = getattr(settings, "portal_url", None)
    result["target_folder"] = getattr(settings, "target_folder", None)
    if env_reasons:
        blocked = _blocked_result(packet_path, dry_run=False, reasons=env_reasons, settings=settings)
        write_smoke_test_receipt(packet_path, blocked)
        return blocked

    publish_result = publish_one_private_draft_item(packet_path)
    result.update(
        {
            "real_publish_attempted": bool(publish_result.get("real_publish_attempted")),
            "blocked": publish_result.get("status") == "blocked",
            "block_reasons": publish_result.get("block_reasons") or [],
            "item_created": bool(publish_result.get("created_item")),
            "item_id": publish_result.get("item_id"),
            "item_url": publish_result.get("item_url"),
            "portal_url": publish_result.get("portal_url"),
            "target_folder": publish_result.get("target_folder"),
            "item_title": publish_result.get("item_title") or publish_result.get("title"),
        }
    )

    if result["item_created"] and result["item_id"]:
        try:
            gis = connect_to_arcgis(settings)
            item = gis.content.get(result["item_id"])
            verification = build_verification_receipt(item, packet_path)
        except Exception as exc:
            verification = {
                "verified_private": False,
                "verified_not_public": False,
                "verified_not_org_shared": False,
                "verified_webmap_type": False,
                "verified_layer_urls": False,
                "verification_errors": [str(exc)],
            }
        result.update(
            {
                "verified_private": bool(verification.get("verified_private")),
                "verified_not_public": bool(verification.get("verified_not_public")),
                "verified_not_org_shared": bool(verification.get("verified_not_org_shared")),
                "verified_webmap_type": bool(verification.get("verified_webmap_type")),
                "verified_layer_urls": bool(verification.get("verified_layer_urls")),
                "verification_errors": verification.get("verification_errors") or [],
            }
        )

    completed = _complete(result)
    write_smoke_test_receipt(packet_path, completed)
    return completed
