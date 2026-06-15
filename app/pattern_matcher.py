"""Similarity matching for AutoMap approved patterns."""

from __future__ import annotations

from collections import Counter, defaultdict
import re
from typing import Any

from app.pattern_library import list_patterns
from app.prompt_parser import parse_prompt


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in "".join(char.lower() if char.isalnum() else " " for char in text).split()
        if len(token) > 2
    }


def _as_string_set(values: list[Any]) -> set[str]:
    result: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            for key in ("name", "type", "value"):
                if value.get(key):
                    result.add(str(value[key]).lower())
        elif value is not None:
            result.add(str(value).lower())
    return result


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _request_parts(raw_prompt: str, request_intelligence: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_prompt(raw_prompt)
    return {
        "tokens": _tokens(parsed.get("normalized_prompt") or raw_prompt),
        "topics": set(parsed.get("topics") or []),
        "geographies": _as_string_set(parsed.get("geography_terms") or []),
        "primary_intent": request_intelligence.get("primary_intent"),
        "secondary_intents": set(request_intelligence.get("secondary_intents") or []),
        "detected_intents": set(request_intelligence.get("detected_intents") or []),
        "historical": parsed.get("historical_year") is not None or "historical" in (parsed.get("time_references") or []),
    }


def _pattern_historical(pattern: dict[str, Any]) -> bool:
    prompt = str(pattern.get("raw_prompt") or pattern.get("normalized_prompt") or "").lower()
    if "historical" in prompt or "archive" in prompt:
        return True
    if re.search(r"\b20(0[4-9]|1[0-5])\b", prompt):
        return True
    return any(str(topic).lower() == "historical" for topic in pattern.get("topics") or [])


def score_pattern_similarity(pattern: dict[str, Any], request_intelligence: dict[str, Any], raw_prompt: str = "") -> float:
    """Score how similar one approved pattern is to a request."""
    if not pattern.get("is_active", True):
        return 0.0
    prompt = raw_prompt or str(pattern.get("raw_prompt") or "")
    request = _request_parts(prompt, request_intelligence)
    pattern_topics = set(str(topic).lower() for topic in pattern.get("topics") or [])
    pattern_geos = _as_string_set(pattern.get("geographies") or [])
    pattern_tokens = _tokens(str(pattern.get("normalized_prompt") or pattern.get("raw_prompt") or ""))
    pattern_primary = pattern.get("primary_intent")
    pattern_secondary = set(pattern.get("secondary_intents") or [])

    score = 0.0
    if pattern_primary and pattern_primary == request["primary_intent"]:
        score += 0.35
    elif pattern_primary and pattern_primary in request["detected_intents"]:
        score += 0.22
    score += min(len(pattern_secondary & request["detected_intents"]) * 0.06, 0.18)
    score += min(len(pattern_topics & request["topics"]) * 0.08, 0.24)
    score += min(len(pattern_geos & request["geographies"]) * 0.08, 0.16)
    score += _jaccard(pattern_tokens, request["tokens"]) * 0.22

    if _pattern_historical(pattern) != request["historical"]:
        score -= 0.25
    if pattern.get("final_publish_ready"):
        score += 0.05
    if pattern.get("usage_count"):
        score += min(float(pattern["usage_count"]) * 0.01, 0.05)

    return round(max(0.0, min(score, 0.99)), 3)


def find_similar_patterns(
    raw_prompt: str,
    request_intelligence: dict[str, Any],
    *,
    limit: int = 5,
    min_score: float = 0.28,
) -> list[dict[str, Any]]:
    """Find approved patterns similar to a request."""
    try:
        patterns = list_patterns(limit=100)
    except Exception:
        return []
    scored = []
    for pattern in patterns:
        score = score_pattern_similarity(pattern, request_intelligence, raw_prompt=raw_prompt)
        if score >= min_score:
            scored.append({**pattern, "similarity_score": score})
    return sorted(scored, key=lambda item: item["similarity_score"], reverse=True)[:limit]


def get_preferred_layers_from_patterns(patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate preferred layers from similar approved patterns."""
    counts: Counter[str] = Counter()
    sources: defaultdict[str, list[str]] = defaultdict(list)
    for pattern in patterns:
        for layer_key in pattern.get("preferred_layer_keys") or pattern.get("selected_layer_keys") or []:
            key = str(layer_key)
            counts[key] += 1
            sources[key].append(pattern.get("pattern_key") or "")
    total = max(len(patterns), 1)
    return [
        {
            "layer_key": key,
            "pattern_count": count,
            "confidence_score": round(min(0.99, count / total), 3),
            "source_patterns": sorted(set(source for source in sources[key] if source)),
        }
        for key, count in counts.most_common()
    ]


def get_avoided_layers_from_patterns(patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate avoided/rejected layers from similar approved patterns."""
    counts: Counter[str] = Counter()
    for pattern in patterns:
        for layer_key in pattern.get("avoided_layer_keys") or pattern.get("rejected_layer_keys") or []:
            counts[str(layer_key)] += 1
    total = max(len(patterns), 1)
    return [
        {"layer_key": key, "pattern_count": count, "confidence_score": round(min(0.99, count / total), 3)}
        for key, count in counts.most_common()
    ]


def get_common_filter_defaults(patterns: list[dict[str, Any]]) -> dict[str, Any]:
    """Return filter-plan entries repeated in similar patterns."""
    common: dict[str, Any] = {}
    for pattern in patterns:
        for layer_key, entry in (pattern.get("filter_plan") or {}).items():
            if layer_key not in common:
                common[layer_key] = entry
    return common


def get_common_clarification_answers(patterns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate common clarification answers from similar patterns."""
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    payloads: dict[tuple[str, str], dict[str, Any]] = {}
    for pattern in patterns:
        for answer in pattern.get("clarification_answers") or []:
            if not isinstance(answer, dict) or not answer.get("question_id"):
                continue
            question_id = str(answer["question_id"])
            label = str(answer.get("answer_label") or answer.get("answer_value"))
            grouped[question_id][label] += 1
            payloads[(question_id, label)] = answer
    results: list[dict[str, Any]] = []
    total = max(len(patterns), 1)
    for question_id, counter in grouped.items():
        label, count = counter.most_common(1)[0]
        payload = payloads[(question_id, label)]
        results.append(
            {
                "question_id": question_id,
                "answer_value": payload.get("answer_value"),
                "answer_label": label,
                "pattern_count": count,
                "confidence_score": round(min(0.99, count / total), 3),
            }
        )
    return sorted(results, key=lambda item: item["confidence_score"], reverse=True)
