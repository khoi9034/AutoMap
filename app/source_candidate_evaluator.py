"""Rule-based evaluation for external AutoMap source candidates."""

from __future__ import annotations

from typing import Any


GAP_TERMS = {
    "current_permits": {"permit", "permits", "building", "accela", "development"},
    "current_planning_cases": {"planning", "case", "cases", "rezoning", "zoning", "development"},
    "current_development_pipeline": {"pipeline", "development", "plan_review", "review", "subdivision", "project", "accela"},
    "traffic_counts": {"traffic", "aadt", "transportation"},
    "stip_projects": {"stip", "transportation", "project", "planned_projects"},
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).lower() for item in value]
    return [str(value).lower()]


def _blob(source: dict[str, Any]) -> str:
    parts = [
        source.get("source_key"),
        source.get("source_name"),
        source.get("source_type"),
        source.get("approval_status"),
        source.get("source_status"),
        source.get("notes"),
        source.get("limitations"),
        *_as_list(source.get("categories")),
        *_as_list(source.get("intended_gaps")),
    ]
    return " ".join(str(part or "").lower() for part in parts)


def score_source_for_gap(source: dict[str, Any], gap: dict[str, Any] | str) -> float:
    """Score how well a source may address one data gap."""
    gap_key = gap if isinstance(gap, str) else str(gap.get("gap_key") or gap.get("topic") or "")
    intended_gaps = set(_as_list(source.get("intended_gaps")))
    categories = set(_as_list(source.get("categories")))
    text = _blob(source)
    score = 0.0
    if gap_key.lower() in intended_gaps:
        score += 70
    for term in GAP_TERMS.get(gap_key, {gap_key.lower()}):
        if term in categories:
            score += 18
        if term in text:
            score += 8
    if source.get("approval_status") == "approved":
        score += 20
    elif source.get("approval_status") == "candidate":
        score += 8
    else:
        score -= 5
    if source.get("source_status") == "proxy":
        score -= 8
    elif source.get("source_status") == "reference":
        score -= 4
    metadata = source.get("inspected_metadata") or {}
    if metadata.get("is_verified"):
        score += 25
    if metadata.get("inspection_status") == "failed":
        score -= 30
    return max(0.0, round(score, 2))


def inspect_source_metadata(source: dict[str, Any]) -> dict[str, Any]:
    """Return normalized metadata summary for frontend/API display."""
    metadata = source.get("inspected_metadata") or {}
    return {
        "inspection_status": metadata.get("inspection_status") or "not_inspected",
        "is_verified": bool(metadata.get("is_verified")),
        "record_count": metadata.get("record_count"),
        "downloaded_geometry": bool(metadata.get("downloaded_geometry")),
        "verification_status": metadata.get("verification_status"),
        "verification_error": metadata.get("verification_error"),
        "layer_count": len(metadata.get("layers") or []),
    }


def classify_source_limitations(source: dict[str, Any]) -> list[str]:
    """Classify important review limitations for a source."""
    limitations: list[str] = []
    approval_status = source.get("approval_status")
    source_status = source.get("source_status")
    text = _blob(source)
    metadata = source.get("inspected_metadata") or {}
    if approval_status != "approved":
        limitations.append("Source requires review before authoritative use.")
    if source_status == "proxy":
        limitations.append("Proxy/context only; not official development approval, permit issuance, or capacity.")
    if source_status == "reference":
        limitations.append("Reference/context only.")
    if "concord" in text and ("limited" in text or "only" in text):
        limitations.append("Coverage may be limited to Concord.")
    if not (source.get("base_url") or source.get("layer_url")):
        limitations.append("No ArcGIS REST URL is configured yet.")
    if metadata.get("inspection_status") == "failed":
        limitations.append("Metadata inspection failed.")
    if metadata.get("inspection_status") == "reference_only":
        limitations.append("External reference only; no layer metadata was inspected.")
    return sorted(set(limitations))


def recommend_catalog_category(source: dict[str, Any]) -> str:
    """Recommend a catalog category for verified external source layers."""
    categories = set(_as_list(source.get("categories")))
    if {"aadt", "traffic", "transportation", "stip", "planned_projects"} & categories:
        return "transportation"
    if {"permit", "plan_review", "planning", "development_pipeline_proxy"} & categories:
        return "development"
    if {"utility", "infrastructure"} & categories:
        return "utility"
    return next(iter(categories), "reference")
