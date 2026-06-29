"""Optional AI MapPlan planner, validated before deterministic execution."""

from __future__ import annotations

from typing import Any

from app.ai.map_plan_validator import MapPlanValidationError, map_plan_to_request_plan, validate_map_plan
from app.ai.openai_client import ai_settings_from_env, request_structured_map_plan
from app.automap_brain.ontology import kernel_ontology


def _catalog_summary(catalog_records: list[dict[str, Any]] | None = None, limit: int = 30) -> list[dict[str, Any]]:
    rows = catalog_records or []
    summary: list[dict[str, Any]] = []
    for row in rows[:limit]:
        summary.append(
            {
                "title": row.get("layer_name"),
                "domain": row.get("category") or row.get("canonical_topic"),
                "geometry": row.get("geometry_type"),
                "verified": bool(row.get("is_verified")),
                "fields": [
                    str(field.get("name") or field.get("alias"))
                    for field in (row.get("fields") or [])[:8]
                    if isinstance(field, dict)
                ],
            }
        )
    return summary


def _planner_messages(prompt: str, catalog_records: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    ontology = kernel_ontology()
    compact_context = {
        "scope": ontology["scope"],
        "request_types": ontology["request_types"],
        "output_modes": ["map", "table", "route", "report", "map_and_table"],
        "domains": sorted(ontology["domains"].keys()),
        "municipalities": sorted({meta["name"] for meta in ontology["place_aliases"].values()}),
        "unsupported_places": ontology["out_of_scope_places"],
        "layer_summaries": _catalog_summary(catalog_records),
    }
    return [
        {
            "role": "system",
            "content": (
                "You are AutoMap's GIS request planner for Cabarrus County, NC. "
                "Return only strict JSON matching the MapPlan schema. Do not output SQL, raw URLs, "
                "owner/name field searches, arbitrary data sources, or publishing instructions. "
                "Plan primary results, supporting context, AOI, safe spatial operations, and fallback truth. "
                "AutoMap's deterministic backend will validate and execute only approved operations."
            ),
        },
        {"role": "user", "content": f"Catalog context: {compact_context}\nUser request: {prompt}"},
    ]


def plan_with_ai(prompt: str, catalog_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return safe planner metadata and a deterministic request-plan override when valid."""
    settings = ai_settings_from_env()
    if not settings.enabled:
        return {"planner_used": "deterministic", "ai_status": "disabled", "request_plan": None}
    result = request_structured_map_plan(_planner_messages(prompt, catalog_records), settings)
    if result.get("ai_status") != "ok":
        return {
            "planner_used": "fallback" if settings.fallback_to_deterministic else "deterministic",
            "ai_status": result.get("ai_status") or "unavailable",
            "ai_error_category": result.get("error_category"),
            "request_plan": None,
        }
    try:
        plan = validate_map_plan(result.get("plan") or {})
        request_plan = map_plan_to_request_plan(plan)
    except MapPlanValidationError as exc:
        return {
            "planner_used": "fallback",
            "ai_status": "invalid",
            "ai_error_category": str(exc),
            "request_plan": None,
        }
    return {
        "planner_used": "ai",
        "ai_status": "ok",
        "ai_confidence": plan.get("confidence"),
        "map_plan": plan,
        "map_plan_summary": {
            "interpreted_request": plan.get("user_intent_summary"),
            "main_operation": ", ".join(plan.get("spatial_operations") or []),
            "primary_result": plan.get("result_expectation"),
            "context_layers": [
                item.get("domain")
                for item in plan.get("context_layers") or []
                if isinstance(item, dict) and item.get("domain")
            ],
            "fallback_strategy": plan.get("fallback_strategy"),
        },
        "request_plan": request_plan,
    }

