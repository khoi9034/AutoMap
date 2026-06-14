"""Configuration helpers for AutoMap."""

from dataclasses import dataclass
import os

from dotenv import load_dotenv


DEFAULT_AUTOMAP_SCHEMA = "automap"


@dataclass(frozen=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    DATABASE_URL: str | None
    AUTOMAP_DB_SCHEMA: str = DEFAULT_AUTOMAP_SCHEMA


def get_settings() -> Settings:
    """Load AutoMap settings from environment variables and a local .env file."""
    load_dotenv()

    return Settings(
        DATABASE_URL=os.getenv("DATABASE_URL"),
        AUTOMAP_DB_SCHEMA=os.getenv("AUTOMAP_DB_SCHEMA", DEFAULT_AUTOMAP_SCHEMA)
        or DEFAULT_AUTOMAP_SCHEMA,
    )


def require_database_url(settings: Settings | None = None) -> str:
    """Return DATABASE_URL or raise a helpful error when it is not configured."""
    loaded_settings = settings or get_settings()
    if not loaded_settings.DATABASE_URL:
        raise ValueError(
            "DATABASE_URL is not configured. Copy .env.example to .env and set "
            "AutoMap's own PostGIS connection string."
        )

    return loaded_settings.DATABASE_URL

