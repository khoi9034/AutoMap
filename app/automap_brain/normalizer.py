"""Prompt normalization for AutoMap Brain v2."""

from __future__ import annotations

import re
from typing import Any

from app.automap_brain.domain_ontology import PHRASE_REPLACEMENTS, TYPO_REPLACEMENTS


def normalize_prompt(prompt: str) -> dict[str, Any]:
    raw_text = str(prompt or "")
    text = raw_text.lower()
    corrections: list[dict[str, str]] = []
    for source, target in PHRASE_REPLACEMENTS.items():
        if source in text:
            text = text.replace(source, target)
            corrections.append({"from": source, "to": target})
    for source, target in TYPO_REPLACEMENTS.items():
        pattern = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE)
        if pattern.search(text):
            text = pattern.sub(target, text)
            corrections.append({"from": source, "to": target})
    text = re.sub(r"[,\t\r\n]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return {
        "raw_text": raw_text,
        "normalized_text": text,
        "corrections": corrections,
        "corrected": bool(corrections),
        "tokens": [token.strip(".,!?;:()[]{}\"'") for token in text.split() if token.strip()],
    }
