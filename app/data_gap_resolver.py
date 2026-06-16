"""Resolve AutoMap data gaps with reviewed external source candidates."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from app.data_gap_registry import KNOWN_GAPS, ensure_data_gap_registry_table, list_data_gaps
from app.db import _quote_identifier, get_engine
from app.external_source_registry import (
    get_external_source,
    init_external_source_tables,
    list_external_sources,
)
from app.source_candidate_evaluator import classify_source_limitations, inspect_source_metadata, score_source_for_gap


GAP_ALIASES = {
    "permits": "current_permits",
    "permit": "current_permits",
    "planning cases": "current_planning_cases",
    "planning": "current_planning_cases",
    "development": "current_development_pipeline",
    "development pipeline": "current_development_pipeline",
    "subdivision activity": "current_development_pipeline",
}


def _table(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def normalize_gap_key(gap_key: str) -> str:
    """Normalize topic/gap aliases to canonical gap keys."""
    return GAP_ALIASES.get(str(gap_key or "").lower(), str(gap_key or ""))


def _gap_record(gap_key: str) -> dict[str, Any]:
    canonical = normalize_gap_key(gap_key)
    for known in KNOWN_GAPS.values():
        if known["gap_key"] == canonical:
            return dict(known)
    for row in list_data_gaps():
        if row.get("gap_key") == canonical:
            return row
    return {
        "gap_key": canonical,
        "topic": canonical.replace("_", " "),
        "missing_layer_type": f"{canonical.replace('_', ' ')} layer",
        "reason": "External source review is needed.",
        "suggested_source": None,
    }


def _resolution_table(schema_name: str) -> str:
    return _table(schema_name, "data_gap_resolution_log")


def log_gap_resolution(
    gap_key: str,
    source_key: str | None,
    resolution_status: str,
    resolution_notes: str,
    source_score: float = 0.0,
    inspected_metadata: dict[str, Any] | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Insert one data gap resolution log row."""
    init_external_source_tables(schema_name)
    table = _resolution_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} AS target (
                    gap_key, source_key, resolution_status, resolution_notes,
                    source_score, inspected_metadata
                )
                VALUES (
                    :gap_key, :source_key, :resolution_status, :resolution_notes,
                    :source_score, CAST(:inspected_metadata AS jsonb)
                );
                """
            ),
            {
                "gap_key": normalize_gap_key(gap_key),
                "source_key": source_key,
                "resolution_status": resolution_status,
                "resolution_notes": resolution_notes,
                "source_score": source_score,
                "inspected_metadata": json.dumps(inspected_metadata or {}, default=str),
            },
        )
    return {
        "gap_key": normalize_gap_key(gap_key),
        "source_key": source_key,
        "resolution_status": resolution_status,
        "resolution_notes": resolution_notes,
        "source_score": source_score,
        "inspected_metadata": inspected_metadata or {},
    }


def map_gap_to_candidate_sources(gap_key: str, schema_name: str = "automap") -> list[dict[str, Any]]:
    """Return ranked candidate sources for one data gap."""
    gap = _gap_record(gap_key)
    canonical = gap["gap_key"]
    candidates: list[dict[str, Any]] = []
    for source in list_external_sources(schema_name):
        source_score = score_source_for_gap(source, canonical)
        intended = {str(item).lower() for item in source.get("intended_gaps") or []}
        if canonical.lower() not in intended and source_score < 25:
            continue
        limitations = classify_source_limitations(source)
        metadata_summary = inspect_source_metadata(source)
        candidates.append(
            {
                **source,
                "gap_key": canonical,
                "source_score": source_score,
                "metadata_summary": metadata_summary,
                "classified_limitations": limitations,
                "resolution_recommendation": _recommend_status(source, metadata_summary),
            }
        )
    return sorted(candidates, key=lambda item: (-float(item.get("source_score") or 0), int(item.get("priority") or 999), item["source_key"]))


def _recommend_status(source: dict[str, Any], metadata_summary: dict[str, Any]) -> str:
    if source.get("approval_status") == "approved" and source.get("source_status") == "active" and metadata_summary.get("is_verified"):
        return "resolved"
    if source.get("source_status") in {"proxy", "reference"} or source.get("approval_status") != "approved":
        return "needs_review"
    if metadata_summary.get("inspection_status") == "failed":
        return "rejected"
    return "inspected"


def evaluate_gap_resolution(gap_key: str, schema_name: str = "automap") -> dict[str, Any]:
    """Evaluate whether a gap has a current authoritative source."""
    candidates = map_gap_to_candidate_sources(gap_key, schema_name)
    canonical = normalize_gap_key(gap_key)
    authoritative = [
        candidate
        for candidate in candidates
        if candidate.get("approval_status") == "approved"
        and candidate.get("source_status") == "active"
        and (candidate.get("metadata_summary") or {}).get("is_verified")
    ]
    proxy = [candidate for candidate in candidates if candidate.get("source_status") == "proxy"]
    status = "resolved" if authoritative else "needs_review" if candidates else "open"
    notes = "Authoritative approved source found." if authoritative else "Candidate/proxy sources require review." if candidates else "No candidate sources are registered."
    return {
        "gap_key": canonical,
        "status": status,
        "notes": notes,
        "authoritative_sources": authoritative,
        "proxy_sources": proxy,
        "candidates": candidates,
    }


def mark_gap_status(gap_key: str, status: str, notes: str = "", schema_name: str = "automap") -> dict[str, Any]:
    """Update the data gap registry status safely."""
    canonical = normalize_gap_key(gap_key)
    ensure_data_gap_registry_table(schema_name)
    table = _table(schema_name, "data_gap_registry")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} AS target (
                    gap_key, topic, missing_layer_type, reason, suggested_source, status
                )
                VALUES (
                    :gap_key, :topic, :missing_layer_type, :reason, :suggested_source, :status
                )
                ON CONFLICT (gap_key) DO UPDATE SET
                    status = EXCLUDED.status,
                    reason = CASE
                        WHEN :notes = '' THEN target.reason
                        ELSE :notes
                    END,
                    updated_at = now();
                """
            ),
            {**_gap_record(canonical), "status": status, "notes": notes},
        )
    return {"gap_key": canonical, "status": status, "notes": notes}


def resolve_gap_with_source(
    gap_key: str,
    source_key: str,
    resolution_status: str | None = None,
    notes: str | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Record a selected source as proposed/resolved/needs-review for a gap."""
    source = get_external_source(source_key, schema_name)
    metadata_summary = inspect_source_metadata(source)
    source_score = score_source_for_gap(source, normalize_gap_key(gap_key))
    status = resolution_status or _recommend_status(source, metadata_summary)
    limitations = classify_source_limitations(source)
    resolution_notes = notes or "; ".join(limitations) or "Source reviewed."
    log = log_gap_resolution(
        gap_key,
        source_key,
        status,
        resolution_notes,
        source_score,
        source.get("inspected_metadata") or {},
        schema_name,
    )
    if status == "resolved":
        mark_gap_status(gap_key, "resolved", "Resolved by approved verified external source.", schema_name)
    elif status in {"needs_review", "proposed", "inspected"}:
        mark_gap_status(gap_key, "needs_review", resolution_notes, schema_name)
    return {"source": source, "resolution": log}


def list_gap_resolution_candidates(schema_name: str = "automap") -> list[dict[str, Any]]:
    """Return candidates for every tracked data gap."""
    gap_keys = {row.get("gap_key") for row in list_data_gaps(schema_name)}
    gap_keys.update({"current_permits", "current_planning_cases", "current_development_pipeline"})
    return [
        {
            "gap_key": gap_key,
            "candidates": map_gap_to_candidate_sources(str(gap_key), schema_name),
            "evaluation": evaluate_gap_resolution(str(gap_key), schema_name),
        }
        for gap_key in sorted(gap_keys)
        if gap_key
    ]


def resolve_known_data_gaps(schema_name: str = "automap") -> dict[str, Any]:
    """Evaluate known gaps and log proposed/needs-review/resolved status."""
    results = []
    for gap_key in ["current_permits", "current_planning_cases", "current_development_pipeline"]:
        evaluation = evaluate_gap_resolution(gap_key, schema_name)
        candidates = evaluation["candidates"]
        if candidates:
            best = candidates[0]
            result = resolve_gap_with_source(gap_key, best["source_key"], evaluation["status"], evaluation["notes"], schema_name)
            results.append({**evaluation, "selected_source_key": best["source_key"], "resolution": result["resolution"]})
        else:
            log = log_gap_resolution(gap_key, None, "proposed", "No candidate sources are registered.", 0.0, {}, schema_name)
            results.append({**evaluation, "resolution": log})
    return {"resolved": sum(1 for result in results if result["status"] == "resolved"), "results": results}


def safe_gap_context_for_recipe(missing_data: list[str]) -> dict[str, Any]:
    """Return gap candidate context without allowing DB issues to break recipe creation."""
    context: dict[str, Any] = {}
    for item in missing_data:
        gap_key = normalize_gap_key(item)
        try:
            evaluation = evaluate_gap_resolution(gap_key)
        except Exception:
            continue
        if evaluation.get("candidates"):
            context[gap_key] = {
                "status": evaluation.get("status"),
                "notes": evaluation.get("notes"),
                "candidates": [
                    {
                        "source_key": candidate.get("source_key"),
                        "source_name": candidate.get("source_name"),
                        "approval_status": candidate.get("approval_status"),
                        "source_status": candidate.get("source_status"),
                        "source_score": candidate.get("source_score"),
                        "limitations": candidate.get("classified_limitations") or [],
                    }
                    for candidate in evaluation["candidates"][:5]
                ],
            }
    return context
