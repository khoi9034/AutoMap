"""Safe production smoke checks for the public AutoMap deployment."""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FRONTEND = "https://auto-map-cyan.vercel.app"

PRESET_PROMPTS = [
    ("nearest fire station preset", "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"),
    ("floodplain parcel preset", "show parcels in Concord that are in the 100-year floodplain"),
    ("parcel table preset", "give me a table of parcels in Cabarrus County with parcel ID, acreage, municipality, and zoning"),
]


@dataclass
class SmokeResult:
    name: str
    ok: bool
    status: int | None
    seconds: float
    detail: str


def _redacted(text: str, limit: int = 260) -> str:
    lowered = text.lower()
    if any(marker in lowered for marker in ["database_url", "password", "secret", "token", "service" + "_role"]):
        return "[redacted]"
    return text[:limit].replace("\n", " ")


def _summarize_json(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return _redacted(text)
    summary = {
        "request_type": payload.get("request_type"),
        "can_preview": payload.get("can_preview"),
        "title": payload.get("map_title"),
        "route_mode": payload.get("route_mode") or (payload.get("proximity_result") or {}).get("route_mode"),
        "table_status": (payload.get("table_context") or {}).get("export_status"),
        "database_connected": payload.get("database_connected"),
        "real_publish_enabled": payload.get("real_publish_enabled"),
    }
    return _redacted(json.dumps({key: value for key, value in summary.items() if value is not None}, default=str))


def request_check(
    name: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout: int = 30,
    expect_json: bool = False,
) -> SmokeResult:
    url = f"{FRONTEND}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json" if expect_json else "text/html,application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    started = time.perf_counter()
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=timeout) as response:
            raw = response.read()
            seconds = time.perf_counter() - started
            detail = _summarize_json(raw) if expect_json else _redacted(raw.decode("utf-8", errors="replace"))
            return SmokeResult(name, 200 <= response.status < 300, response.status, seconds, detail)
    except HTTPError as exc:
        seconds = time.perf_counter() - started
        return SmokeResult(name, False, exc.code, seconds, _redacted(exc.read().decode("utf-8", errors="replace")))
    except TimeoutError:
        seconds = time.perf_counter() - started
        return SmokeResult(name, False, None, seconds, "timeout")
    except URLError as exc:
        seconds = time.perf_counter() - started
        reason = getattr(exc, "reason", exc)
        return SmokeResult(name, False, None, seconds, f"network_error: {reason}")


def main() -> int:
    checks = [
        request_check("homepage", "/", timeout=30),
        request_check("map composer", "/map-composer", timeout=30),
        request_check("methodology", "/methodology", timeout=30),
        request_check("system status", "/system-status", timeout=30),
        request_check("proxy health", "/api/automap/health", timeout=30, expect_json=True),
        request_check("proxy quick status", "/api/automap/status?mode=quick", timeout=45, expect_json=True),
        request_check("proxy db-health", "/api/automap/db-health", timeout=45, expect_json=True),
    ]
    for name, prompt in PRESET_PROMPTS:
        checks.append(
            request_check(
                name,
                "/api/automap/composer/generate",
                method="POST",
                payload={"prompt": prompt},
                timeout=240,
                expect_json=True,
            )
        )

    for result in checks:
        outcome = "PASS" if result.ok else "FAIL"
        print(f"{outcome} {result.name}: status={result.status} seconds={result.seconds:.2f} detail={result.detail}")
    return 0 if all(result.ok for result in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
