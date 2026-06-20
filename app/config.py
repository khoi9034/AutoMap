"""Configuration helpers for AutoMap."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


DEFAULT_AUTOMAP_SCHEMA = "automap"
AUTOMAP_DEV_DATABASE = "automap"
SUPABASE_DIRECT_DATABASE = "postgres"
SUPABASE_HOST_SUFFIX = ".supabase.co"
PROTECTED_DATABASE_NAMES = {"cfs_dev"}
PLACEHOLDER_PASSWORDS = {
    "YOUR_LOCAL_POSTGRES_PASSWORD",
    "YOUR_SUPABASE_DB_PASSWORD",
    "your_password",
    "your_admin_password",
    "your_supabase_db_password",
}


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    DATABASE_URL: str | None
    AUTOMAP_DB_SCHEMA: str = DEFAULT_AUTOMAP_SCHEMA
    ALLOWED_ORIGINS: str | None = None
    FRONTEND_ORIGIN: str | None = None


def get_settings(load_env_file: bool = True) -> Settings:
    """Load AutoMap settings from environment variables and a local .env file."""
    if load_env_file:
        load_dotenv()

    return Settings(
        DATABASE_URL=os.getenv("DATABASE_URL"),
        AUTOMAP_DB_SCHEMA=os.getenv("AUTOMAP_DB_SCHEMA", DEFAULT_AUTOMAP_SCHEMA)
        or DEFAULT_AUTOMAP_SCHEMA,
        ALLOWED_ORIGINS=os.getenv("ALLOWED_ORIGINS"),
        FRONTEND_ORIGIN=os.getenv("FRONTEND_ORIGIN"),
    )


def _database_name_from_url(database_url: str) -> str | None:
    return make_url(database_url).database


def _is_supabase_direct_database(database_url: str) -> bool:
    parsed_url = make_url(database_url)
    host = parsed_url.host or ""
    return (
        parsed_url.database == SUPABASE_DIRECT_DATABASE
        and host.startswith("db.")
        and host.endswith(SUPABASE_HOST_SUFFIX)
    )


def parse_allowed_origins(value: str | None) -> list[str]:
    """Parse comma-separated origins from an environment variable."""
    if not value:
        return []
    cleaned = value.strip()
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    origins: list[str] = []
    for part in cleaned.split(","):
        origin = part.strip().strip("\"'")
        if origin and origin not in origins:
            origins.append(origin)
    return origins


def allowed_origins_from_settings(settings: Settings) -> list[str]:
    """Return CORS origins from env settings plus local AutoMap defaults."""
    origins = [
        "http://127.0.0.1:3010",
        "http://localhost:3010",
        *parse_allowed_origins(settings.ALLOWED_ORIGINS),
    ]
    if settings.FRONTEND_ORIGIN:
        origins.extend(parse_allowed_origins(settings.FRONTEND_ORIGIN))

    deduped: list[str] = []
    for origin in origins:
        if origin and origin not in deduped:
            deduped.append(origin)
    return deduped


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
            "Configured database points to protected CFS database 'cfs_dev'. AutoMap "
            "must use its own database 'automap'."
        )

    if database_name != AUTOMAP_DEV_DATABASE and not _is_supabase_direct_database(database_url):
        raise ValueError(
            "Configured database must point to AutoMap's local dev database "
            f"'{AUTOMAP_DEV_DATABASE}' or the Supabase direct Postgres "
            "database 'postgres'."
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
            "AutoMap database."
        )


def require_database_url(settings: Settings | None = None) -> str:
    """Return DATABASE_URL or raise a helpful error when it is not configured."""
    loaded_settings = settings or get_settings()
    validate_settings(loaded_settings)

    return loaded_settings.DATABASE_URL or ""
