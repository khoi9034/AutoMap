"""Command-line entry point for AutoMap."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.catalog_builder import build_catalog_records, inspect_services
from app.config import get_settings
from app.data_gap_registry import list_data_gaps
from app.db import test_db_connection
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
from app.recipe_engine import build_recipe
from app.rest_sources import load_rest_sources


def _print_project_banner() -> None:
    print("AutoMap: County GIS Request Engine")
    print("v0.0 repo setup only")


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
