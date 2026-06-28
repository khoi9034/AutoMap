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
    "map recent permits and planning cases near Kannapolis",
    "show 2014 parcels and zoning in Cabarrus County",
    "show parcels near 123 Main St Charlotte NC",
]


def _visible_layer_count(result: dict[str, Any]) -> int:
    config = result.get("preview_config") if isinstance(result.get("preview_config"), dict) else {}
    layers = config.get("context_layers") or config.get("operational_layers") or []
    return sum(1 for layer in layers if isinstance(layer, dict) and layer.get("visibility", layer.get("default_visible", True)) is not False)


def _primary_role(result: dict[str, Any]) -> str | None:
    if result.get("primary_result_role"):
        return str(result["primary_result_role"])
    config = result.get("preview_config") if isinstance(result.get("preview_config"), dict) else {}
    for layer in config.get("derived_overlays") or []:
        if isinstance(layer, dict) and layer.get("visible", layer.get("default_visible", True)) is not False:
            return str(layer.get("role") or layer.get("map_role") or "")
    for layer in config.get("context_layers") or config.get("operational_layers") or []:
        if isinstance(layer, dict) and layer.get("visibility", layer.get("default_visible", True)) is not False:
            return str(layer.get("map_role") or layer.get("role") or "")
    return None


def check_prompt(prompt: str) -> dict[str, Any]:
    started = time.perf_counter()
    body = json.dumps({"prompt": prompt}).encode("utf-8")
    try:
        with urlopen(Request(URL, data=body, headers={"Content-Type": "application/json"}, method="POST"), timeout=330) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
            result = payload.get("result") if isinstance(payload.get("result"), dict) else payload
            return {
                "prompt": prompt,
                "http_status": response.status,
                "seconds": round(time.perf_counter() - started, 2),
                "result_state": result.get("result_state"),
                "request_type": result.get("request_type"),
                "can_preview": result.get("can_preview"),
                "visible_layer_count": _visible_layer_count(result),
                "primary_role": _primary_role(result),
                "warnings": (result.get("warnings") or [])[:4],
                "failure_category": result.get("error_category") or result.get("failure_category"),
            }
    except HTTPError as exc:
        return {"prompt": prompt, "http_status": exc.code, "seconds": round(time.perf_counter() - started, 2), "failure_category": "http_error"}
    except (TimeoutError, URLError) as exc:
        return {"prompt": prompt, "http_status": None, "seconds": round(time.perf_counter() - started, 2), "failure_category": exc.__class__.__name__}


def main() -> int:
    rows = [check_prompt(prompt) for prompt in PROMPTS]
    for row in rows:
        print(json.dumps(row, default=str))
    return 0 if all(row.get("http_status") == 200 for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
