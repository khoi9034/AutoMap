"""Validate AI MapPlan JSON before deterministic execution."""

from __future__ import annotations

from typing import Any
import re

from app.ai.map_plan_schema import ALLOWED_DOMAINS, LAYER_ROLES, OUTPUT_MODES, SPATIAL_OPERATIONS
from app.automap_brain.domain_ontology import OUT_OF_SCOPE_PLACES, SUPPORTED_SCOPE
from app.automap_brain.request_parser import build_brain_plan


REQUEST_TYPES = {
    "proximity",
    "floodplain_screening",
    "zoning_context",
    "parcel_screening",
    "table_request",
    "development_activity",
    "suitability",
    "historical_lookup",
    "general_map",
    "unsupported_area",
    "unsupported_request",
}
DOMAIN_MAP = {
    "addresses": "address_proximity",
    "roads": "transportation",
    "facilities": "address_proximity",
    "boundaries": "jurisdiction",
}
RAW_URL_RE = re.compile(r"https?://", re.IGNORECASE)
SQL_RE = re.compile(r"\b(select|insert|update|delete|drop|alter|truncate|create)\b", re.IGNORECASE)
OWNER_FIELD_RE = re.compile(r"\b(owner|name)\b", re.IGNORECASE)


class MapPlanValidationError(ValueError):
    """Raised when an AI plan asks for something AutoMap will not execute."""


def _walk_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        strings: list[str] = []
        for item in value:
            strings.extend(_walk_strings(item))
        return strings
    if isinstance(value, dict):
        strings = []
        for item in value.values():
            strings.extend(_walk_strings(item))
        return strings
    return []


def _planned_domains(plan: dict[str, Any]) -> list[str]:
    domains: list[str] = []
    for group in ("target_layers", "context_layers"):
        for layer in plan.get(group) or []:
            if isinstance(layer, dict) and layer.get("domain"):
                domains.append(str(layer["domain"]))
    return domains


def _planned_roles(plan: dict[str, Any]) -> list[str]:
    roles: list[str] = []
    for group in ("target_layers", "context_layers", "cartography_roles"):
        for item in plan.get(group) or []:
            if isinstance(item, dict) and item.get("role"):
                roles.append(str(item["role"]))
            elif isinstance(item, str):
                roles.append(item)
    return roles


def validate_map_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Return a sanitized MapPlan or raise a safe validation error."""
    if not isinstance(plan, dict):
        raise MapPlanValidationError("AI plan was not a JSON object.")
    request_type = str(plan.get("request_type") or "")
    if request_type not in REQUEST_TYPES:
        raise MapPlanValidationError("AI plan used an unsupported request type.")
    if str(plan.get("output_mode") or "") not in OUTPUT_MODES:
        raise MapPlanValidationError("AI plan used an unsupported output mode.")
    operations = [str(item) for item in plan.get("spatial_operations") or []]
    if any(operation not in SPATIAL_OPERATIONS for operation in operations):
        raise MapPlanValidationError("AI plan used an unsupported spatial operation.")
    domains = _planned_domains(plan)
    if any(domain not in ALLOWED_DOMAINS for domain in domains):
        raise MapPlanValidationError("AI plan referenced an unknown data domain.")
    roles = _planned_roles(plan)
    if any(role not in LAYER_ROLES for role in roles):
        raise MapPlanValidationError("AI plan referenced an unknown layer role.")
    strings = _walk_strings(plan)
    if any(RAW_URL_RE.search(text) for text in strings):
        raise MapPlanValidationError("AI plan included a raw URL.")
    if any(SQL_RE.search(text) for text in strings):
        raise MapPlanValidationError("AI plan included SQL-like text.")
    for layer in [*(plan.get("target_layers") or []), *(plan.get("context_layers") or [])]:
        if not isinstance(layer, dict):
            raise MapPlanValidationError("AI layer entries must be objects.")
        for field_key in ("filter_intent", "preferred_source_hint"):
            if OWNER_FIELD_RE.search(str(layer.get(field_key) or "")):
                raise MapPlanValidationError("AI plan referenced owner/name fields.")
    geography_blob = " ".join(_walk_strings({"geography": plan.get("geography"), "aoi": plan.get("aoi")})).lower()
    if any(place in geography_blob for place in OUT_OF_SCOPE_PLACES) and request_type != "unsupported_area":
        raise MapPlanValidationError("AI plan kept an out-of-county request in scope.")
    if plan.get("cabarrus_scope_check") == "out_of_scope" and request_type != "unsupported_area":
        raise MapPlanValidationError("AI plan scope check conflicts with request type.")
    return plan


def map_plan_to_request_plan(plan: dict[str, Any]) -> dict[str, Any]:
    """Adapt a validated MapPlan to the deterministic brain's request-plan shape."""
    request_type = str(plan.get("request_type") or "general_map")
    normalized = str(plan.get("normalized_prompt") or "")
    request_plan = build_brain_plan(normalized or str(plan.get("user_intent_summary") or ""))
    domains = [DOMAIN_MAP.get(domain, domain) for domain in _planned_domains(plan)]
    primary_domain = domains[0] if domains else request_plan.get("primary_domain")
    secondary_domains = [domain for domain in domains[1:] if domain != primary_domain]
    operations = [str(item) for item in plan.get("spatial_operations") or []]
    geography = plan.get("geography") if isinstance(plan.get("geography"), dict) else {}
    geography_name = geography.get("name") or geography.get("geography_name") or request_plan.get("geography")
    geography_type = geography.get("type") or geography.get("geography_type") or request_plan.get("geography_type")
    request_plan.update(
        {
            "brain_version": "automap_ai_planner_v1",
            "ai_plan": plan,
            "normalized_prompt": normalized or request_plan.get("normalized_prompt"),
            "request_type": request_type,
            "confidence": float(plan.get("confidence") or request_plan.get("confidence") or 0),
            "geography": geography_name,
            "geography_type": geography_type,
            "output_mode": plan.get("output_mode") or request_plan.get("output_mode"),
            "primary_domain": primary_domain,
            "secondary_domains": secondary_domains,
            "spatial_relationships": [
                "intersects" if operation == "intersect" else
                "near_or_around" if operation == "near" else
                "excluding" if operation == "avoid" else
                operation
                for operation in operations
            ],
            "safety_notes": [
                *[str(item) for item in plan.get("safety_notes") or [] if item],
                f"Validated against AutoMap catalog/domain whitelist for {SUPPORTED_SCOPE}.",
                "Real ArcGIS publishing is disabled.",
            ],
            "ai_validated": True,
        }
    )
    if request_type == "floodplain_screening":
        request_plan["primary_domain"] = "parcels"
        if "floodplain" not in request_plan["secondary_domains"]:
            request_plan["secondary_domains"].append("floodplain")
        request_plan["result_layer"] = "affected_parcels"
        request_plan["constraint_domain"] = "floodplain"
    if request_type == "zoning_context" and "commercial" in normalized.lower():
        request_plan["zoning_category"] = "commercial"
    if request_type == "proximity" and "closest_by_road" in operations:
        request_plan["spatial_relationships"] = ["closest_by_road"]
    return request_plan

