"""Local deterministic feedback learning for AutoMap."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.clarification_engine import get_clarification_session
from app.db import get_engine
from app.pattern_library import (
    _json_text,
    _qualified,
    _upsert_clarification_defaults,
    extract_pattern_from_approved_packet,
    init_pattern_tables,
    list_feedback,
    upsert_approved_pattern,
)


VALID_FEEDBACK_TYPES = {
    "approved",
    "needs_changes",
    "rejected",
    "manual_adjustment",
    "clarification_answered",
}


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def record_recipe_feedback(
    raw_prompt: str,
    recipe: dict[str, Any],
    feedback_type: str,
    feedback_json: dict[str, Any],
    source_packet_path: str | Path | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Record one local feedback event without external services."""
    if feedback_type not in VALID_FEEDBACK_TYPES:
        raise ValueError(f"Unsupported feedback_type: {feedback_type}")
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "recipe_feedback_log")
    engine = get_engine()
    with engine.begin() as connection:
        row_id = connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    raw_prompt, recipe_json, feedback_type, feedback_json,
                    source_packet_path, created_at
                )
                VALUES (
                    :raw_prompt, CAST(:recipe_json AS jsonb), :feedback_type,
                    CAST(:feedback_json AS jsonb), :source_packet_path, now()
                )
                RETURNING id;
                """
            ),
            {
                "raw_prompt": raw_prompt,
                "recipe_json": _json_text(recipe or {}),
                "feedback_type": feedback_type,
                "feedback_json": _json_text(feedback_json or {}),
                "source_packet_path": str(source_packet_path) if source_packet_path else None,
            },
        ).scalar_one()
    return {
        "id": row_id,
        "raw_prompt": raw_prompt,
        "feedback_type": feedback_type,
        "feedback_json": feedback_json or {},
        "source_packet_path": str(source_packet_path) if source_packet_path else None,
    }


def learn_from_approved_packet(approved_packet_folder: str | Path, schema_name: str = "automap") -> dict[str, Any]:
    """Extract and store an approved packet pattern."""
    pattern = extract_pattern_from_approved_packet(approved_packet_folder)
    stored = upsert_approved_pattern(pattern, schema_name=schema_name)
    recipe = _load_json(Path(approved_packet_folder) / "approved_recipe.json", {})
    record_recipe_feedback(
        pattern.get("raw_prompt") or "",
        recipe,
        "approved",
        {
            "pattern_key": stored["pattern_key"],
            "final_publish_ready": stored.get("final_publish_ready"),
            "clarification_defaults_upserted": stored.get("clarification_defaults_upserted", 0),
        },
        source_packet_path=approved_packet_folder,
        schema_name=schema_name,
    )
    return stored


def learn_from_clarification_session(session_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Record clarification answers as local feedback."""
    session = get_clarification_session(session_id, schema_name=schema_name)
    recipe = session.get("refined_recipe") or session.get("initial_recipe") or {}
    parsed = recipe.get("parsed_request") or {}
    intelligence = recipe.get("request_intelligence") or {}
    default_count = _upsert_clarification_defaults(
        {
            "pattern_key": f"clarification_{session_id}",
            "primary_intent": intelligence.get("primary_intent"),
            "topics": parsed.get("topics") or [],
            "clarification_answers": session.get("answers") or [],
            "confidence_score": min(float(recipe.get("confidence_score") or 0.65), 0.75),
        },
        schema_name=schema_name,
    )
    return record_recipe_feedback(
        session.get("raw_prompt") or "",
        recipe,
        "clarification_answered",
        {
            "session_id": session_id,
            "answers": session.get("answers") or [],
            "refined_request_context": session.get("refined_request_context") or {},
            "status": session.get("status"),
            "clarification_defaults_upserted": default_count,
        },
        schema_name=schema_name,
    )


def learn_from_adjustment_packet(adjusted_packet_folder: str | Path, schema_name: str = "automap") -> dict[str, Any]:
    """Record a local adjustment packet as feedback."""
    packet_path = Path(adjusted_packet_folder)
    recipe = _load_json(packet_path / "adjusted_recipe.json", {})
    adjustments = _load_json(packet_path / "applied_adjustments.json", {})
    if not recipe:
        raise FileNotFoundError(f"adjusted_recipe.json not found in {packet_path}")
    return record_recipe_feedback(
        recipe.get("user_intent") or (recipe.get("parsed_request") or {}).get("raw_prompt") or "",
        recipe,
        "manual_adjustment",
        {"adjustments": adjustments, "adjusted_packet_folder": str(packet_path)},
        source_packet_path=packet_path,
        schema_name=schema_name,
    )


def recent_feedback(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """Return recent feedback events for UI display."""
    return list_feedback(limit=limit, schema_name=schema_name)
