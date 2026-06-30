"""Production prompt smoke for AutoMap composer reliability."""

from __future__ import annotations

import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


URL = "https://auto-map-cyan.vercel.app/api/automap/composer/generate"
PROMPTS = [
    "commercial zoning around Concord",
    "show commercial zoning around Concord with nearby major roads",
    "show commercial zonign aorund concord with bearny major roads",
    "show parcels in Concord that are in the 100-year floodplain",
    "make a map of my address 793 bartram ave and include nearest line to the nearest fire station",
    "give me a table of parcels in Cabarrus County with parcel ID, acreage, municipality, and zoning",
]


def _preview_config(result: dict[str, Any]) -> dict[str, Any]:
    config = result.get("preview_config")
    return config if isinstance(config, dict) else {}


def _rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = result.get("visible_feature_summary") or _preview_config(result).get("visible_feature_summary") or []
    return [row for row in rows if isinstance(row, dict)]


def _legend_items(result: dict[str, Any]) -> list[str]:
    layout = result.get("map_layout") if isinstance(result.get("map_layout"), dict) else {}
    if not layout:
        layout = _preview_config(result).get("map_layout") if isinstance(_preview_config(result).get("map_layout"), dict) else {}
    items = layout.get("legend_items") or []
    return [str(item.get("label") or item.get("title") or "") for item in items if isinstance(item, dict)]


def _visible_row(row: dict[str, Any]) -> bool:
    try:
        count = int(row.get("feature_count") or 0)
    except (TypeError, ValueError):
        count = 0
    return row.get("visible") is not False and (count > 0 or row.get("query_status") == "generated")


def _visible_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [row for row in _rows(result) if _visible_row(row)]


def _visible_feature_count(result: dict[str, Any]) -> int:
    try:
        return int(result.get("visible_feature_total") or _preview_config(result).get("visible_feature_total") or 0)
    except (TypeError, ValueError):
        return sum(int(row.get("feature_count") or 0) for row in _visible_rows(result))


def _primary_role(result: dict[str, Any]) -> str | None:
    if result.get("primary_result_role"):
        return str(result["primary_result_role"])
    for row in _visible_rows(result):
        return str(row.get("expected_role") or row.get("map_role") or "")
    return None


def _legend_failures(result: dict[str, Any]) -> list[str]:
    visible_labels = {
        str(row.get("legend_label") or row.get("renderer_label") or row.get("layer_title") or "")
        for row in _visible_rows(result)
        if row.get("legend_included") is not False
    }
    failures: list[str] = []
    for label in _legend_items(result):
        if label and label not in visible_labels:
            failures.append(f"legend item has no matching visible feature: {label}")
    return failures


def _road_requested(prompt: str) -> bool:
    text = prompt.lower()
    return any(term in text for term in ("road", "roads", "street", "highway", "traffic", "corridor"))


def _prompt_failures(prompt: str, row: dict[str, Any], result: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    state = str(row.get("result_state") or "")
    if row.get("http_status") != 200:
        failures.append("server 500" if row.get("http_status") == 500 else "composer request did not return HTTP 200")
    if state == "ready" and int(row.get("visible_feature_count") or 0) == 0:
        failures.append("result_state=ready and visible_feature_count=0")
    failures.extend(_legend_failures(result))

    lower_prompt = prompt.lower()
    if "commercial" in lower_prompt and "zoning" in lower_prompt:
        visible = _visible_rows(result)
        zoning_rows = [item for item in visible if str(item.get("expected_role") or item.get("map_role") or "").lower() == "zoning"]
        road_rows = [item for item in visible if str(item.get("expected_role") or item.get("map_role") or "").lower() == "roads"]
        if state == "ready" and not zoning_rows:
            failures.append("commercial zoning prompt returned ready without visible zoning features")
        if state in {"ready", "partial"} and int(row.get("visible_feature_count") or 0) == 0:
            failures.append("commercial zoning prompt produced preview without visible features")
        if not _road_requested(prompt) and road_rows:
            failures.append("commercial zoning prompt included road context when roads were not requested")

    if "nearest line" in lower_prompt and "fire station" in lower_prompt:
        route_mode = str(result.get("route_mode") or (result.get("proximity_result") or {}).get("route_mode") or "")
        if state != "ready" or route_mode != "road_network":
            failures.append("proximity prompt did not return a ready road-network route")

    warnings = " ".join(str(item) for item in row.get("warnings") or []).lower()
    if "live request could not finish" in warnings:
        failures.append("generic live request failed")
    return failures


def check_prompt(prompt: str) -> dict[str, Any]:
    started = time.perf_counter()
    body = json.dumps({"prompt": prompt}).encode("utf-8")
    try:
        with urlopen(Request(URL, data=body, headers={"Content-Type": "application/json"}, method="POST"), timeout=330) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
            row = {
                "prompt": prompt,
                "http_status": response.status,
                "seconds": round(time.perf_counter() - started, 2),
                "result_state": result.get("result_state"),
                "request_type": result.get("request_type"),
                "can_preview": result.get("can_preview"),
                "visible_feature_count": _visible_feature_count(result),
                "primary_result_role": _primary_role(result),
                "legend_items": _legend_items(result),
                "warnings": (result.get("warnings") or [])[:4],
                "planner_used": result.get("planner_used"),
                "failure_category": result.get("error_category") or result.get("failure_category"),
            }
            row["failures"] = _prompt_failures(prompt, row, result)
            return row
    except HTTPError as exc:
        return {"prompt": prompt, "http_status": exc.code, "seconds": round(time.perf_counter() - started, 2), "failure_category": "http_error", "failures": ["composer request did not return HTTP 200"]}
    except (TimeoutError, URLError) as exc:
        return {"prompt": prompt, "http_status": None, "seconds": round(time.perf_counter() - started, 2), "failure_category": exc.__class__.__name__, "failures": ["composer request did not return HTTP 200"]}


def main() -> int:
    rows = [check_prompt(prompt) for prompt in PROMPTS]
    for row in rows:
        print(json.dumps(row, default=str))
    return 1 if any(row.get("failures") for row in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
