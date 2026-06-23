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
PROMPT = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station"


@dataclass
class SmokeResult:
    name: str
    ok: bool
    status: int | None
    seconds: float
    detail: str


def _safe_detail(body: bytes, limit: int = 220) -> str:
    text = body.decode("utf-8", errors="replace")
    lowered = text.lower()
    if "database_url" in lowered or "password" in lowered or "secret" in lowered or "token" in lowered:
        return "[redacted]"
    return text[:limit].replace("\n", " ")


def request_json(name: str, path: str, method: str = "GET", payload: dict[str, Any] | None = None, timeout: int = 30) -> SmokeResult:
    url = f"{FRONTEND}{path}"
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    started = time.perf_counter()
    try:
        with urlopen(Request(url, data=body, headers=headers, method=method), timeout=timeout) as response:
            raw = response.read()
            seconds = time.perf_counter() - started
            return SmokeResult(name, 200 <= response.status < 300, response.status, seconds, _safe_detail(raw))
    except HTTPError as exc:
        seconds = time.perf_counter() - started
        return SmokeResult(name, False, exc.code, seconds, _safe_detail(exc.read()))
    except TimeoutError:
        seconds = time.perf_counter() - started
        return SmokeResult(name, False, None, seconds, "timeout")
    except URLError as exc:
        seconds = time.perf_counter() - started
        reason = getattr(exc, "reason", exc)
        return SmokeResult(name, False, None, seconds, f"network_error: {reason}")


def main() -> int:
    checks = [
        request_json("frontend map-composer", "/map-composer", timeout=30),
        request_json("proxy health", "/api/automap/health", timeout=30),
        request_json("proxy quick status", "/api/automap/status?mode=quick", timeout=45),
        request_json("proxy db-health", "/api/automap/db-health", timeout=45),
        request_json(
            "composer demo prompt",
            "/api/automap/composer/generate",
            method="POST",
            payload={"prompt": PROMPT},
            timeout=210,
        ),
    ]
    for result in checks:
        outcome = "PASS" if result.ok else "FAIL"
        print(f"{outcome} {result.name}: status={result.status} seconds={result.seconds:.2f} detail={result.detail}")
    return 0 if all(result.ok for result in checks) else 1


if __name__ == "__main__":
    sys.exit(main())
