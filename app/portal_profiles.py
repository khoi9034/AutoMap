"""Named ArcGIS portal profile rules for AutoMap publishing."""

from __future__ import annotations

from dataclasses import dataclass


KNOWN_PORTAL_PROFILES = {"dev", "staging", "production"}


@dataclass(frozen=True)
class PortalProfile:
    """Publishing profile metadata loaded from environment names."""

    name: str
    description: str
    production: bool
    real_publish_profile_allowed: bool


PORTAL_PROFILES = {
    "dev": PortalProfile(
        name="dev",
        description="Development profile for controlled private draft publishing tests.",
        production=False,
        real_publish_profile_allowed=True,
    ),
    "staging": PortalProfile(
        name="staging",
        description="Optional staging profile for controlled private draft publishing.",
        production=False,
        real_publish_profile_allowed=True,
    ),
    "production": PortalProfile(
        name="production",
        description="Production profile. Blocked unless explicit real-publish safeguards are enabled.",
        production=True,
        real_publish_profile_allowed=False,
    ),
}


def normalize_publish_env(value: str | None) -> str:
    """Normalize a publish environment name."""
    normalized = str(value or "dev").strip().lower()
    return normalized or "dev"


def get_portal_profile(value: str | None) -> PortalProfile:
    """Return a known portal profile or raise a clear configuration error."""
    name = normalize_publish_env(value)
    if name not in PORTAL_PROFILES:
        raise ValueError(f"Unknown ArcGIS publish environment: {name}")
    return PORTAL_PROFILES[name]


def real_publish_profile_block_reasons(
    value: str | None,
    *,
    allow_real_publish: bool,
    confirm_publish: bool,
) -> list[str]:
    """Return profile-specific block reasons for real publishing."""
    profile = get_portal_profile(value)
    if profile.production and not (allow_real_publish and confirm_publish):
        return [
            "Production profile requires AUTOMAP_ALLOW_REAL_PUBLISH=true and --confirm-publish."
        ]
    if not profile.real_publish_profile_allowed and not (allow_real_publish and confirm_publish):
        return [f"Portal profile {profile.name} is blocked for real publishing without explicit safeguards."]
    return []
