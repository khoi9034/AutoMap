"""Command-line entry point for AutoMap."""

import argparse
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.catalog_builder import build_catalog_records, inspect_services
from app.config import get_settings
from app.db import test_db_connection
from app.layer_catalog_store import (
    export_layer_catalog_json,
    list_layers,
    search_layers,
    upsert_layer_records,
    verify_catalog_layers,
)
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
