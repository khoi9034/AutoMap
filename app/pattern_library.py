"""Approved pattern library for deterministic AutoMap feedback learning."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.db import _quote_identifier, get_engine
from app.layer_semantics import slugify
from app.prompt_parser import parse_prompt


PATTERN_COLUMNS = {
    "pattern_key": "text UNIQUE",
    "source_approved_packet": "text",
    "raw_prompt": "text",
    "normalized_prompt": "text",
    "primary_intent": "text",
    "secondary_intents": "jsonb DEFAULT '[]'::jsonb",
    "geographies": "jsonb DEFAULT '[]'::jsonb",
    "topics": "jsonb DEFAULT '[]'::jsonb",
    "selected_layer_keys": "jsonb DEFAULT '[]'::jsonb",
    "rejected_layer_keys": "jsonb DEFAULT '[]'::jsonb",
    "preferred_layer_keys": "jsonb DEFAULT '[]'::jsonb",
    "avoided_layer_keys": "jsonb DEFAULT '[]'::jsonb",
    "spatial_operations": "jsonb DEFAULT '[]'::jsonb",
    "filter_plan": "jsonb DEFAULT '{}'::jsonb",
    "clarification_answers": "jsonb DEFAULT '[]'::jsonb",
    "reviewer_notes": "jsonb DEFAULT '[]'::jsonb",
    "accepted_assumptions": "jsonb DEFAULT '[]'::jsonb",
    "warning_resolutions": "jsonb DEFAULT '{}'::jsonb",
    "missing_data_decisions": "jsonb DEFAULT '[]'::jsonb",
    "confidence_score": "numeric",
    "approval_decision": "text",
    "final_publish_ready": "boolean",
    "usage_count": "integer DEFAULT 0",
    "is_active": "boolean DEFAULT true",
    "created_at": "timestamptz DEFAULT now()",
    "updated_at": "timestamptz DEFAULT now()",
}

DEFAULT_COLUMNS = {
    "default_key": "text UNIQUE",
    "intent": "text",
    "topic": "text",
    "question_type": "text",
    "question_text": "text",
    "default_answer": "jsonb DEFAULT '{}'::jsonb",
    "answer_label": "text",
    "source_pattern_key": "text",
    "confidence_score": "numeric",
    "usage_count": "integer DEFAULT 0",
    "is_active": "boolean DEFAULT true",
    "created_at": "timestamptz DEFAULT now()",
    "updated_at": "timestamptz DEFAULT now()",
}

FEEDBACK_COLUMNS = {
    "raw_prompt": "text",
    "recipe_json": "jsonb DEFAULT '{}'::jsonb",
    "feedback_type": "text",
    "feedback_json": "jsonb DEFAULT '{}'::jsonb",
    "source_packet_path": "text",
    "created_at": "timestamptz DEFAULT now()",
}


def _qualified(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def _json_text(value: Any) -> str:
    return json.dumps(value, default=str)


def _load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonb(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _layer_keys(layers: list[Any]) -> list[str]:
    keys: list[str] = []
    for layer in layers:
        if isinstance(layer, dict):
            key = layer.get("layer_key") or layer.get("id")
            if key:
                keys.append(str(key))
    return sorted(dict.fromkeys(keys))


def _question_topic(question_id: str, recipe_topics: list[str]) -> str:
    if "flood" in question_id:
        return "flood"
    if "school" in question_id or "near_distance" in question_id and "schools" in recipe_topics:
        return "schools"
    if "development" in question_id:
        return "development"
    if "commercial" in question_id or "zoning" in question_id:
        return "zoning"
    if "recent" in question_id:
        return "time"
    return recipe_topics[0] if recipe_topics else "general"


def _question_type(question_id: str, answer_value: Any) -> str:
    if question_id in {"near_distance"}:
        return "distance"
    if question_id in {"flood_layer_scope", "commercial_zoning_codes", "suitability_priorities"}:
        return "multi_choice"
    if question_id in {"recent_time_range"}:
        return "date_range"
    if question_id in {"historical_year"}:
        return "year"
    if isinstance(answer_value, list):
        return "multi_choice"
    return "single_choice"


def _question_text(question_id: str) -> str:
    return {
        "near_distance": "What distance should count as near?",
        "recent_time_range": "What time range should count as recent?",
        "flood_layer_scope": "Which flood hazard layers should be included?",
        "commercial_zoning_codes": "Which zoning codes should count as commercial?",
        "missing_development_data_decision": "How should AutoMap handle missing current development activity data?",
        "suitability_priorities": "Which factors should AutoMap prioritize for suitability?",
        "historical_year": "Which historical year or archive period should be compared?",
    }.get(question_id, question_id.replace("_", " ").title())


def _row_to_pattern(row: dict[str, Any]) -> dict[str, Any]:
    json_fields = {
        "secondary_intents": [],
        "geographies": [],
        "topics": [],
        "selected_layer_keys": [],
        "rejected_layer_keys": [],
        "preferred_layer_keys": [],
        "avoided_layer_keys": [],
        "spatial_operations": [],
        "filter_plan": {},
        "clarification_answers": [],
        "reviewer_notes": [],
        "accepted_assumptions": [],
        "warning_resolutions": {},
        "missing_data_decisions": [],
    }
    converted = dict(row)
    for field, fallback in json_fields.items():
        converted[field] = _load_jsonb(converted.get(field), fallback)
    if converted.get("confidence_score") is not None:
        converted["confidence_score"] = float(converted["confidence_score"])
    converted["created_at"] = str(converted.get("created_at") or "")
    converted["updated_at"] = str(converted.get("updated_at") or "")
    return converted


def _row_to_default(row: dict[str, Any]) -> dict[str, Any]:
    converted = dict(row)
    converted["default_answer"] = _load_jsonb(converted.get("default_answer"), {})
    if converted.get("confidence_score") is not None:
        converted["confidence_score"] = float(converted["confidence_score"])
    converted["created_at"] = str(converted.get("created_at") or "")
    converted["updated_at"] = str(converted.get("updated_at") or "")
    return converted


def init_pattern_tables(schema_name: str = "automap") -> None:
    """Create or safely update local approved-pattern tables."""
    schema = _quote_identifier(schema_name)
    pattern_table = _qualified(schema_name, "approved_pattern_library")
    default_table = _qualified(schema_name, "clarification_defaults")
    feedback_table = _qualified(schema_name, "recipe_feedback_log")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        for table_name, columns in (
            (pattern_table, PATTERN_COLUMNS),
            (default_table, DEFAULT_COLUMNS),
            (feedback_table, FEEDBACK_COLUMNS),
        ):
            connection.execute(text(f"CREATE TABLE IF NOT EXISTS {table_name} (id serial PRIMARY KEY);"))
            for column, column_type in columns.items():
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS approved_pattern_library_key_uidx ON {pattern_table} (pattern_key);"))
        connection.execute(text(f"CREATE UNIQUE INDEX IF NOT EXISTS clarification_defaults_key_uidx ON {default_table} (default_key);"))
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS recipe_feedback_log_created_idx ON {feedback_table} (created_at DESC);"))


def extract_pattern_from_approved_packet(approved_packet_folder: str | Path) -> dict[str, Any]:
    """Extract one deterministic pattern from an approved local packet."""
    packet_path = Path(approved_packet_folder)
    recipe = _load_json(packet_path / "approved_recipe.json", {})
    receipt = _load_json(packet_path / "approval_receipt.json", {})
    approval_file = _load_json(packet_path / "approval_file.json", {})
    warnings = _load_json(packet_path / "approved_warnings.json", {})
    if not recipe:
        raise FileNotFoundError(f"approved_recipe.json not found in {packet_path}")
    if receipt.get("final_publish_ready") is not True:
        raise ValueError("Only approved packets with final_publish_ready=true can become learned patterns.")

    parsed = recipe.get("parsed_request") or {}
    raw_prompt = recipe.get("user_intent") or parsed.get("raw_prompt") or ""
    if not parsed.get("normalized_prompt"):
        parsed = {**parse_prompt(raw_prompt), **parsed}
    intelligence = recipe.get("request_intelligence") or {}
    analysis_plan = recipe.get("analysis_plan") or {}
    topics = [str(item) for item in parsed.get("topics") or []]
    selected_layer_keys = _layer_keys(recipe.get("selected_layers") or [])
    rejected_layer_keys = _layer_keys(recipe.get("rejected_layers") or [])
    clarification_answers = (recipe.get("clarification") or {}).get("answers") or []
    accepted_assumptions = [
        *[str(item) for item in analysis_plan.get("assumptions") or []],
        *[str(item) for item in receipt.get("accepted_risks") or []],
    ]
    warning_resolutions = {
        "resolved_warnings": receipt.get("resolved_warnings") or [],
        "accepted_warnings": receipt.get("accepted_warnings") or [],
        "kept_non_blocking_warnings": receipt.get("kept_non_blocking_warnings") or [],
        "approved_warnings": warnings,
    }
    key_seed = "|".join([str(packet_path), raw_prompt, str(receipt.get("approved_at") or "")])
    digest = sha1(key_seed.encode("utf-8")).hexdigest()[:10]
    pattern_key = slugify(
        "_".join(
            [
                "approved",
                str(intelligence.get("primary_intent") or "general"),
                *(topics[:2] or ["map"]),
                digest,
            ]
        )
    )[:140]
    return {
        "pattern_key": pattern_key,
        "source_approved_packet": str(packet_path),
        "raw_prompt": raw_prompt,
        "normalized_prompt": parsed.get("normalized_prompt") or raw_prompt.lower(),
        "primary_intent": intelligence.get("primary_intent"),
        "secondary_intents": intelligence.get("secondary_intents") or [],
        "geographies": parsed.get("geography_terms") or [],
        "topics": topics,
        "selected_layer_keys": selected_layer_keys,
        "rejected_layer_keys": rejected_layer_keys,
        "preferred_layer_keys": selected_layer_keys,
        "avoided_layer_keys": rejected_layer_keys,
        "spatial_operations": recipe.get("spatial_operations") or [],
        "filter_plan": recipe.get("filter_plan") or {},
        "clarification_answers": clarification_answers,
        "reviewer_notes": receipt.get("reviewer_notes") or approval_file.get("reviewer_notes") or [],
        "accepted_assumptions": accepted_assumptions,
        "warning_resolutions": warning_resolutions,
        "missing_data_decisions": receipt.get("missing_data_decisions") or approval_file.get("missing_data_decisions") or [],
        "confidence_score": recipe.get("confidence_score"),
        "approval_decision": receipt.get("decision") or approval_file.get("decision"),
        "final_publish_ready": receipt.get("final_publish_ready") is True,
        "usage_count": 0,
        "is_active": True,
    }


def _default_rows_from_pattern(pattern: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    topics = [str(topic) for topic in pattern.get("topics") or []]
    for answer in pattern.get("clarification_answers") or []:
        if not isinstance(answer, dict) or not answer.get("question_id"):
            continue
        question_id = str(answer["question_id"])
        topic = _question_topic(question_id, topics)
        label = answer.get("answer_label") or str(answer.get("answer_value"))
        default_key = slugify(f"{pattern.get('primary_intent') or 'general'}_{topic}_{question_id}_{label}")[:140]
        rows.append(
            {
                "default_key": default_key,
                "intent": pattern.get("primary_intent"),
                "topic": topic,
                "question_type": _question_type(question_id, answer.get("answer_value")),
                "question_text": _question_text(question_id),
                "default_answer": answer.get("answer_value"),
                "answer_label": label,
                "source_pattern_key": pattern.get("pattern_key"),
                "confidence_score": max(float(pattern.get("confidence_score") or 0.75), 0.75),
                "usage_count": 0,
                "is_active": True,
            }
        )
    return rows


def _upsert_clarification_defaults(pattern: dict[str, Any], schema_name: str = "automap") -> int:
    rows = _default_rows_from_pattern(pattern)
    if not rows:
        return 0
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "clarification_defaults")
    engine = get_engine()
    with engine.begin() as connection:
        for row in rows:
            connection.execute(
                text(
                    f"""
                    INSERT INTO {table} (
                        default_key, intent, topic, question_type, question_text,
                        default_answer, answer_label, source_pattern_key,
                        confidence_score, usage_count, is_active, created_at, updated_at
                    )
                    VALUES (
                        :default_key, :intent, :topic, :question_type, :question_text,
                        CAST(:default_answer AS jsonb), :answer_label, :source_pattern_key,
                        :confidence_score, :usage_count, :is_active, now(), now()
                    )
                    ON CONFLICT (default_key) DO UPDATE SET
                        default_answer = EXCLUDED.default_answer,
                        answer_label = EXCLUDED.answer_label,
                        source_pattern_key = EXCLUDED.source_pattern_key,
                        confidence_score = GREATEST(
                            COALESCE({table}.confidence_score, 0),
                            COALESCE(EXCLUDED.confidence_score, 0)
                        ),
                        is_active = true,
                        updated_at = now();
                    """
                ),
                {**row, "default_answer": _json_text(row.get("default_answer"))},
            )
    return len(rows)


def upsert_approved_pattern(pattern: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    """Insert or update one approved pattern and derived clarification defaults."""
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "approved_pattern_library")
    fields = [field for field in PATTERN_COLUMNS if field not in {"created_at", "updated_at"}]
    json_fields = {
        "secondary_intents",
        "geographies",
        "topics",
        "selected_layer_keys",
        "rejected_layer_keys",
        "preferred_layer_keys",
        "avoided_layer_keys",
        "spatial_operations",
        "filter_plan",
        "clarification_answers",
        "reviewer_notes",
        "accepted_assumptions",
        "warning_resolutions",
        "missing_data_decisions",
    }
    insert_columns = ", ".join([*fields, "created_at", "updated_at"])
    placeholders = ", ".join(
        [f"CAST(:{field} AS jsonb)" if field in json_fields else f":{field}" for field in fields]
        + ["now()", "now()"]
    )
    updates = ", ".join(
        f"{field} = EXCLUDED.{field}"
        for field in fields
        if field not in {"pattern_key", "usage_count"}
    )
    params = {
        field: _json_text(pattern.get(field) or ([] if field != "filter_plan" and field != "warning_resolutions" else {}))
        if field in json_fields
        else pattern.get(field)
        for field in fields
    }
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} ({insert_columns})
                VALUES ({placeholders})
                ON CONFLICT (pattern_key) DO UPDATE SET
                    {updates},
                    updated_at = now();
                """
            ),
            params,
        )
    default_count = _upsert_clarification_defaults(pattern, schema_name)
    return {**pattern, "clarification_defaults_upserted": default_count}


def list_patterns(limit: int = 50, include_inactive: bool = False, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List approved patterns for UI/API use."""
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "approved_pattern_library")
    where = "" if include_inactive else "WHERE is_active = true"
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT *
                FROM {table}
                {where}
                ORDER BY updated_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
    return [_row_to_pattern(dict(row)) for row in rows]


def get_pattern(pattern_key: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one approved pattern by key."""
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "approved_pattern_library")
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(f"SELECT * FROM {table} WHERE pattern_key = :pattern_key;"),
            {"pattern_key": pattern_key},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"Approved pattern not found: {pattern_key}")
    return _row_to_pattern(dict(row))


def deactivate_pattern(pattern_key: str, schema_name: str = "automap") -> dict[str, Any]:
    """Mark a pattern inactive without deleting it."""
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "approved_pattern_library")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(f"UPDATE {table} SET is_active = false, updated_at = now() WHERE pattern_key = :pattern_key;"),
            {"pattern_key": pattern_key},
        )
    return get_pattern(pattern_key, schema_name)


def list_clarification_defaults(limit: int = 50, include_inactive: bool = False, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List learned clarification defaults."""
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "clarification_defaults")
    where = "" if include_inactive else "WHERE is_active = true"
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT *
                FROM {table}
                {where}
                ORDER BY usage_count DESC, updated_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
    return [_row_to_default(dict(row)) for row in rows]


def list_feedback(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List recent feedback log rows."""
    init_pattern_tables(schema_name)
    table = _qualified(schema_name, "recipe_feedback_log")
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT id, raw_prompt, feedback_type, feedback_json, source_packet_path, created_at
                FROM {table}
                ORDER BY created_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
    return [
        {
            **dict(row),
            "feedback_json": _load_jsonb(row.get("feedback_json"), {}),
            "created_at": str(row.get("created_at") or ""),
        }
        for row in rows
    ]
