"""Intent classification for AutoMap Brain Kernel v1."""

from __future__ import annotations

from typing import Any

from app.automap_brain.request_parser import build_brain_plan
from app.prompt_parser import parse_prompt


def classify_intent(prompt: str, parsed_request: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify a county GIS prompt into a stable kernel intent object."""
    parsed = parsed_request or parse_prompt(prompt)
    plan = build_brain_plan(prompt, parsed)
    request_type = str(plan.get("request_type") or "unsupported_request")
    status = str(plan.get("status") or "")
    kernel_request_type = "unsupported_area" if request_type == "unsupported" and status == "unsupported_area" else request_type
    if kernel_request_type == "unsupported":
        kernel_request_type = "unsupported_request"
    domains = [domain for domain in [plan.get("primary_domain"), *(plan.get("secondary_domains") or [])] if domain]
    return {
        "original_prompt": prompt,
        "normalized_prompt": plan.get("normalized_prompt"),
        "request_type": kernel_request_type,
        "legacy_request_type": request_type,
        "confidence": plan.get("confidence", 0),
        "output_mode": plan.get("output_mode"),
        "primary_domain": plan.get("primary_domain"),
        "secondary_domains": plan.get("secondary_domains") or [],
        "domains": domains,
        "geography": plan.get("geography"),
        "geography_type": plan.get("geography_type"),
        "unsupported_status": status if kernel_request_type.startswith("unsupported") else None,
        "safety_notes": plan.get("safety_notes") or [],
        "request_plan": plan,
    }
