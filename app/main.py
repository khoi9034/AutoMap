"""Command-line entry point for AutoMap."""

import argparse
import sys

from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import test_db_connection


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


def main() -> int:
    """Run the AutoMap command-line interface."""
    parser = argparse.ArgumentParser(description="AutoMap command-line tools")
    parser.add_argument(
        "--check-db",
        action="store_true",
        help="Check AutoMap's own PostGIS database connection.",
    )
    args = parser.parse_args()

    if args.check_db:
        return _check_db()

    _print_project_banner()
    return 0


if __name__ == "__main__":
    sys.exit(main())
