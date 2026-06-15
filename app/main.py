"""Command-line entry point for AutoMap."""

import argparse
from datetime import UTC, datetime
import json
import os
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.adjustment_engine import (
    apply_adjustments_to_review_packet,
    create_adjustment_template,
    validate_adjusted_packet,
)
from app.analysis_executor import build_analysis_plan, execute_analysis, list_runs as list_analysis_runs
from app.analysis_result_store import validate_analysis_run
from app.approval_engine import (
    apply_approval_to_adjusted_packet,
    create_approval_template,
    list_approval_history,
    validate_approved_packet,
)
from app.arcgis_publisher import (
    check_arcgis_connection,
    publish_webmap_draft,
)
from app.catalog_builder import build_catalog_records, inspect_services
from app.config import get_settings
from app.data_gap_registry import list_data_gaps
from app.db import test_db_connection
from app.demo_workflow import run_demo_workflow
from app.feedback_learning import learn_from_approved_packet
from app.field_profiler import (
    log_recipe_validation,
    profile_catalog_fields,
    profile_layer_fields,
)
from app.filter_planner import validate_filter_plan
from app.layer_catalog_store import (
    export_layer_catalog_json,
    load_catalog_records,
    list_layers,
    search_layers,
    upsert_layer_records,
    verify_catalog_layers,
)
from app.layer_semantics import slugify
from app.packet_index import (
    build_preview_config,
    find_latest_packet,
    list_adjusted_packets,
    list_approved_packets,
    list_review_packets,
)
from app.ports import AUTOMAP_BACKEND_PORT, CFS_RESERVED_WARNING
from app.portal_item_verifier import verify_portal_item
from app.portal_smoke_test import run_publish_smoke_test
from app.pattern_library import list_clarification_defaults, list_patterns
from app.recipe_engine import build_recipe
from app.report_generator import generate_report, list_reports, validate_report
from app.review_packet_builder import (
    build_review_packet,
    save_review_packet,
    validate_review_packet,
)
from app.rest_sources import load_rest_sources
from app.system_status import format_system_status, get_system_status
from app.version import AUTOMAP_VERSION
from app.webmap_builder import validate_webmap_json
from app.webmap_exporter import export_recipe_and_webmap


def _print_project_banner() -> None:
    print("AutoMap: County GIS Request Engine")
    print(f"version {AUTOMAP_VERSION}")


def _check_db() -> int:
    settings = get_settings()
    if not settings.DATABASE_URL:
        print(
            "DATABASE_URL is not configured. Copy .env.example to .env and set "
            "AutoMap's own PostGIS connection string."
        )
        return 0

    try:
        result = test_db_connection(settings)
    except ValueError as exc:
        print(f"Database configuration error: {exc}")
        return 1
    except SQLAlchemyError as exc:
        print(f"Database connection failed: {exc}")
        return 1

    print(f"database connected: {result['database_connected']}")
    print(f"database name: {result['database_name']}")
    print(f"PostGIS version: {result['postgis_version']}")
    print(f"AutoMap schema: {result['automap_schema']}")
    return 0


def _inspect_rest_sources() -> int:
    sources = load_rest_sources()
    result = inspect_services(sources)
    print("ArcGIS REST sources inspected")
    for service in result["services"]:
        print(
            f"{service['source_key']} | {service['service_name']} | "
            f"layers={service['layer_count']} | tables={service['table_count']} | "
            f"{service['service_url']}"
        )
    if result["failures"]:
        print("Failures:")
        for failure in result["failures"]:
            print(f"{failure['source_key']} | {failure['url']} | {failure['error']}")
    print(f"services discovered: {len(result['services'])}")
    print(f"layers discovered: {sum(service['layer_count'] for service in result['services'])}")
    return 0


def _build_catalog_from_rest() -> int:
    sources = load_rest_sources()
    result = build_catalog_records(sources)
    upserted = upsert_layer_records(result["records"])
    print("ArcGIS REST catalog build complete")
    print(f"records upserted: {upserted}")
    print(f"verified layers: {result['verified_count']}")
    for source_key, count in result["service_count_by_source"].items():
        print(f"{source_key} services discovered: {count}")
    for source_key, count in result["layer_count_by_source"].items():
        print(f"{source_key} layers discovered: {count}")
    if result["failures"]:
        print("Failures:")
        for failure in result["failures"]:
            print(f"{failure['source_key']} | {failure['url']} | {failure['error']}")
    return 0


def _verify_layer_catalog() -> int:
    result = verify_catalog_layers()
    print("Layer catalog verification complete")
    print(f"layers checked: {result['checked']}")
    print(f"verified layers: {result['verified']}")
    if result["failed"]:
        print("Failed layer URLs:")
        for failure in result["failed"]:
            print(f"{failure['layer_key']} | {failure['layer_url']} | {failure['error']}")
    return 0


def _list_layers() -> int:
    rows = list_layers()
    for row in rows:
        print(
            f"{row['layer_key']} | {row['layer_name']} | {row['category']} | "
            f"{row['source_status']} | priority={row['source_priority']} | "
            f"verified={row['is_verified']} | {row['layer_url']}"
        )
    print(f"layers listed: {len(rows)}")
    return 0


def _search_layers(query: str) -> int:
    rows = search_layers(query)
    for row in rows:
        print(
            f"{row['layer_key']} | {row['layer_name']} | {row['category']} | "
            f"{row['source_status']} | priority={row['source_priority']} | "
            f"verified={row['is_verified']} | count={row['record_count']} | "
            f"{row['layer_url']}"
        )
    print(f"matches: {len(rows)}")
    return 0


def _export_layer_catalog_json() -> int:
    export_path = export_layer_catalog_json()
    print(f"layer catalog exported: {export_path}")
    return 0


def _make_recipe(prompt: str, save_recipe: bool = False) -> int:
    recipe = build_recipe(prompt)
    print(json.dumps(recipe, indent=2, default=str))
    if save_recipe:
        output_dir = Path("outputs/sample_recipes")
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        output_path = output_dir / f"{timestamp}_{slugify(prompt)[:80]}.json"
        output_path.write_text(json.dumps(recipe, indent=2, default=str), encoding="utf-8")
        print(f"recipe saved: {output_path}", file=sys.stderr)
    return 0


def _profile_layer_fields(layer_key: str | None) -> int:
    if not layer_key:
        print("--profile-layer-fields requires --layer-key")
        return 1
    records = load_catalog_records()
    layer_record = next((record for record in records if record.get("layer_key") == layer_key), None)
    if not layer_record:
        print(f"Layer key not found in AutoMap catalog: {layer_key}")
        return 1
    result = profile_layer_fields(layer_record)
    print(json.dumps({
        "layer_key": result["layer_key"],
        "field_profiles": len(result["field_profiles"]),
        "value_profiles": len(result["value_profiles"]),
    }, indent=2))
    return 0


def _profile_catalog_fields(category: str | None = None) -> int:
    categories = [category] if category else None
    result = profile_catalog_fields(categories=categories)
    print(json.dumps(result, indent=2))
    return 0


def _validate_recipe(prompt: str) -> int:
    recipe = build_recipe(prompt)
    validation = validate_filter_plan(recipe)
    recipe["validation"] = validation
    log_recipe_validation(recipe, validation)
    print(json.dumps(recipe, indent=2, default=str))
    return 0


def _list_data_gaps() -> int:
    gaps = list_data_gaps()
    for gap in gaps:
        print(
            f"{gap['gap_key']} | {gap['topic']} | {gap['status']} | "
            f"{gap['missing_layer_type']} | {gap['reason']}"
        )
    print(f"data gaps: {len(gaps)}")
    return 0


def _make_webmap_draft(prompt: str) -> int:
    result = export_recipe_and_webmap(prompt)
    recipe = result["recipe"]
    validation = result["validation"]
    webmap_path = result["webmap_path"]

    print(f"webmap draft saved: {webmap_path}")
    print(f"validation passed: {validation['is_valid']}")
    print(f"needs review: {recipe['needs_review']}")
    print("selected layers:")
    for layer in recipe["selected_layers"]:
        print(
            f"- {layer['layer_key']} | {layer['layer_name']} | "
            f"{layer['role']} | {layer['layer_url']}"
        )
    warnings = sorted(
        {
            *recipe.get("review_reasons", []),
            *validation.get("warnings", []),
            *validation.get("errors", []),
        }
    )
    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"- {warning}")
    return 0 if validation["is_valid"] else 1


def _validate_webmap_draft(path: str) -> int:
    webmap_path = Path(path)
    if not webmap_path.exists():
        print(f"WebMap draft not found: {webmap_path}")
        return 1
    webmap_json = json.loads(webmap_path.read_text(encoding="utf-8"))
    validation = validate_webmap_json(webmap_json)
    print(json.dumps(validation, indent=2))
    return 0 if validation["is_valid"] else 1


def _make_review_packet(prompt: str) -> int:
    packet = build_review_packet(prompt)
    packet_path = save_review_packet(prompt, packet["recipe"], packet["webmap_json"])
    validation = validate_review_packet(packet_path)
    print(f"review packet saved: {packet_path}")
    print(f"validation passed: {validation['is_valid']}")
    print("selected layers:")
    for layer in packet["recipe"]["selected_layers"]:
        print(
            f"- {layer['layer_key']} | {layer['layer_name']} | "
            f"{layer['role']} | {layer['layer_url']}"
        )
    warning_report = packet["warnings"]
    any_warnings = False
    for group_name, warnings in warning_report.items():
        if not warnings:
            continue
        any_warnings = True
        print(f"{group_name}:")
        for warning in warnings:
            print(f"- {warning}")
    if not any_warnings:
        print("warnings: none")
    if validation["errors"]:
        print("validation errors:")
        for error in validation["errors"]:
            print(f"- {error}")
    return 0 if validation["is_valid"] else 1


def _validate_review_packet(path: str) -> int:
    validation = validate_review_packet(path)
    print(json.dumps(validation, indent=2))
    return 0 if validation["is_valid"] else 1


def _create_adjustment_template(path: str) -> int:
    template_path = create_adjustment_template(path)
    print(f"adjustment template created: {template_path}")
    return 0


def _apply_adjustments(packet_folder: str, adjustment_file: str) -> int:
    adjusted_path = apply_adjustments_to_review_packet(packet_folder, adjustment_file)
    validation = validate_adjusted_packet(adjusted_path)
    print(f"adjusted packet saved: {adjusted_path}")
    print(f"validation passed: {validation['is_valid']}")
    print(f"publish ready: {validation.get('publish_ready')}")
    if validation["errors"]:
        print("validation errors:")
        for error in validation["errors"]:
            print(f"- {error}")
    return 0 if validation["is_valid"] else 1


def _validate_adjusted_packet(path: str) -> int:
    validation = validate_adjusted_packet(path)
    print(json.dumps(validation, indent=2))
    return 0 if validation["is_valid"] else 1


def _create_approval_template(path: str) -> int:
    template_path = create_approval_template(path)
    print(f"approval template created: {template_path}")
    return 0


def _apply_approval(adjusted_packet_folder: str, approval_file: str) -> int:
    approved_path = apply_approval_to_adjusted_packet(adjusted_packet_folder, approval_file)
    validation = validate_approved_packet(approved_path)
    print(f"approved packet saved: {approved_path}")
    print(f"validation passed: {validation['is_valid']}")
    print(f"final publish ready: {validation.get('final_publish_ready')}")
    if validation["errors"]:
        print("validation errors:")
        for error in validation["errors"]:
            print(f"- {error}")
    if validation.get("block_reasons"):
        print("block reasons:")
        for reason in validation["block_reasons"]:
            print(f"- {reason}")
    return 0 if validation["is_valid"] else 1


def _validate_approved_packet(path: str) -> int:
    validation = validate_approved_packet(path)
    print(json.dumps(validation, indent=2))
    return 0 if validation["is_valid"] else 1


def _list_approvals() -> int:
    rows = list_approval_history()
    for row in rows:
        print(
            f"{row['id']} | {row['decision']} | ready={row['final_publish_ready']} | "
            f"{row['reviewer_name']} | {row['approved_packet_path']}"
        )
    print(f"approval history rows: {len(rows)}")
    return 0


def _portal_check() -> int:
    result = check_arcgis_connection()
    print(json.dumps(result, indent=2))
    return 0 if result.get("connected") else 1


def _publish_draft_webmap(path: str, dry_run: bool = True, confirm_publish: bool = False) -> int:
    result = publish_webmap_draft(path, dry_run=dry_run, confirm_publish=confirm_publish)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") in {"dry_run", "published_private_draft"} else 1


def _portal_smoke_test(path: str, confirm_publish: bool = False) -> int:
    result = run_publish_smoke_test(path, confirm_publish=confirm_publish)
    print(json.dumps(result, indent=2, default=str))
    if result.get("dry_run") and not result.get("blocked") and not result.get("item_created"):
        return 0
    if result.get("item_created") and not result.get("verification_errors"):
        return 0
    return 1


def _verify_portal_item(item_id: str, approved_packet: str | None = None) -> int:
    result = verify_portal_item(item_id, approved_packet)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("verified") else 1


def _default_backend_port() -> int:
    return int(
        os.getenv(
            "AUTOMAP_BACKEND_PORT",
            os.getenv("BACKEND_PORT", os.getenv("AUTOMAP_UI_PORT", str(AUTOMAP_BACKEND_PORT))),
        )
    )


def _serve_ui(port: int | None = None) -> int:
    from app.web_ui import run_ui

    selected_port = port or _default_backend_port()
    try:
        run_ui(host="127.0.0.1", port=selected_port)
    except ValueError as exc:
        print(str(exc))
        return 1
    return 0


def _list_packets() -> int:
    review_packets = list_review_packets()
    adjusted_packets = list_adjusted_packets()
    approved_packets = list_approved_packets()
    print("review packets:")
    for packet in review_packets:
        print(f"- {packet['packet_id']} | {packet['map_title']} | {packet['preview_url']}")
    if not review_packets:
        print("- none")
    print("adjusted packets:")
    for packet in adjusted_packets:
        print(f"- {packet['packet_id']} | {packet['map_title']} | {packet['preview_url']}")
    if not adjusted_packets:
        print("- none")
    print("approved packets:")
    for packet in approved_packets:
        print(f"- {packet['packet_id']} | {packet['map_title']} | {packet['preview_url']}")
    if not approved_packets:
        print("- none")
    latest = find_latest_packet()
    if latest:
        print(f"latest: {latest['packet_id']} | {latest['preview_url']}")
    print(f"review packet count: {len(review_packets)}")
    print(f"adjusted packet count: {len(adjusted_packets)}")
    print(f"approved packet count: {len(approved_packets)}")
    return 0


def _generate_report(packet_folder: str) -> int:
    package = generate_report(packet_folder)
    print(f"report saved: {package.report_path}")
    print(f"report title: {package.report_title}")
    print(f"packet type: {package.packet_type}")
    print(f"validation passed: {bool(package.validation and package.validation.get('is_valid'))}")
    print("files:")
    for file_name, file_path in package.files.items():
        print(f"- {file_name}: {file_path}")
    return 0 if package.validation and package.validation.get("is_valid") else 1


def _list_reports() -> int:
    rows = list_reports()
    if not rows:
        print("reports: none")
        return 0
    for row in rows:
        print(
            f"{row['report_id']} | {row.get('report_title')} | "
            f"{row.get('packet_type')} | {row.get('report_path')}"
        )
    print(f"reports listed: {len(rows)}")
    return 0


def _learn_from_approved_packet(path: str) -> int:
    pattern = learn_from_approved_packet(path)
    print(f"learned pattern: {pattern['pattern_key']}")
    print(f"primary intent: {pattern.get('primary_intent')}")
    print(f"preferred layers: {len(pattern.get('preferred_layer_keys') or [])}")
    print(f"clarification defaults upserted: {pattern.get('clarification_defaults_upserted', 0)}")
    return 0


def _list_patterns() -> int:
    rows = list_patterns()
    if not rows:
        print("approved patterns: none")
        return 0
    for row in rows:
        print(
            f"{row['pattern_key']} | {row.get('primary_intent')} | "
            f"layers={len(row.get('preferred_layer_keys') or [])} | "
            f"ready={row.get('final_publish_ready')}"
        )
    print(f"patterns listed: {len(rows)}")
    return 0


def _list_clarification_defaults() -> int:
    rows = list_clarification_defaults()
    if not rows:
        print("clarification defaults: none")
        return 0
    for row in rows:
        print(
            f"{row['default_key']} | {row.get('intent')} | {row.get('topic')} | "
            f"{row.get('answer_label')} | confidence={row.get('confidence_score')}"
        )
    print(f"clarification defaults listed: {len(rows)}")
    return 0


def _validate_report(path: str) -> int:
    validation = validate_report(path)
    print(json.dumps(validation, indent=2, default=str))
    return 0 if validation["is_valid"] else 1


def _plan_analysis(prompt: str) -> int:
    plan = build_analysis_plan(prompt)
    print(json.dumps(plan, indent=2, default=str))
    return 0


def _execute_analysis(prompt: str) -> int:
    result = execute_analysis(prompt)
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "completed" else 1


def _list_analysis_runs() -> int:
    rows = list_analysis_runs()
    if not rows:
        print("analysis runs: none")
        return 0
    for row in rows:
        print(
            f"{row['analysis_run_id']} | {row.get('operation_type')} | "
            f"{row.get('status')} | output={row.get('output_count')} | "
            f"{row.get('output_geojson_path') or 'no output'}"
        )
    print(f"analysis runs listed: {len(rows)}")
    return 0


def _validate_analysis_run(path_or_id: str) -> int:
    validation = validate_analysis_run(path_or_id)
    print(json.dumps(validation, indent=2, default=str))
    return 0 if validation["is_valid"] else 1


def _preview_packet(path: str, port: int | None = None) -> int:
    try:
        config = build_preview_config(path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Preview packet error: {exc}")
        return 1
    selected_port = port or _default_backend_port()
    print(f"preview source: {config['packet_path']}")
    print(f"preview URL: http://127.0.0.1:{selected_port}/preview?path={config['packet_path']}")
    print("Start the local UI first if it is not already running:")
    print(f"python -m app.main --serve-ui --ui-port {selected_port}")
    return 0


def _system_status() -> int:
    status = get_system_status()
    print(format_system_status(status))
    return 0 if status.get("database_connected") else 1


def _run_demo_workflow(ui_port: int | None = None) -> int:
    selected_port = ui_port or _default_backend_port()
    result = run_demo_workflow(ui_port=selected_port)
    print(json.dumps(result, indent=2, default=str))
    publish_result = result.get("publish_result") or {}
    no_real_publish = (
        publish_result.get("created_item") is False
        and publish_result.get("published") is False
        and result.get("real_publish_attempted") is False
    )
    return 0 if no_real_publish else 1


def main() -> int:
    """Run the AutoMap command-line interface."""
    parser = argparse.ArgumentParser(description="AutoMap command-line tools")
    parser.add_argument(
        "--check-db",
        action="store_true",
        help="Check AutoMap's own PostGIS database connection.",
    )
    parser.add_argument(
        "--inspect-rest-sources",
        action="store_true",
        help="Inspect configured ArcGIS REST services without writing to the database.",
    )
    parser.add_argument(
        "--build-catalog-from-rest",
        action="store_true",
        help="Build or update the AutoMap layer catalog from ArcGIS REST metadata.",
    )
    parser.add_argument(
        "--verify-layer-catalog",
        action="store_true",
        help="Re-check every stored layer URL in the AutoMap layer catalog.",
    )
    parser.add_argument(
        "--list-layers",
        action="store_true",
        help="List layers stored in the AutoMap layer catalog.",
    )
    parser.add_argument(
        "--search-layers",
        metavar="QUERY",
        help="Search the AutoMap layer catalog.",
    )
    parser.add_argument(
        "--export-layer-catalog-json",
        action="store_true",
        help="Export the AutoMap layer catalog to outputs/layer_catalog_export.json.",
    )
    parser.add_argument(
        "--make-recipe",
        metavar="PROMPT",
        help="Create a map recipe from a plain-English GIS request.",
    )
    parser.add_argument(
        "--save-recipe",
        action="store_true",
        help="Save --make-recipe JSON to outputs/sample_recipes/.",
    )
    parser.add_argument(
        "--profile-layer-fields",
        action="store_true",
        help="Profile fields and small value samples for one catalog layer.",
    )
    parser.add_argument(
        "--layer-key",
        help="Layer key to use with --profile-layer-fields.",
    )
    parser.add_argument(
        "--profile-catalog-fields",
        action="store_true",
        help="Profile fields for active verified catalog layers.",
    )
    parser.add_argument(
        "--category",
        help="Optional category filter for --profile-catalog-fields.",
    )
    parser.add_argument(
        "--validate-recipe",
        metavar="PROMPT",
        help="Create, validate, and log a recipe with filter intelligence.",
    )
    parser.add_argument(
        "--list-data-gaps",
        action="store_true",
        help="List missing-data topics recorded from recipe runs.",
    )
    parser.add_argument(
        "--make-webmap-draft",
        metavar="PROMPT",
        help="Create and save local-only ArcGIS WebMap draft JSON from a GIS request.",
    )
    parser.add_argument(
        "--validate-webmap-draft",
        metavar="PATH",
        help="Validate a generated AutoMap WebMap draft JSON file.",
    )
    parser.add_argument(
        "--make-review-packet",
        metavar="PROMPT",
        help="Create a local human-review packet for a draft map request.",
    )
    parser.add_argument(
        "--validate-review-packet",
        metavar="PATH",
        help="Validate a generated AutoMap review packet folder.",
    )
    parser.add_argument(
        "--create-adjustment-template",
        metavar="REVIEW_PACKET_FOLDER",
        help="Create a YAML adjustment template for a review packet.",
    )
    parser.add_argument(
        "--apply-adjustments",
        nargs=2,
        metavar=("REVIEW_PACKET_FOLDER", "ADJUSTMENT_FILE"),
        help="Apply a YAML or JSON adjustment file to a review packet.",
    )
    parser.add_argument(
        "--validate-adjusted-packet",
        metavar="PATH",
        help="Validate a generated adjusted review packet folder.",
    )
    parser.add_argument(
        "--create-approval-template",
        metavar="ADJUSTED_PACKET_FOLDER",
        help="Create a YAML approval template for an adjusted packet.",
    )
    parser.add_argument(
        "--apply-approval",
        nargs=2,
        metavar=("ADJUSTED_PACKET_FOLDER", "APPROVAL_FILE"),
        help="Apply a YAML or JSON approval file to an adjusted packet.",
    )
    parser.add_argument(
        "--validate-approved-packet",
        metavar="PATH",
        help="Validate a generated approved review packet folder.",
    )
    parser.add_argument(
        "--list-approvals",
        action="store_true",
        help="List local reviewer approval history.",
    )
    parser.add_argument(
        "--portal-check",
        action="store_true",
        help="Check ArcGIS portal credentials without publishing.",
    )
    parser.add_argument(
        "--publish-draft-webmap",
        metavar="APPROVED_PACKET_FOLDER",
        help="Dry-run or publish an approved AutoMap packet as a private draft Web Map.",
    )
    parser.add_argument(
        "--portal-smoke-test",
        metavar="APPROVED_PACKET_FOLDER",
        help="Run the guarded one-item Portal publish smoke test for an approved packet.",
    )
    parser.add_argument(
        "--verify-portal-item",
        metavar="ITEM_ID",
        help="Verify a Portal Web Map item against AutoMap private draft rules.",
    )
    parser.add_argument(
        "--approved-packet",
        metavar="APPROVED_PACKET_FOLDER",
        help="Approved packet folder used with --verify-portal-item.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Force publisher dry-run mode. This is the default.",
    )
    parser.add_argument(
        "--confirm-publish",
        action="store_true",
        help="Explicitly allow real private ArcGIS draft publishing.",
    )
    parser.add_argument(
        "--serve-ui",
        action="store_true",
        help="Start the local AutoMap backend/API at http://127.0.0.1:8010.",
    )
    parser.add_argument(
        "--ui-port",
        type=int,
        help=f"Optional local backend/API port override. Defaults to {AUTOMAP_BACKEND_PORT}. {CFS_RESERVED_WARNING}",
    )
    parser.add_argument(
        "--list-packets",
        action="store_true",
        help="List local review and adjusted packets with preview URLs.",
    )
    parser.add_argument(
        "--generate-report",
        metavar="PACKET_FOLDER",
        help="Generate a local report/export package from a review, adjusted, or approved packet.",
    )
    parser.add_argument(
        "--list-reports",
        action="store_true",
        help="List generated local report/export packages.",
    )
    parser.add_argument(
        "--validate-report",
        metavar="REPORT_FOLDER",
        help="Validate a generated local report/export package.",
    )
    parser.add_argument(
        "--plan-analysis",
        metavar="PROMPT",
        help="Plan a safe bounded spatial analysis without downloading feature geometries.",
    )
    parser.add_argument(
        "--execute-analysis",
        metavar="PROMPT",
        help="Execute a supported bounded local spatial analysis if counts are safe.",
    )
    parser.add_argument(
        "--list-analysis-runs",
        action="store_true",
        help="List local AutoMap spatial analysis runs.",
    )
    parser.add_argument(
        "--validate-analysis-run",
        metavar="ANALYSIS_RUN_ID_OR_FOLDER",
        help="Validate a generated analysis output folder or stored run id.",
    )
    parser.add_argument(
        "--learn-from-approved-packet",
        metavar="APPROVED_PACKET_FOLDER",
        help="Learn deterministic approved defaults from a local approved packet.",
    )
    parser.add_argument(
        "--list-patterns",
        action="store_true",
        help="List approved pattern-library records.",
    )
    parser.add_argument(
        "--list-clarification-defaults",
        action="store_true",
        help="List learned clarification defaults.",
    )
    parser.add_argument(
        "--preview-packet",
        metavar="PACKET_FOLDER_OR_WEBMAP_JSON",
        help="Print a local UI preview URL for a packet or generated WebMap JSON path.",
    )
    parser.add_argument(
        "--system-status",
        action="store_true",
        help="Print sanitized AutoMap v1 local system status.",
    )
    parser.add_argument(
        "--run-demo-workflow",
        action="store_true",
        help="Run the safe local v1 demo workflow without real publishing.",
    )
    args = parser.parse_args()

    try:
        if args.check_db:
            return _check_db()
        if args.inspect_rest_sources:
            return _inspect_rest_sources()
        if args.build_catalog_from_rest:
            return _build_catalog_from_rest()
        if args.verify_layer_catalog:
            return _verify_layer_catalog()
        if args.list_layers:
            return _list_layers()
        if args.search_layers:
            return _search_layers(args.search_layers)
        if args.export_layer_catalog_json:
            return _export_layer_catalog_json()
        if args.make_recipe:
            return _make_recipe(args.make_recipe, args.save_recipe)
        if args.profile_layer_fields:
            return _profile_layer_fields(args.layer_key)
        if args.profile_catalog_fields:
            return _profile_catalog_fields(args.category)
        if args.validate_recipe:
            return _validate_recipe(args.validate_recipe)
        if args.list_data_gaps:
            return _list_data_gaps()
        if args.make_webmap_draft:
            return _make_webmap_draft(args.make_webmap_draft)
        if args.validate_webmap_draft:
            return _validate_webmap_draft(args.validate_webmap_draft)
        if args.make_review_packet:
            return _make_review_packet(args.make_review_packet)
        if args.validate_review_packet:
            return _validate_review_packet(args.validate_review_packet)
        if args.create_adjustment_template:
            return _create_adjustment_template(args.create_adjustment_template)
        if args.apply_adjustments:
            return _apply_adjustments(args.apply_adjustments[0], args.apply_adjustments[1])
        if args.validate_adjusted_packet:
            return _validate_adjusted_packet(args.validate_adjusted_packet)
        if args.create_approval_template:
            return _create_approval_template(args.create_approval_template)
        if args.apply_approval:
            return _apply_approval(args.apply_approval[0], args.apply_approval[1])
        if args.validate_approved_packet:
            return _validate_approved_packet(args.validate_approved_packet)
        if args.list_approvals:
            return _list_approvals()
        if args.portal_check:
            return _portal_check()
        if args.publish_draft_webmap:
            dry_run = True
            if args.confirm_publish:
                dry_run = False
            if args.dry_run:
                dry_run = True
            return _publish_draft_webmap(args.publish_draft_webmap, dry_run=dry_run, confirm_publish=args.confirm_publish)
        if args.portal_smoke_test:
            return _portal_smoke_test(args.portal_smoke_test, confirm_publish=args.confirm_publish and not args.dry_run)
        if args.verify_portal_item:
            return _verify_portal_item(args.verify_portal_item, args.approved_packet)
        if args.serve_ui:
            return _serve_ui(args.ui_port)
        if args.list_packets:
            return _list_packets()
        if args.generate_report:
            return _generate_report(args.generate_report)
        if args.list_reports:
            return _list_reports()
        if args.validate_report:
            return _validate_report(args.validate_report)
        if args.plan_analysis:
            return _plan_analysis(args.plan_analysis)
        if args.execute_analysis:
            return _execute_analysis(args.execute_analysis)
        if args.list_analysis_runs:
            return _list_analysis_runs()
        if args.validate_analysis_run:
            return _validate_analysis_run(args.validate_analysis_run)
        if args.learn_from_approved_packet:
            return _learn_from_approved_packet(args.learn_from_approved_packet)
        if args.list_patterns:
            return _list_patterns()
        if args.list_clarification_defaults:
            return _list_clarification_defaults()
        if args.preview_packet:
            return _preview_packet(args.preview_packet, args.ui_port)
        if args.system_status:
            return _system_status()
        if args.run_demo_workflow:
            return _run_demo_workflow(args.ui_port)
    except ValueError as exc:
        print(f"Configuration error: {exc}")
        return 1
    except SQLAlchemyError as exc:
        print(f"Database error: {exc}")
        return 1

    _print_project_banner()
    return 0


if __name__ == "__main__":
    sys.exit(main())
