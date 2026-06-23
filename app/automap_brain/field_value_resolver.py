"""Field/value resolution summaries for AutoMap Brain v2."""

from __future__ import annotations

from typing import Any

from app.filter_planner import build_filter_plan


FIELD_ROLE_KEYWORDS = {
    "zoning_code": ["zone", "zoning", "district", "class"],
    "zoning_description": ["description", "desc", "label"],
    "municipality": ["municipal", "city", "jurisdiction", "town"],
    "parcel_id": ["pin", "pin14", "parcel", "pid"],
    "acreage": ["acre", "area"],
    "flood_type": ["flood", "fld", "zone"],
    "road_class": ["class", "route", "functional", "type", "aadt"],
    "date_year": ["date", "year", "issued", "activity"],
    "permit_status": ["permit", "status", "case"],
}


def infer_field_roles(layer: dict[str, Any]) -> list[dict[str, Any]]:
    roles: list[dict[str, Any]] = []
    for field in layer.get("fields") or []:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or field.get("field_name") or "")
        alias = str(field.get("alias") or field.get("field_alias") or "")
        blob = f"{name} {alias}".lower()
        for role, keywords in FIELD_ROLE_KEYWORDS.items():
            if any(keyword in blob for keyword in keywords):
                roles.append({"field_name": name, "field_alias": alias or name, "role": role, "confidence": 0.72})
                break
    return roles


def resolve_field_values(recipe: dict[str, Any], catalog_records: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    filter_plan = recipe.get("filter_plan") or build_filter_plan(recipe, catalog_records=catalog_records)
    return {
        "filter_plan": filter_plan,
        "field_roles": {layer.get("layer_key"): infer_field_roles(layer) for layer in recipe.get("selected_layers") or [] if isinstance(layer, dict)},
        "warnings": filter_plan.get("warnings") or [],
    }
