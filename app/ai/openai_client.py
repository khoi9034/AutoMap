"""Small OpenAI wrapper for structured planner calls."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any

from app.ai.map_plan_schema import MAP_PLAN_SCHEMA


@dataclass(frozen=True)
class AISettings:
    enabled: bool
    provider: str
    model: str
    timeout_seconds: float
    max_retries: int
    planner_mode: str
    fallback_to_deterministic: bool
    api_key_present: bool


def ai_settings_from_env() -> AISettings:
    return AISettings(
        enabled=os.getenv("AUTOMAP_AI_ENABLED", "false").lower() == "true",
        provider=os.getenv("AUTOMAP_AI_PROVIDER", "openai"),
        model=os.getenv("AUTOMAP_AI_MODEL", "gpt-5.5"),
        timeout_seconds=float(os.getenv("AUTOMAP_AI_TIMEOUT_SECONDS", "20") or 20),
        max_retries=int(os.getenv("AUTOMAP_AI_MAX_RETRIES", "1") or 1),
        planner_mode=os.getenv("AUTOMAP_AI_PLANNER_MODE", "structured_map_plan"),
        fallback_to_deterministic=os.getenv("AUTOMAP_AI_FALLBACK_TO_DETERMINISTIC", "true").lower() != "false",
        api_key_present=bool(os.getenv("OPENAI_API_KEY")),
    )


def request_structured_map_plan(messages: list[dict[str, str]], settings: AISettings | None = None) -> dict[str, Any]:
    """Call OpenAI for strict JSON. Returns a status dict; never raises secrets."""
    loaded = settings or ai_settings_from_env()
    if not loaded.enabled or loaded.provider != "openai":
        return {"ai_status": "disabled", "plan": None}
    if not loaded.api_key_present:
        return {"ai_status": "unavailable", "error_category": "missing_api_key", "plan": None}
    try:
        from openai import OpenAI
    except Exception:
        return {"ai_status": "unavailable", "error_category": "openai_sdk_missing", "plan": None}

    try:
        client = OpenAI(timeout=loaded.timeout_seconds, max_retries=loaded.max_retries)
        response = client.responses.create(
            model=loaded.model,
            input=messages,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "automap_map_plan",
                    "schema": MAP_PLAN_SCHEMA,
                    "strict": True,
                }
            },
        )
        raw = getattr(response, "output_text", None)
        if not raw:
            raw = response.model_dump_json()
        plan = json.loads(raw)
        return {"ai_status": "ok", "plan": plan}
    except Exception as exc:  # pragma: no cover - network/SDK safety wrapper
        return {"ai_status": "unavailable", "error_category": type(exc).__name__, "plan": None}

