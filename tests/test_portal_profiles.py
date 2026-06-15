import pytest

from app.portal_profiles import (
    get_portal_profile,
    normalize_publish_env,
    real_publish_profile_block_reasons,
)


def test_normalize_publish_env_defaults_to_dev():
    assert normalize_publish_env(None) == "dev"
    assert normalize_publish_env(" DEV ") == "dev"


def test_known_portal_profiles_load():
    assert get_portal_profile("dev").real_publish_profile_allowed is True
    assert get_portal_profile("staging").real_publish_profile_allowed is True
    assert get_portal_profile("production").production is True


def test_unknown_portal_profile_fails_clearly():
    with pytest.raises(ValueError, match="Unknown ArcGIS publish environment"):
        get_portal_profile("sandbox")


def test_production_profile_requires_explicit_safeguards():
    blocked = real_publish_profile_block_reasons(
        "production",
        allow_real_publish=False,
        confirm_publish=True,
    )
    allowed = real_publish_profile_block_reasons(
        "production",
        allow_real_publish=True,
        confirm_publish=True,
    )

    assert blocked
    assert allowed == []
