"""Build safe table recipes from verified catalog metadata."""

from __future__ import annotations

from typing import Any

from app.field_profiler import load_field_profiles
from app.layer_catalog_store import load_catalog_records
from app.table_request_classifier import classify_table_request
from app.table_request_models import table_recipe_shell
from app.table_safety import MAX_FIELDS, evaluate_table_safety


FIELD_PREFERENCES = {
    "parcel_table": ["pin", "pin14", "parcel", "address", "situs", "site", "municip", "district", "acre", "area", "zoning"],
    "permit_table": ["permit", "type", "date", "status", "address", "parcel", "pin", "year"],
    "planning_case_table": ["case", "planning", "rezoning", "status", "date", "address", "parcel", "pin"],
    "zoning_table": ["zone", "zoning", "description", "category", "municip", "area", "acre"],
    "historical_table": ["year", "permit", "parcel", "pin", "address", "zone", "zoning"],
    "attribute_table": [],
}


def _text_blob(record: dict[str, Any]) -> str:
    return " ".join(
        str(record.get(key) or "")
        for key in ("layer_key", "layer_name", "service_name", "category", "canonical_topic", "aliases", "planning_use_cases", "source_status")
    ).lower()


def _layer_score(record: dict[str, Any], intent: str, prompt: str, historical_year: int | None) -> int:
    blob = _text_blob(record)
    prompt_text = prompt.lower()
    score = 0
    if record.get("is_verified"):
        score += 10
    if intent == "parcel_table" and "parcel" in blob:
        score += 40
    if intent == "permit_table" and "permit" in blob:
        score += 40
    if intent == "planning_case_table" and any(word in blob for word in ("planning", "case", "rezoning")):
        score += 40
    if intent == "zoning_table" and "zoning" in blob:
        score += 40
    if "parcel" in prompt_text and "parcel" in blob:
        score += 35
    if "permit" in prompt_text and "permit" in blob:
        score += 35
    if any(word in prompt_text for word in ("zoning", "zone")) and "zoning" in blob:
        score += 35
    if any(word in prompt_text for word in ("planning", "case", "rezoning")) and any(word in blob for word in ("planning", "case", "rezoning")):
        score += 35
    if "zoning" in prompt_text and not any(place in prompt_text for place in ("concord", "kannapolis", "harrisburg", "locust", "midland", "pleasant")):
        if "cabarruscounty" in blob or "county_zoning" in blob or "countyzoning" in blob:
            score += 15
    if historical_year:
        if record.get("is_historical") or "historical" in blob or "legacy" in blob:
            score += 25
        if str(historical_year) in blob or record.get("historical_year") == historical_year:
            score += 30
    elif record.get("is_historical") or "legacy" in str(record.get("source_status") or "").lower():
        score -= 25
    for token in prompt.lower().split():
        if len(token) > 3 and token.strip(".,") in blob:
            score += 1
    if "anno" in blob:
        score -= 30
    return score


def _select_layers(prompt: str, intent: str, catalog: list[dict[str, Any]], historical_year: int | None) -> list[dict[str, Any]]:
    def eligible(record: dict[str, Any]) -> bool:
        if not record.get("is_public", True):
            return False
        if record.get("is_active", True):
            return True
        if historical_year and record.get("is_verified") and (record.get("is_historical") or record.get("historical_year")):
            return True
        return False

    scored = [
        (_layer_score(record, intent, prompt, historical_year), record)
        for record in catalog
        if eligible(record)
    ]
    selected = [record for score, record in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]
    if intent == "permit_table" and not historical_year:
        selected = [record for record in selected if not record.get("is_historical")]
    if historical_year:
        selected = [
            record
            for record in selected
            if record.get("historical_year") == historical_year or str(historical_year) in _text_blob(record)
        ]
    prompt_text = prompt.lower()
    if historical_year and "parcel" in prompt_text and any(word in prompt_text for word in ("zoning", "zone")):
        diversified: list[dict[str, Any]] = []
        for topic in ("parcel", "zoning"):
            match = next((record for record in selected if topic in _text_blob(record)), None)
            if match and match not in diversified:
                diversified.append(match)
        if diversified:
            for record in selected:
                if len(diversified) >= 2:
                    break
                if record not in diversified:
                    diversified.append(record)
            return diversified[:2]
    if historical_year and "permit" in prompt_text:
        permit_match = next((record for record in selected if "permit" in _text_blob(record)), None)
        if permit_match:
            return [permit_match]
    if intent == "parcel_table" and not any(word in prompt_text for word in ("zoning", "zone", "flood", "school", "district", "context")):
        parcel_match = next((record for record in selected if record.get("category") == "parcel" or "parcel" in _text_blob(record)), None)
        if parcel_match:
            return [parcel_match]
    return selected[:2]


def _field_candidates(layer: dict[str, Any], profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    profile_names = {str(profile.get("field_name") or "").lower() for profile in profiles}
    fields: list[dict[str, Any]] = []
    for profile in profiles:
        name = str(profile.get("field_name") or "").strip()
        if name:
            fields.append({"name": name, "alias": profile.get("field_alias") or profile.get("alias") or name, "source": "field_profile"})
    for field in layer.get("fields") or []:
        if not isinstance(field, dict):
            continue
        name = str(field.get("name") or "").strip()
        if name and name.lower() not in profile_names:
            fields.append({"name": name, "alias": field.get("alias") or name, "source": "catalog_fields"})
    return fields


def choose_fields(layer: dict[str, Any], intent: str, profiles: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    preferences = FIELD_PREFERENCES.get(intent) or FIELD_PREFERENCES.get("attribute_table") or []
    candidates = _field_candidates(layer, profiles or [])
    if not candidates:
        return []
    ranked: list[tuple[int, dict[str, Any]]] = []
    for field in candidates:
        blob = f"{field.get('name')} {field.get('alias')}".lower()
        score = 0
        for rank, pref in enumerate(preferences):
            if pref in blob:
                score += 100 - rank
        if "owner" in blob:
            score -= 40
        ranked.append((score, field))
    chosen = [field for score, field in sorted(ranked, key=lambda item: item[0], reverse=True) if score > 0]
    if not chosen:
        chosen = candidates[: min(MAX_FIELDS, 12)]
    return chosen[:MAX_FIELDS]


def _title(prompt: str, intent: str, historical_year: int | None) -> str:
    if historical_year and "permit" in prompt.lower():
        return f"Historical Permits Table ({historical_year})"
    if intent == "parcel_table":
        return "Parcel Table"
    if intent == "permit_table":
        return "Permit Table"
    if intent == "planning_case_table":
        return "Planning Cases Table"
    if intent == "zoning_table":
        return "Zoning Records Table"
    return "AutoMap Attribute Table"


def _geography_filter(prompt: str) -> str | None:
    for geography in ("concord", "kannapolis", "harrisburg", "cabarrus county"):
        if geography in prompt.lower():
            return geography.title()
    return None


def _where_clauses(prompt: str, geography: str | None, historical_year: int | None) -> list[dict[str, Any]]:
    clauses: list[dict[str, Any]] = []
    if geography:
        clauses.append({"type": "geography", "label": geography, "where": "review_required_geography_filter"})
    if historical_year:
        clauses.append({"type": "time", "label": str(historical_year), "where": f"historical_year = {historical_year}"})
    if "100-year flood" in prompt.lower() or "100 year flood" in prompt.lower():
        clauses.append({"type": "context", "label": "100-year floodplain", "where": "requires bounded spatial/table refinement"})
    return clauses


def build_table_recipe(prompt: str, layer_catalog: list[dict[str, Any]] | None = None, schema_name: str = "automap") -> dict[str, Any]:
    classification = classify_table_request(prompt)
    intent = str(classification.get("primary_intent") or "unsupported_table_request")
    historical_year = classification.get("historical_year")
    recipe = table_recipe_shell(prompt, intent, _title(prompt, intent, historical_year))
    recipe["classification"] = classification
    recipe["historical_year"] = historical_year
    recipe["geography_filter"] = _geography_filter(prompt)
    recipe["where_clauses"] = _where_clauses(prompt, recipe["geography_filter"], historical_year)

    catalog = layer_catalog if layer_catalog is not None else load_catalog_records(schema_name)
    layers = _select_layers(prompt, intent, catalog, historical_year)
    if intent == "permit_table" and not historical_year:
        recipe["missing_data_needed"].append("current_permits")
        recipe["warnings"].append("Official current permit source is unresolved; AutoMap will not invent a permit table.")
    if not layers:
        recipe["safety_status"] = "needs_review"
        recipe["blocked_reasons"].append("No verified catalog layer matched this table request.")
        return recipe

    profiles = load_field_profiles([str(layer["layer_key"]) for layer in layers if layer.get("layer_key")], schema_name=schema_name)
    selected_fields: list[dict[str, Any]] = []
    source_layers: list[dict[str, Any]] = []
    for layer in layers:
        layer_key = str(layer.get("layer_key"))
        fields = choose_fields(layer, intent, profiles.get(layer_key, []))
        source_layers.append(
            {
                "layer_key": layer_key,
                "layer_name": layer.get("layer_name"),
                "category": layer.get("category"),
                "source_status": layer.get("source_status"),
                "approval_status": layer.get("approval_status"),
                "is_historical": bool(layer.get("is_historical")),
                "historical_year": layer.get("historical_year"),
                "layer_url": layer.get("layer_url"),
                "record_count": layer.get("record_count"),
                "returnGeometry": False,
            }
        )
        for field in fields:
            selected_fields.append({"layer_key": layer_key, **field})

    recipe["source_layers"] = source_layers
    recipe["selected_fields"] = selected_fields[:MAX_FIELDS]
    estimate = sum(int(layer.get("record_count") or 0) for layer in source_layers)
    recipe["estimated_count"] = estimate
    decision = evaluate_table_safety(estimate, len(recipe["selected_fields"]))
    recipe.update(decision.as_dict())
    if historical_year:
        recipe["warnings"].append("Historical/legacy table request; review source currency and schema before official use.")
    if len(source_layers) > 1:
        recipe["warnings"].append("Multiple source layers selected; AutoMap will not pretend a joined table exists without a verified join key.")
    return recipe
