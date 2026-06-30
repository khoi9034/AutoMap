"""Small OpenAI wrapper for structured planner calls."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any

from app.ai.map_plan_schema import MAP_PLAN_SCHEMA


@dataclass(frozen=True)
class AISettings:
    enabled: bool
    provider: str
    model: str
    fallback_model: str | None
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
        fallback_model=os.getenv("AUTOMAP_AI_MODEL_FALLBACK") or None,
        timeout_seconds=float(os.getenv("AUTOMAP_AI_TIMEOUT_SECONDS", "20") or 20),
        max_retries=int(os.getenv("AUTOMAP_AI_MAX_RETRIES", "1") or 1),
        planner_mode=os.getenv("AUTOMAP_AI_PLANNER_MODE", "structured_map_plan"),
        fallback_to_deterministic=os.getenv("AUTOMAP_AI_FALLBACK_TO_DETERMINISTIC", "true").lower() != "false",
        api_key_present=bool(os.getenv("OPENAI_API_KEY")),
    )


def _safe_error(exc: Exception) -> dict[str, Any]:
    body = getattr(exc, "body", None) or {}
    if not isinstance(body, dict):
        body = {}
    error = body.get("error") if isinstance(body.get("error"), dict) else body
    message = str(error.get("message") or getattr(exc, "message", None) or exc)
    message = re.sub(r"sk-[A-Za-z0-9_-]+", "[redacted]", message)
    message = re.sub(r"Bearer\s+[A-Za-z0-9._-]+", "Bearer [redacted]", message)
    return {
        "error_category": type(exc).__name__,
        "error_status_code": getattr(exc, "status_code", None),
        "error_code": error.get("code"),
        "error_type": error.get("type"),
        "error_message_safe": message[:500],
    }


def _is_model_access_error(error: dict[str, Any]) -> bool:
    blob = " ".join(str(error.get(key) or "") for key in ("error_code", "error_type", "error_message_safe")).lower()
    return "model" in blob and any(term in blob for term in ("not found", "does not exist", "access", "permission", "unsupported"))


def _create_response(client: Any, model: str, messages: list[dict[str, str]]) -> Any:
    return client.responses.create(
        model=model,
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
        model_used = loaded.model
        try:
            response = _create_response(client, model_used, messages)
        except Exception as exc:
            first_error = _safe_error(exc)
            if loaded.fallback_model and _is_model_access_error(first_error):
                model_used = loaded.fallback_model
                response = _create_response(client, model_used, messages)
            else:
                return {"ai_status": "unavailable", "plan": None, **first_error}
        raw = getattr(response, "output_text", None)
        if not raw:
            raw = response.model_dump_json()
        plan = json.loads(raw)
        return {"ai_status": "ok", "model_used": model_used, "plan": plan}
    except Exception as exc:  # pragma: no cover - network/SDK safety wrapper
        return {"ai_status": "unavailable", "plan": None, **_safe_error(exc)}


def _diagnose() -> int:
    settings = ai_settings_from_env()
    report: dict[str, Any] = {
        "ai_enabled": settings.enabled,
        "provider": settings.provider,
        "model": settings.model,
        "fallback_model_configured": bool(settings.fallback_model),
        "api_key_present": settings.api_key_present,
    }
    if not settings.api_key_present:
        print(json.dumps({**report, "ai_status": "unavailable", "error_category": "missing_api_key"}, indent=2))
        return 1
    result = request_structured_map_plan(
        [
            {"role": "system", "content": "Return a minimal valid AutoMap MapPlan JSON only."},
            {"role": "user", "content": "commercial zoning around Concord"},
        ],
        settings,
    )
    safe_result = {key: value for key, value in result.items() if key != "plan"}
    print(json.dumps({**report, **safe_result}, indent=2))
    return 0 if result.get("ai_status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(_diagnose())
