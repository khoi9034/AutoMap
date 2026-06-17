"""Detect approved routing capability without calling paid or external APIs."""

from __future__ import annotations

from typing import Any

from app.layer_catalog_store import load_catalog_records


def detect_route_service(
    *,
    layer_catalog: list[dict[str, Any]] | None = None,
    schema_name: str = "automap",
) -> dict[str, Any]:
    """Return approved route service metadata if AutoMap has one configured.

    v3.8 intentionally does not call any paid routing or geocoding APIs. This
    detector only checks the local verified catalog for a route/network service
    that has already been approved for AutoMap use.
    """
    records = layer_catalog if layer_catalog is not None else load_catalog_records(schema_name)
    for record in records:
        blob = " ".join(
            str(value).lower()
            for value in [
                record.get("layer_key"),
                record.get("layer_name"),
                record.get("service_name"),
                record.get("category"),
                record.get("canonical_topic"),
                record.get("aliases"),
                record.get("planning_use_cases"),
            ]
            if value
        )
        if not record.get("is_verified") or record.get("approval_status") not in {"approved", None}:
            continue
        if "routing" in blob or "network analysis" in blob or "route service" in blob:
            return {
                "available": True,
                "route_mode": "road_network_route",
                "service": record,
                "warning": "Approved route/network service is configured.",
            }
    return {
        "available": False,
        "route_mode": "road_following_draft",
        "service": None,
        "warning": "No approved route/network service is configured; AutoMap will try a bounded road-following draft before falling back to a straight-line reference.",
    }

