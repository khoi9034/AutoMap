"""Configuration helpers for AutoMap."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv
from sqlalchemy.engine import make_url


DEFAULT_AUTOMAP_SCHEMA = "automap"
AUTOMAP_DEV_DATABASE = "automap"
SUPABASE_DIRECT_DATABASE = "postgres"
SUPABASE_PROJECT_REF = "mjfbpmatxvjczikqbuva"
SUPABASE_DIRECT_HOST = f"db.{SUPABASE_PROJECT_REF}.supabase.co"
SUPABASE_POOLER_HOST_SUFFIX = ".pooler.supabase.com"
VERCEL_PROJECT_PREVIEW_ORIGIN_REGEX = (
    r"^https://(?:"
    r"auto-map-cyan|"
    r"auto-[a-z0-9-]+-(?:khoi9034|khoi-nguyens-projects-9f6b140b)|"
    r"auto-map-[a-z0-9-]+-(?:khoi9034|khoi-nguyens-projects-9f6b140b)"
    r")\.vercel\.app$"
)
LOCAL_AUTOMAP_HOSTS = {"localhost", "127.0.0.1", "::1", ""}
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
    ALLOWED_ORIGIN_REGEX: str | None = None
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
        ALLOWED_ORIGIN_REGEX=os.getenv("ALLOWED_ORIGIN_REGEX"),
        FRONTEND_ORIGIN=os.getenv("FRONTEND_ORIGIN"),
    )


def _database_name_from_url(database_url: str) -> str | None:
    return make_url(database_url).database


def _normalized_host(database_url: str) -> str:
    return (make_url(database_url).host or "").lower()


def _normalized_username(database_url: str) -> str:
    return (make_url(database_url).username or "").lower()


def _is_local_automap_database(database_url: str) -> bool:
    parsed_url = make_url(database_url)
    host = (parsed_url.host or "").lower()
    return parsed_url.database == AUTOMAP_DEV_DATABASE and host in LOCAL_AUTOMAP_HOSTS


def _is_supabase_direct_database(database_url: str) -> bool:
    parsed_url = make_url(database_url)
    return parsed_url.database == SUPABASE_DIRECT_DATABASE and _normalized_host(database_url) == SUPABASE_DIRECT_HOST


def _is_supabase_pooler_database(database_url: str) -> bool:
    parsed_url = make_url(database_url)
    host = _normalized_host(database_url)
    username = _normalized_username(database_url)
    pooler_host = host.endswith(SUPABASE_POOLER_HOST_SUFFIX)
    postgres_user = username == "postgres" or username.startswith("postgres.")
    known_project = SUPABASE_PROJECT_REF in username or SUPABASE_PROJECT_REF in host
    return (
        parsed_url.database == SUPABASE_DIRECT_DATABASE
        and pooler_host
        and postgres_user
        and known_project
    )


def database_host_kind(database_url: str | None) -> str:
    """Classify an AutoMap DATABASE_URL without exposing host or credentials."""
    if not database_url:
        return "unknown"
    try:
        if _is_local_automap_database(database_url):
            return "local_dev"
        if _is_supabase_direct_database(database_url):
            return "supabase_direct"
        if _is_supabase_pooler_database(database_url):
            return "supabase_pooler"
    except Exception:
        return "unknown"
    return "unknown"


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


def allowed_origin_regex_from_settings(settings: Settings) -> str:
    """Return a restricted CORS regex for AutoMap's Vercel production/preview hosts."""
    configured = (settings.ALLOWED_ORIGIN_REGEX or "").strip()
    if configured:
        return f"(?:{configured})|(?:{VERCEL_PROJECT_PREVIEW_ORIGIN_REGEX})"
    return VERCEL_PROJECT_PREVIEW_ORIGIN_REGEX


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

    is_allowed_database = (
        _is_local_automap_database(database_url)
        or _is_supabase_direct_database(database_url)
        or _is_supabase_pooler_database(database_url)
    )
    if not is_allowed_database:
        raise ValueError(
            "Configured database must point to AutoMap's local dev database "
            f"'{AUTOMAP_DEV_DATABASE}', the Supabase direct Postgres database "
            "'postgres', or the approved Supabase Session Pooler for the "
            f"'{SUPABASE_PROJECT_REF}' project."
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
