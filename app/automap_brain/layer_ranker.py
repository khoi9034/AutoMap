"""Semantic layer ranking for AutoMap Brain v2."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


CATEGORY_BY_DOMAIN = {
    "parcels": {"parcel"},
    "zoning": {"zoning"},
    "floodplain": {"flood"},
    "transportation": {"transportation", "traffic", "transportation_projects"},
    "development_activity": {"development", "planning", "permit", "permits", "planning_cases", "development_activity_proxy"},
    "historical_layers": {"parcel", "zoning", "permit", "permits"},
    "address_proximity": {"address", "public_facilities", "transportation"},
}


def _blob(record: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("layer_name", "service_name", "category", "canonical_topic", "aliases", "description", "planning_use_cases"):
        value = record.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts).lower()


def rank_candidate_layers(request_plan: dict[str, Any], catalog_records: list[dict[str, Any]], *, limit: int = 12) -> list[dict[str, Any]]:
    required = set(request_plan.get("required_layers") or [])
    domains = {request_plan.get("primary_domain"), *(request_plan.get("secondary_domains") or [])}
    request_type = str(request_plan.get("request_type") or "")
    geography = str(request_plan.get("geography") or "").lower()
    ranked: list[dict[str, Any]] = []
    for record in catalog_records:
        score = 0
        reasons: list[str] = []
        category = str(record.get("category") or record.get("canonical_topic") or "")
        blob = _blob(record)
        if category in required:
            score += 80
            reasons.append(f"category satisfies required layer role: {category}")
        for domain in domains:
            if domain and category in CATEGORY_BY_DOMAIN.get(str(domain), set()):
                score += 60
                reasons.append(f"semantic domain match: {domain}")
                break
        if request_type == "zoning_context" and "zoning" in blob:
            score += 45
            reasons.append("zoning context request")
        if request_type == "zoning_context" and ("road" in blob or "street" in blob or "centerline" in blob):
            score += 40
            reasons.append("road context requested")
        if request_type == "floodplain_screening" and ("flood" in blob or "fema" in blob):
            score += 50
            reasons.append("floodplain screening request")
        if geography and geography in blob:
            score += 25
            reasons.append(f"geography-specific layer match: {geography}")
        if record.get("is_verified"):
            score += 15
            reasons.append("verified layer")
        if record.get("is_feature_layer"):
            score += 8
            reasons.append("feature layer")
        if record.get("is_historical") and request_type != "historical_lookup":
            score -= 120
            reasons.append("historical layer excluded from current request")
        if request_type == "historical_lookup" and record.get("is_historical"):
            score += 80
            reasons.append("historical layer matches time request")
        if score <= 0:
            continue
        ranked.append({**deepcopy(record), "brain_rank_score": score, "brain_rank_confidence": round(min(score / 180, 0.99), 3), "brain_rank_reasons": reasons})
    ranked.sort(key=lambda item: item.get("brain_rank_score", 0), reverse=True)
    return ranked[:limit]


def attach_layer_rank_explanations(recipe: dict[str, Any], ranked_layers: list[dict[str, Any]]) -> dict[str, Any]:
    by_key = {item.get("layer_key"): item for item in ranked_layers}
    for layer in recipe.get("selected_layers") or []:
        rank = by_key.get(layer.get("layer_key"))
        if rank:
            layer["brain_rank_score"] = rank.get("brain_rank_score")
            layer["brain_rank_reasons"] = rank.get("brain_rank_reasons") or []
    recipe["brain_layer_rankings"] = [
        {"layer_key": item.get("layer_key"), "layer_name": item.get("layer_name"), "category": item.get("category"), "score": item.get("brain_rank_score"), "confidence": item.get("brain_rank_confidence"), "reasons": item.get("brain_rank_reasons")}
        for item in ranked_layers
    ]
    return recipe
