"""Source usage and coverage intelligence for AutoMap recipes."""

from __future__ import annotations

from typing import Any

from app.coverage_warnings import (
    coverage_geography,
    has_limited_coverage,
    source_text_blob,
    source_warnings,
    warning_for_missing_official_data,
)


EXTERNAL_SOURCE_KEYS = ("external_", "ncdot_", "cabarrus_accela", "concord_planning")


CATALOG_SEMANTICS: dict[str, dict[str, list[str] | str]] = {
    "transportation": {
        "aliases": [
            "traffic",
            "aadt",
            "traffic count",
            "traffic counts",
            "high traffic",
            "road volume",
            "corridor traffic",
            "transportation context",
        ],
        "planning_use_cases": [
            "high traffic corridor map",
            "transportation context",
            "site access context",
            "corridor traffic review",
        ],
        "limitations": "Reference/context only. Traffic counts are not development approvals or capacity findings.",
    },
    "transportation_projects": {
        "aliases": [
            "stip",
            "planned road projects",
            "transportation projects",
            "road improvements",
            "ncdot projects",
            "planned infrastructure",
        ],
        "planning_use_cases": [
            "planned infrastructure context",
            "corridor planning",
            "future road improvements",
            "transportation project reference",
        ],
        "limitations": "Reference/context only. STIP projects are not parcel development approvals.",
    },
    "development_activity_proxy": {
        "aliases": [
            "plan review",
            "plan reviews",
            "accela",
            "development pipeline",
            "application activity",
            "review activity",
            "development activity proxy",
        ],
        "planning_use_cases": [
            "early development signal",
            "pipeline proxy",
            "plan review context",
            "development activity review",
        ],
        "limitations": (
            "Proxy/context only. Plan review activity is not final permit approval, entitlement approval, "
            "completed development, or official capacity."
        ),
    },
    "planning_cases": {
        "aliases": [
            "planning cases",
            "rezonings",
            "rezoning cases",
            "development cases",
            "land use cases",
            "current planning cases",
        ],
        "planning_use_cases": [
            "planning case review",
            "rezoning context",
            "municipal planning activity",
            "land use case context",
        ],
        "limitations": "Coverage and case authority require review; municipal sources may not be countywide.",
    },
    "permits": {
        "aliases": [
            "permit",
            "permits",
            "building permits",
            "current permits",
            "permit activity",
        ],
        "planning_use_cases": [
            "current permit review",
            "development activity review",
            "construction activity context",
        ],
        "limitations": "Use only if verified as an official current permit source.",
    },
}


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            rows.append(text)
            seen.add(text)
    return rows


def catalog_semantics_for_category(category: str, source: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return enriched aliases/use cases/limitations for external catalog rows."""
    semantics = CATALOG_SEMANTICS.get(category, {})
    source = source or {}
    aliases = [
        category,
        *_as_list(source.get("categories")),
        *_as_list(semantics.get("aliases")),
    ]
    planning_use_cases = [
        category,
        *_as_list(source.get("intended_gaps")),
        *_as_list(semantics.get("planning_use_cases")),
    ]
    limitations = " ".join(
        item
        for item in [
            str(source.get("limitations") or "").strip(),
            str(semantics.get("limitations") or "").strip(),
        ]
        if item
    ).strip()
    return {
        "aliases": _dedupe(aliases),
        "planning_use_cases": _dedupe(planning_use_cases),
        "known_limitations": limitations,
        "canonical_topic": category,
    }


def is_external_source(layer: dict[str, Any]) -> bool:
    source_key = str(layer.get("source_key") or layer.get("layer_key") or "").lower()
    return source_key.startswith(EXTERNAL_SOURCE_KEYS) or str(layer.get("source_status") or "") in {"proxy", "reference"}


def source_role_for_layer(layer: dict[str, Any]) -> str:
    """Classify how AutoMap may use a selected source."""
    source_status = str(layer.get("source_status") or "").lower()
    approval_status = str(layer.get("approval_status") or "approved").lower()
    category = str(layer.get("category") or "").lower()
    if source_status == "proxy" or category == "development_activity_proxy":
        return "proxy"
    if source_status == "reference" or category in {"transportation_projects"}:
        return "reference"
    if source_status.startswith("legacy") or layer.get("is_historical"):
        return "historical_fallback"
    if has_limited_coverage(layer):
        return "limited_coverage"
    if approval_status == "approved" and source_status == "active":
        return "official"
    if approval_status == "candidate" and layer.get("is_verified"):
        return "limited_coverage"
    return "needs_review"


def related_gap_keys_for_layer(layer: dict[str, Any]) -> list[str]:
    category = str(layer.get("category") or "").lower()
    blob = source_text_blob(layer)
    gaps: list[str] = []
    if category == "permits" or "permit" in blob:
        gaps.append("current_permits")
    if category == "planning_cases" or "planning case" in blob or "rezoning" in blob:
        gaps.append("current_planning_cases")
    if category == "development_activity_proxy" or "plan review" in blob or "development pipeline" in blob:
        gaps.append("current_development_pipeline")
    if category == "transportation":
        gaps.append("traffic_counts")
    if category == "transportation_projects":
        gaps.append("stip_projects")
    return _dedupe(gaps)


def gap_support_for_layer(layer: dict[str, Any]) -> dict[str, Any]:
    role = source_role_for_layer(layer)
    gaps = related_gap_keys_for_layer(layer)
    if role == "official":
        status = "resolves" if gaps else "official_context"
    elif role in {"proxy", "limited_coverage"}:
        status = "partially_supports" if gaps else "review_context"
    elif role == "reference":
        status = "context_only"
    else:
        status = "does_not_resolve"
    return {
        "status": status,
        "related_gaps": gaps,
        "notes": _gap_support_note(layer, role, gaps),
    }


def _gap_support_note(layer: dict[str, Any], role: str, gaps: list[str]) -> str:
    if role == "proxy":
        return "Proxy source may support review context but does not resolve official permit, planning, or development approval gaps."
    if role == "limited_coverage":
        return "Limited-coverage source may support the matching geography but should not be treated as countywide."
    if role == "reference":
        return "Reference layer provides transportation or map context only."
    if role == "official" and gaps:
        return "Approved active source can satisfy the related gap for its verified coverage."
    return "Reviewer should confirm source use."


def display_label_for_layer(layer: dict[str, Any]) -> str:
    """Return a review-facing layer title with proxy/reference labels where useful."""
    name = str(layer.get("layer_name") or layer.get("title") or "Untitled Layer")
    category = str(layer.get("category") or "")
    source_key = str(layer.get("source_key") or "").lower()
    role = source_role_for_layer(layer)
    if category == "development_activity_proxy" or "accela" in source_key:
        return "Plan Reviews / Accela Activity (Proxy)"
    if category == "planning_cases" and (has_limited_coverage(layer) or "concord" in source_key):
        return "Concord Planning Cases (Limited Coverage)"
    if category == "transportation" and ("aadt" in source_key or "aadt" in name.lower()):
        return "NCDOT AADT Traffic Counts"
    if category == "transportation_projects" or "stip" in source_key or "stip" in name.lower():
        return "NCDOT STIP Projects"
    if role == "proxy" and "(proxy)" not in name.lower():
        return f"{name} (Proxy)"
    if role == "reference" and "(reference)" not in name.lower():
        return f"{name} (Reference)"
    if role == "limited_coverage" and "limited" not in name.lower():
        return f"{name} (Limited Coverage)"
    return name


def enrich_selected_layers_with_source_usage(
    selected_layers: list[dict[str, Any]],
    parsed_request: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Attach source usage fields to selected recipe layers."""
    enriched: list[dict[str, Any]] = []
    for layer in selected_layers:
        row = dict(layer)
        role = source_role_for_layer(row)
        support = gap_support_for_layer(row)
        warnings = source_warnings(row)
        row["source_role"] = role
        row["coverage_geography"] = coverage_geography(row)
        row["source_limitation"] = row.get("known_limitations") or row.get("source_notes") or ""
        row["gap_support"] = support
        row["coverage_warnings"] = warnings
        row["display_title"] = display_label_for_layer(row)
        if warnings:
            row["review_notes"] = _dedupe([*_as_list(row.get("review_notes")), *warnings])
        enriched.append(row)
    return enriched


def build_source_coverage(
    selected_layers: list[dict[str, Any]],
    missing_data: list[str] | None = None,
    data_gap_context: dict[str, Any] | None = None,
    parsed_request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the source_coverage object embedded in map recipes."""
    official_sources: list[dict[str, Any]] = []
    proxy_sources: list[dict[str, Any]] = []
    limited_sources: list[dict[str, Any]] = []
    reference_sources: list[dict[str, Any]] = []
    historical_sources: list[dict[str, Any]] = []
    warnings: list[str] = []
    selected_source_roles: dict[str, dict[str, Any]] = {}

    for layer in selected_layers:
        entry = _coverage_entry(layer)
        layer_key = str(layer.get("layer_key") or layer.get("layer_name") or "")
        if layer_key:
            selected_source_roles[layer_key] = entry
        role = entry["source_role"]
        if role == "official":
            official_sources.append(entry)
        elif role == "proxy":
            proxy_sources.append(entry)
        elif role == "limited_coverage":
            limited_sources.append(entry)
        elif role == "reference":
            reference_sources.append(entry)
        elif role == "historical_fallback":
            historical_sources.append(entry)
        warnings.extend(entry.get("warnings") or [])

    missing_official_sources = _missing_official_sources(
        selected_layers,
        missing_data or [],
        data_gap_context or {},
        parsed_request or {},
    )
    warnings.extend(item["warning"] for item in missing_official_sources if item.get("warning"))

    return {
        "official_sources": official_sources,
        "proxy_sources": proxy_sources,
        "limited_coverage_sources": limited_sources,
        "reference_sources": reference_sources,
        "historical_fallback_sources": historical_sources,
        "missing_official_sources": missing_official_sources,
        "selected_source_roles": selected_source_roles,
        "warnings": _dedupe(warnings),
    }


def _coverage_entry(layer: dict[str, Any]) -> dict[str, Any]:
    support = layer.get("gap_support") if isinstance(layer.get("gap_support"), dict) else gap_support_for_layer(layer)
    return {
        "layer_key": layer.get("layer_key"),
        "layer_name": layer.get("layer_name"),
        "display_title": layer.get("display_title") or display_label_for_layer(layer),
        "category": layer.get("category"),
        "source_key": layer.get("source_key"),
        "source_status": layer.get("source_status"),
        "approval_status": layer.get("approval_status") or "approved",
        "source_role": layer.get("source_role") or source_role_for_layer(layer),
        "coverage_geography": layer.get("coverage_geography") or coverage_geography(layer),
        "limitation": layer.get("source_limitation") or layer.get("known_limitations") or "",
        "gap_support": support,
        "warnings": layer.get("coverage_warnings") or source_warnings(layer),
    }


def _missing_official_sources(
    selected_layers: list[dict[str, Any]],
    missing_data: list[str],
    data_gap_context: dict[str, Any],
    parsed_request: dict[str, Any],
) -> list[dict[str, Any]]:
    requested_gaps = set(_gap_keys_from_missing_data(missing_data))
    prompt = str(parsed_request.get("normalized_prompt") or parsed_request.get("raw_prompt") or "").lower()
    if "permit" in prompt or "development activity" in prompt or "development pressure" in prompt:
        requested_gaps.add("current_permits")
    if "planning case" in prompt or "rezoning" in prompt:
        requested_gaps.add("current_planning_cases")
    if "development pipeline" in prompt or "development pressure" in prompt or "development activity" in prompt:
        requested_gaps.add("current_development_pipeline")

    official_resolved: set[str] = set()
    partial: dict[str, list[dict[str, Any]]] = {}
    for layer in selected_layers:
        support = layer.get("gap_support") if isinstance(layer.get("gap_support"), dict) else gap_support_for_layer(layer)
        for gap in support.get("related_gaps") or []:
            if support.get("status") == "resolves":
                official_resolved.add(gap)
            elif support.get("status") in {"partially_supports", "context_only"}:
                partial.setdefault(gap, []).append(_coverage_entry(layer))

    rows: list[dict[str, Any]] = []
    for gap_key in sorted(requested_gaps):
        if gap_key in official_resolved:
            continue
        if gap_key == "current_planning_cases" and partial.get(gap_key) and _request_geography_is_concord(parsed_request):
            continue
        context = data_gap_context.get(gap_key) or {}
        rows.append(
            {
                "gap_key": gap_key,
                "status": context.get("status") or ("partially_supported" if partial.get(gap_key) else "needs_review"),
                "reason": context.get("notes") or "No official verified source is selected for this request.",
                "partial_sources": partial.get(gap_key, []),
                "candidate_sources": context.get("candidates") or [],
                "warning": warning_for_missing_official_data(gap_key),
            }
        )
    return rows


def _request_geography_is_concord(parsed_request: dict[str, Any]) -> bool:
    prompt = str(parsed_request.get("normalized_prompt") or parsed_request.get("raw_prompt") or "").lower()
    if "concord" in prompt:
        return True
    for geography in parsed_request.get("geography_terms") or []:
        if isinstance(geography, dict) and str(geography.get("name") or "").lower() == "concord":
            return True
    return False


def _gap_keys_from_missing_data(missing_data: list[str]) -> list[str]:
    aliases = {
        "permits": "current_permits",
        "permit": "current_permits",
        "planning cases": "current_planning_cases",
        "planning": "current_planning_cases",
        "development": "current_development_pipeline",
        "development pipeline": "current_development_pipeline",
        "subdivision activity": "current_development_pipeline",
    }
    return [aliases.get(str(item).lower(), str(item)) for item in missing_data]
