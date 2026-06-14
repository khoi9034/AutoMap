"""Configuration helpers for AutoMap."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


DEFAULT_AUTOMAP_SCHEMA = "automap"
AUTOMAP_DEV_DATABASE = "automap"
PROTECTED_DATABASE_NAMES = {"cfs_dev"}
PLACEHOLDER_PASSWORDS = {
    "YOUR_LOCAL_POSTGRES_PASSWORD",
    "your_password",
    "your_admin_password",
}


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    DATABASE_URL: str | None
    AUTOMAP_DB_SCHEMA: str = DEFAULT_AUTOMAP_SCHEMA


def get_settings(load_env_file: bool = True) -> Settings:
    """Load AutoMap settings from environment variables and a local .env file."""
    if load_env_file:
        load_dotenv()

    return Settings(
        DATABASE_URL=os.getenv("DATABASE_URL"),
        AUTOMAP_DB_SCHEMA=os.getenv("AUTOMAP_DB_SCHEMA", DEFAULT_AUTOMAP_SCHEMA)
        or DEFAULT_AUTOMAP_SCHEMA,
    )


def _database_name_from_url(database_url: str) -> str | None:
    return make_url(database_url).database


def validate_settings(settings: Settings) -> None:
    """Validate database settings before opening a database connection."""
    database_url = settings.DATABASE_URL
    if not database_url:
        raise ValueError(
            "DATABASE_URL is not configured. Copy .env.example to .env and set "
            "AutoMap's own PostGIS connection string."
        )

    parsed_url = make_url(database_url)
    database_name = _database_name_from_url(database_url)
    if database_name in PROTECTED_DATABASE_NAMES:
        raise ValueError(
            "DATABASE_URL points to protected CFS database 'cfs_dev'. AutoMap "
            "must use its own database 'automap'."
        )

    if database_name != AUTOMAP_DEV_DATABASE:
        raise ValueError(
            "DATABASE_URL must point to AutoMap's local dev database "
            f"'{AUTOMAP_DEV_DATABASE}'."
        )

    if parsed_url.password in PLACEHOLDER_PASSWORDS:
        raise ValueError(
            "DATABASE_URL still contains a placeholder password. Replace "
            "YOUR_LOCAL_POSTGRES_PASSWORD in .env with your local PostgreSQL "
            "password."
        )

    if settings.AUTOMAP_DB_SCHEMA != DEFAULT_AUTOMAP_SCHEMA:
        raise ValueError(
            f"AUTOMAP_DB_SCHEMA must be '{DEFAULT_AUTOMAP_SCHEMA}' for the "
            "AutoMap dev database."
        )


def require_database_url(settings: Settings | None = None) -> str:
    """Return DATABASE_URL or raise a helpful error when it is not configured."""
    loaded_settings = settings or get_settings()
    validate_settings(loaded_settings)

    return loaded_settings.DATABASE_URL or ""
