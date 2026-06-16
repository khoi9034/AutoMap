"""Filter planning for AutoMap map recipes."""

from __future__ import annotations

from typing import Any

from app.field_profiler import (
    infer_field_roles,
    load_field_profiles,
    load_value_profiles,
)
from app.layer_catalog_store import load_catalog_records


COMMERCIAL_TERMS = ["commercial", "office", "business", "retail", "industrial", "c-"]


def _field_names(fields: list[dict[str, Any]]) -> list[str]:
    return [field["field_name"] for field in fields if field.get("field_name")]


def _values_for_field(layer: dict[str, Any], field_name: str | None) -> list[Any]:
    if not field_name:
        return []
    profile = layer.get("value_profiles", {}).get(field_name) or {}
    values = profile.get("sample_values") or []
    if values:
        return values
    for field in layer.get("field_profiles", []):
        if field.get("field_name") != field_name:
            continue
        domain = field.get("domain") or {}
        coded_values = domain.get("codedValues") if isinstance(domain, dict) else None
        if coded_values:
            return [item.get("name") or item.get("code") for item in coded_values]
    return []


def _score_field(field: dict[str, Any], preferred_flags: list[str], name_terms: list[str]) -> float:
    score = 0.0
    field_text = f"{field.get('field_name', '')} {field.get('field_alias', '')}".lower()
    for flag in preferred_flags:
        if field.get(flag):
            score += 0.3
    for term in name_terms:
        if term.lower() in field_text:
            score += 0.2
    if field.get("is_object_id") or field.get("is_geometry_field"):
        score -= 0.6
    return max(score, 0.0)


def _choose_field(fields: list[dict[str, Any]], flags: list[str], terms: list[str]) -> tuple[dict[str, Any] | None, float]:
    scored = [
        (field, _score_field(field, flags, terms))
        for field in fields
        if not field.get("is_object_id") and not field.get("is_geometry_field")
    ]
    scored = [item for item in scored if item[1] > 0]
    if not scored:
        return None, 0.0
    scored.sort(key=lambda item: item[1], reverse=True)
    field, score = scored[0]
    return field, min(score, 0.95)


def _escape_value(value: Any) -> str:
    return str(value).replace("'", "''")


def draft_where_clause(layer: dict[str, Any], field: str | dict[str, Any] | None, values_or_terms: list[Any]) -> str | None:
    """Draft a conservative SQL-like ArcGIS where clause from real fields."""
    if not field or not values_or_terms:
        return None
    field_name = field["field_name"] if isinstance(field, dict) else field
    values = [value for value in values_or_terms if value not in {None, ""}]
    if not values:
        return None
    if len(values) == 1:
        return f"{field_name} = '{_escape_value(values[0])}'"
    quoted = ", ".join(f"'{_escape_value(value)}'" for value in values)
    return f"{field_name} IN ({quoted})"


def choose_geography_filter_field(layer: dict[str, Any], parsed_geography: list[dict[str, str]]) -> dict[str, Any]:
    """Choose a jurisdiction/geography field and requested place value."""
    fields = layer.get("field_profiles", [])
    field, confidence = _choose_field(
        fields,
        ["is_geography_candidate", "is_name_candidate"],
        ["city", "municipality", "town", "jurisdiction", "district", "name"],
    )
    requested_names = [geo["name"] for geo in parsed_geography if geo.get("type") not in {"county", "countywide"}]
    candidate_values = _values_for_field(layer, field.get("field_name") if field else None)
    matched_values = [
        value
        for value in candidate_values
        if any(str(value).lower() == name.lower() or name.lower() in str(value).lower() for name in requested_names)
    ]
    values = matched_values or requested_names
    confirmed = bool(matched_values)
    return {
        "candidate_fields": _field_names(fields),
        "selected_field": field.get("field_name") if field else None,
        "candidate_values": candidate_values[:50],
        "draft_where_clause": draft_where_clause(layer, field, values),
        "confidence_score": round(confidence + (0.2 if confirmed else 0), 3),
        "needs_review": not bool(field) or not confirmed,
        "review_reason": None if confirmed else "Confirm geography value exists in selected field samples.",
    }


def choose_date_filter_field(layer: dict[str, Any], parsed_time_reference: list[str]) -> dict[str, Any]:
    """Choose a date field for recent/current temporal filters."""
    fields = layer.get("field_profiles", [])
    field, confidence = _choose_field(fields, ["is_date_candidate"], ["date", "created", "issue", "activity", "year"])
    needs_recent = "recent" in parsed_time_reference
    return {
        "candidate_fields": _field_names(fields),
        "selected_field": field.get("field_name") if field else None,
        "candidate_values": _values_for_field(layer, field.get("field_name") if field else None)[:20],
        "draft_where_clause": None,
        "confidence_score": round(confidence, 3),
        "needs_review": needs_recent,
        "review_reason": "Define recent date range and confirm the correct date field." if needs_recent else None,
    }


def choose_zoning_filter_field(layer: dict[str, Any], zoning_terms: list[str]) -> dict[str, Any]:
    """Choose zoning code/category fields and commercial-like values when possible."""
    fields = layer.get("field_profiles", [])
    field, confidence = _choose_field(fields, ["is_zoning_candidate", "is_category_candidate"], ["zone", "zoning", "district", "code", "class"])
    values = _values_for_field(layer, field.get("field_name") if field else None)
    if not zoning_terms:
        return {
            "candidate_fields": _field_names(fields),
            "selected_field": field.get("field_name") if field else None,
            "candidate_values": values[:50],
            "draft_where_clause": None,
            "confidence_score": round(confidence, 3),
            "needs_review": not bool(field),
            "review_reason": None if field else "No obvious zoning code or classification field found.",
        }
    terms = COMMERCIAL_TERMS if "commercial" in zoning_terms else zoning_terms
    matched_values = [
        value
        for value in values
        if any(term.lower() in str(value).lower() for term in terms)
    ]
    return {
        "candidate_fields": _field_names(fields),
        "selected_field": field.get("field_name") if field else None,
        "candidate_values": values[:50],
        "draft_where_clause": draft_where_clause(layer, field, matched_values),
        "confidence_score": round(confidence + (0.2 if matched_values else 0), 3),
        "needs_review": not bool(matched_values),
        "review_reason": None if matched_values else "Confirm which zoning codes count as commercial.",
    }


def choose_school_filter_field(layer: dict[str, Any], school_terms: list[str]) -> dict[str, Any]:
    """Choose school/district fields when a school layer needs attributes."""
    fields = layer.get("field_profiles", [])
    field, confidence = _choose_field(fields, ["is_school_candidate", "is_name_candidate"], ["school", "district", "attendance", *school_terms])
    values = _values_for_field(layer, field.get("field_name") if field else None)
    return {
        "candidate_fields": _field_names(fields),
        "selected_field": field.get("field_name") if field else None,
        "candidate_values": values[:50],
        "draft_where_clause": None,
        "confidence_score": round(confidence, 3),
        "needs_review": False if field else True,
        "review_reason": None if field else "No obvious school name/district field found.",
    }


def choose_flood_filter(layer: dict[str, Any], flood_terms: list[str]) -> dict[str, Any]:
    """Floodplain sublayers represent flood type, so avoid fake filters."""
    return {
        "candidate_fields": _field_names(layer.get("field_profiles", [])),
        "selected_field": None,
        "candidate_values": [],
        "draft_where_clause": None,
        "confidence_score": 0.9,
        "needs_review": False,
        "review_reason": "No attribute filter needed; selected layer represents the requested flood condition.",
    }


def _field_profiles_from_catalog_records(catalog_records: list[dict[str, Any]], selected_keys: set[str]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in catalog_records:
        if record.get("layer_key") not in selected_keys:
            continue
        profiles = []
        for profile in infer_field_roles(record.get("fields") or []):
            profile.update({"layer_key": record["layer_key"], "layer_url": record.get("layer_url")})
            profiles.append(profile)
        grouped[record["layer_key"]] = profiles
    return grouped


def _context_layers(
    recipe: dict[str, Any],
    catalog_records: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    selected_layers = recipe.get("selected_layers", [])
    selected_keys = [layer["layer_key"] for layer in selected_layers]
    if catalog_records is None:
        field_profiles = load_field_profiles(selected_keys)
        value_profiles = load_value_profiles(selected_keys)
        inferred_profiles = _field_profiles_from_catalog_records(load_catalog_records(), set(selected_keys))
        for layer_key, profiles in inferred_profiles.items():
            if not field_profiles.get(layer_key):
                field_profiles[layer_key] = profiles
    else:
        field_profiles = _field_profiles_from_catalog_records(catalog_records, set(selected_keys))
        value_profiles = {}

    context_layers = []
    for layer in selected_layers:
        layer_key = layer["layer_key"]
        values_by_field = {
            field_name: profile
            for (profile_layer_key, field_name), profile in value_profiles.items()
            if profile_layer_key == layer_key
        }
        context_layers.append(
            {
                **layer,
                "field_profiles": field_profiles.get(layer_key, []),
                "value_profiles": values_by_field,
            }
        )
    return context_layers


def _plan_for_layer(layer: dict[str, Any], parsed_request: dict[str, Any]) -> dict[str, Any]:
    category = layer.get("category")
    role = layer.get("role")
    if category == "flood":
        plan = choose_flood_filter(layer, [parsed_request.get("topic_details", {}).get("flood_frequency")])
    elif category == "zoning":
        plan = choose_zoning_filter_field(layer, parsed_request.get("topic_details", {}).get("zoning_modifiers") or [])
    elif category == "schools":
        plan = choose_school_filter_field(layer, parsed_request.get("topic_details", {}).get("school_levels") or [])
    elif role == "jurisdiction_filter":
        plan = choose_geography_filter_field(layer, parsed_request.get("geography_terms") or [])
    elif "recent" in parsed_request.get("time_references", []):
        plan = choose_date_filter_field(layer, parsed_request.get("time_references") or [])
    else:
        fields = layer.get("field_profiles", [])
        if category == "parcel":
            field, confidence = _choose_field(fields, [], ["pin14", "pin", "parcel", "account", "owner", "property"])
        else:
            field, confidence = _choose_field(fields, ["is_name_candidate"], ["name", "label", "title"])
        plan = {
            "candidate_fields": _field_names(fields),
            "selected_field": field.get("field_name") if field else None,
            "candidate_values": _values_for_field(layer, field.get("field_name") if field else None)[:50],
            "draft_where_clause": None,
            "confidence_score": round(confidence, 3),
            "needs_review": False,
            "review_reason": None,
        }
    return plan


def build_filter_plan(
    recipe: dict[str, Any],
    catalog_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build per-layer filter plans using profiled fields and sampled values."""
    parsed_request = recipe.get("parsed_request", {})
    plan: dict[str, Any] = {}
    for layer in _context_layers(recipe, catalog_records):
        layer_plan = _plan_for_layer(layer, parsed_request)
        plan[layer["layer_key"]] = {
            "layer_name": layer.get("layer_name"),
            "category": layer.get("category"),
            "role": layer.get("role"),
            **layer_plan,
        }
    return plan


def validate_filter_plan(recipe: dict[str, Any]) -> dict[str, Any]:
    """Validate a recipe and its filter plan for review needs."""
    filter_plan = recipe.get("filter_plan") or {}
    warnings: list[str] = []
    for layer_key, layer_plan in filter_plan.items():
        if layer_plan.get("needs_review"):
            reason = layer_plan.get("review_reason") or "Filter plan needs review."
            warnings.append(f"{layer_key}: {reason}")
    for missing in recipe.get("missing_data_needed") or []:
        warnings.append(f"Missing data: {missing}")

    validation = {
        "is_valid": bool(recipe.get("selected_layers")) and not any("Missing data" in warning for warning in warnings),
        "warnings": warnings,
        "filter_plan_layer_count": len(filter_plan),
        "needs_review": bool(warnings),
    }
    return validation
