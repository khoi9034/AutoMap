"""Benchmark runner for AutoMap Brain Kernel v1."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

from app.automap_brain.intent_classifier import classify_intent
from app.automap_brain.parameter_extractor import extract_parameters
from app.automap_brain.spatial_operation_planner import plan_spatial_operation


DEFAULT_FIXTURE = Path("tests/fixtures/automap_brain_benchmark.json")


def _load_fixture(path: str | Path = DEFAULT_FIXTURE) -> list[dict[str, Any]]:
    fixture_path = Path(path)
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def _domains(intent: dict[str, Any]) -> set[str]:
    return {str(item) for item in intent.get("domains") or [] if item}


def score_prompt(item: dict[str, Any]) -> dict[str, Any]:
    prompt = str(item.get("prompt") or "")
    intent = classify_intent(prompt)
    params = extract_parameters(prompt, request_plan=intent["request_plan"])
    operation = plan_spatial_operation(intent["request_plan"], params)
    failures: list[str] = []

    expected_type = item.get("expected_request_type")
    actual_type = intent["request_type"]
    legacy_type = intent.get("legacy_request_type")
    if expected_type and expected_type not in {actual_type, legacy_type}:
        failures.append(f"intent expected {expected_type}, got {actual_type}")
    if item.get("expected_output_mode") and item["expected_output_mode"] != intent.get("output_mode"):
        failures.append(f"output expected {item['expected_output_mode']}, got {intent.get('output_mode')}")
    if item.get("expected_geography") and item["expected_geography"] != intent.get("geography"):
        failures.append(f"geography expected {item['expected_geography']}, got {intent.get('geography')}")
    missing_domains = set(item.get("expected_domains") or []) - _domains(intent)
    if missing_domains:
        failures.append(f"missing domains {sorted(missing_domains)}")
    expected_operation = item.get("expected_spatial_operation")
    if expected_operation and expected_operation != operation.get("operation"):
        failures.append(f"operation expected {expected_operation}, got {operation.get('operation')}")
    missing_roles = set(item.get("expected_layer_roles") or item.get("must_have_layer_roles") or []) - set(operation.get("layer_roles") or [])
    if missing_roles:
        failures.append(f"missing roles {sorted(missing_roles)}")

    return {
        "prompt": prompt,
        "passed": not failures,
        "failures": failures,
        "confidence": intent.get("confidence", 0),
        "request_type": actual_type,
        "output_mode": intent.get("output_mode"),
        "spatial_operation": operation.get("operation"),
        "layer_roles": operation.get("layer_roles") or [],
    }


def run_benchmark(path: str | Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    items = _load_fixture(path)
    rows = [score_prompt(item) for item in items]
    failed = [row for row in rows if not row["passed"]]
    return {
        "total": len(rows),
        "passed": len(rows) - len(failed),
        "failed": len(failed),
        "warnings": [],
        "average_confidence": round(mean(float(row.get("confidence") or 0) for row in rows), 3) if rows else 0,
        "failed_intent_classifications": [row for row in failed if any("intent expected" in failure for failure in row["failures"])],
        "failed_spatial_operations": [row for row in failed if any("operation expected" in failure for failure in row["failures"])],
        "failed_layer_roles": [row for row in failed if any("missing roles" in failure for failure in row["failures"])],
        "examples_needing_improvement": failed[:10],
        "results": rows,
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the AutoMap Brain Kernel benchmark.")
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE), help="Benchmark fixture JSON path.")
    parser.add_argument("--json", action="store_true", help="Print full JSON report.")
    args = parser.parse_args()
    report = run_benchmark(args.fixture)
    if args.json:
        print(json.dumps(report, indent=2))
        return
    print(f"AutoMap Brain Kernel benchmark: {report['passed']}/{report['total']} passed")
    print(f"Average confidence: {report['average_confidence']}")
    if report["failed"]:
        print("Examples needing improvement:")
        for row in report["examples_needing_improvement"]:
            print(f"- {row['prompt']}: {'; '.join(row['failures'])}")


if __name__ == "__main__":
    main()
