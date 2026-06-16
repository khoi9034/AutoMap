"""Standardized source coverage warnings for AutoMap recipes."""

from __future__ import annotations

from typing import Any


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def source_text_blob(source: dict[str, Any]) -> str:
    """Return a lowercase text blob for coverage and limitation checks."""
    values: list[str] = []
    for field in [
        "layer_key",
        "layer_name",
        "category",
        "canonical_topic",
        "source_key",
        "source_status",
        "approval_status",
        "service_name",
        "description",
        "known_limitations",
        "source_limitation",
        "source_notes",
    ]:
        values.append(str(source.get(field) or ""))
    values.extend(_as_list(source.get("aliases")))
    values.extend(_as_list(source.get("planning_use_cases")))
    return " ".join(values).lower()


def has_limited_coverage(source: dict[str, Any]) -> bool:
    """Return whether source metadata indicates limited geography coverage."""
    blob = source_text_blob(source)
    return any(
        phrase in blob
        for phrase in [
            "limited coverage",
            "coverage limited",
            "limited to concord",
            "concord only",
            "municipal only",
            "municipal coverage",
        ]
    )


def coverage_geography(source: dict[str, Any]) -> str:
    """Return a plain-language coverage geography label."""
    blob = source_text_blob(source)
    source_key = str(source.get("source_key") or "").lower()
    service_name = str(source.get("service_name") or "").lower()
    if "limited to concord" in blob or "concord only" in blob or "concord" in source_key:
        return "Concord only or Concord-limited; confirm before non-Concord use."
    if "ncdot" in source_key or "ncdot" in service_name:
        return "NCDOT statewide/reference context; filter to Cabarrus during review."
    if "cabarrus" in source_key or "cabarrus" in service_name:
        return "Cabarrus County service-defined coverage."
    return "Service-defined coverage; reviewer should confirm extent."


def warning_for_proxy_source(source: dict[str, Any]) -> str:
    return (
        f"{source.get('layer_name') or source.get('source_key')}: proxy/context source only; "
        "do not treat it as official approval, permit issuance, completed development, or capacity."
    )


def warning_for_reference_source(source: dict[str, Any]) -> str:
    return (
        f"{source.get('layer_name') or source.get('source_key')}: reference/context layer only; "
        "use it for map context, not as development approval or pipeline evidence."
    )


def warning_for_limited_coverage(source: dict[str, Any]) -> str:
    return (
        f"{source.get('layer_name') or source.get('source_key')}: coverage is limited or needs geography review; "
        "do not imply countywide coverage."
    )


def warning_for_historical_source(source: dict[str, Any]) -> str:
    return (
        f"{source.get('layer_name') or source.get('source_key')}: historical fallback layer; "
        "do not use as current data unless the request is historical."
    )


def warning_for_missing_official_data(gap_key: str) -> str:
    labels = {
        "current_permits": "official current permit layer",
        "current_planning_cases": "official current planning case layer",
        "current_development_pipeline": "official current development pipeline layer",
    }
    label = labels.get(gap_key, gap_key.replace("_", " "))
    return f"Missing {label}; proxy or reference sources do not resolve this official data gap."


def source_warnings(source: dict[str, Any]) -> list[str]:
    """Build standardized warnings for one selected source/layer."""
    warnings: list[str] = []
    source_status = str(source.get("source_status") or "").lower()
    if source_status == "proxy" or source.get("category") == "development_activity_proxy":
        warnings.append(warning_for_proxy_source(source))
    if source_status == "reference":
        warnings.append(warning_for_reference_source(source))
    if has_limited_coverage(source):
        warnings.append(warning_for_limited_coverage(source))
    if source_status.startswith("legacy") or source.get("is_historical"):
        warnings.append(warning_for_historical_source(source))
    return sorted(set(warnings))
