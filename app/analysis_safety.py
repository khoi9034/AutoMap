"""Conservative safety limits for bounded AutoMap spatial analysis."""

from __future__ import annotations

import os
from typing import Any

from app.analysis_models import DEFAULT_MAX_FEATURES, HARD_MAX_FEATURES


DEFAULT_MAX_CHUNKS = 25
DEFAULT_MAX_FEATURES_PER_CHUNK = 1000
DEFAULT_MAX_CONSTRAINT_FEATURES = 500
DEFAULT_MAX_QUERY_SECONDS_PER_LAYER = 60
DEFAULT_MAX_TOTAL_ANALYSIS_SECONDS = 300


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int | None = None) -> int:
    raw_value = os.getenv(name)
    if not raw_value:
        return default
    try:
        value = int(raw_value)
    except ValueError:
        return default
    value = max(minimum, value)
    if maximum is not None:
        value = min(maximum, value)
    return value


def load_analysis_safety_limits(max_features: int | None = None) -> dict[str, int]:
    """Return local v2.1 analysis limits with safe defaults and env overrides."""
    configured_max = _env_int(
        "AUTOMAP_MAX_DOWNLOAD_FEATURES_PER_LAYER",
        max_features or DEFAULT_MAX_FEATURES,
        maximum=HARD_MAX_FEATURES,
    )
    return {
        "max_download_features_per_layer": min(configured_max, HARD_MAX_FEATURES),
        "hard_max_download_features": HARD_MAX_FEATURES,
        "max_chunks": _env_int("AUTOMAP_MAX_ANALYSIS_CHUNKS", DEFAULT_MAX_CHUNKS, maximum=100),
        "max_features_per_chunk": _env_int(
            "AUTOMAP_MAX_FEATURES_PER_CHUNK",
            DEFAULT_MAX_FEATURES_PER_CHUNK,
            maximum=HARD_MAX_FEATURES,
        ),
        "max_constraint_features": _env_int(
            "AUTOMAP_MAX_CONSTRAINT_FEATURES",
            DEFAULT_MAX_CONSTRAINT_FEATURES,
            maximum=HARD_MAX_FEATURES,
        ),
        "max_query_seconds_per_layer": _env_int("AUTOMAP_MAX_QUERY_SECONDS_PER_LAYER", DEFAULT_MAX_QUERY_SECONDS_PER_LAYER),
        "max_total_analysis_seconds": _env_int("AUTOMAP_MAX_TOTAL_ANALYSIS_SECONDS", DEFAULT_MAX_TOTAL_ANALYSIS_SECONDS),
    }


def enforce_max_count(count: int | None, max_count: int, label: str) -> dict[str, Any]:
    """Return a structured safety check for a count limit."""
    safe_count = int(count or 0)
    passed = safe_count <= max_count
    return {
        "label": label,
        "count": safe_count,
        "limit": max_count,
        "passed": passed,
        "reason": None if passed else f"{label} count {safe_count} exceeds limit {max_count}.",
    }


def enforce_max_chunks(chunk_count: int, max_chunks: int) -> dict[str, Any]:
    """Return a structured safety check for chunk count."""
    return enforce_max_count(chunk_count, max_chunks, "analysis chunk")


def enforce_max_features_per_chunk(feature_count: int, max_features_per_chunk: int, label: str = "chunk candidate") -> dict[str, Any]:
    """Return a structured safety check for one chunk."""
    return enforce_max_count(feature_count, max_features_per_chunk, label)


def enforce_max_total_downloads(feature_count: int, max_download_features: int) -> dict[str, Any]:
    """Return a structured safety check for total feature download size."""
    return enforce_max_count(feature_count, max_download_features, "final selected feature download")


def narrowing_suggestions() -> list[str]:
    """Common reviewer suggestions when a bounded analysis is still too broad."""
    return [
        "Use a smaller geography such as a neighborhood, corridor, or subdivision.",
        "Choose a specific flood layer such as FloodWay or FloodPlain100year.",
        "Add an attribute filter such as parcel type, zoning category, acreage, or assessed value.",
        "Split the request into multiple smaller municipal areas.",
    ]


def block_with_reason(
    reason: str,
    *,
    suggestions: list[str] | None = None,
    safety_checks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a consistent blocked-analysis payload."""
    return {
        "blocked": True,
        "reason": reason,
        "blocked_reasons": [reason],
        "narrowing_suggestions": suggestions or narrowing_suggestions(),
        "safety_checks": safety_checks or [],
    }


def build_safety_summary(
    *,
    limits: dict[str, int],
    safety_checks: list[dict[str, Any]] | None = None,
    blocked_reasons: list[str] | None = None,
    narrowing: list[str] | None = None,
) -> dict[str, Any]:
    """Return receipt-ready safety metadata."""
    checks = safety_checks or []
    blocked = bool(blocked_reasons) or any(not check.get("passed", True) for check in checks)
    return {
        "limits": limits,
        "checks": checks,
        "blocked": blocked,
        "blocked_reasons": blocked_reasons or [check["reason"] for check in checks if check.get("reason")],
        "narrowing_suggestions": narrowing or (narrowing_suggestions() if blocked else []),
    }
