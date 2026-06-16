"""External REST source discovery and verification workflow for AutoMap."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.arcgis_service_search import (
    GAP_KEYWORDS,
    discovered_layer_source_key,
    inspect_candidate_service,
    inspect_candidate_layer,
    score_discovered_layer_for_gap,
    search_services_by_keyword,
    write_discovery_report,
)
from app.external_source_registry import (
    get_external_source,
    inspect_external_source,
    list_external_sources,
    update_external_source_metadata,
    upsert_external_source_to_catalog,
)
from app.layer_semantics import slugify


DEFAULT_DISCOVERY_ROOTS = [
    "https://location.cabarruscounty.us/arcgisservices/rest/services",
    "https://location.cabarruscounty.us/arcgisservices/rest/services/OpenData",
    "https://maps2.concordnc.gov/server/rest/services",
    "https://services.arcgis.com/NuWFvHYDMVmmxMeM/ArcGIS/rest/services",
    "https://gis11.services.ncdot.gov/arcgis/rest/services",
]

DEFAULT_DISCOVERY_KEYWORDS = [
    "permit",
    "permits",
    "planning",
    "cases",
    "plan review",
    "plan reviews",
    "Accela",
    "development",
    "subdivision",
    "zoning cases",
    "rezoning",
    "projects",
    "STIP",
    "AADT",
    "traffic",
]


def _keywords(keyword: str | None = None) -> list[str]:
    return [keyword] if keyword else list(DEFAULT_DISCOVERY_KEYWORDS)


def _best_gap_scores(layer: dict[str, Any]) -> list[dict[str, Any]]:
    scores = [score_discovered_layer_for_gap(layer, gap_key) for gap_key in GAP_KEYWORDS]
    return sorted(scores, key=lambda item: item.get("score", 0), reverse=True)


def _source_type_from_url(layer_url: str) -> str:
    lower = layer_url.lower()
    if "/featureserver/" in lower:
        return "arcgis_layer"
    return "arcgis_layer"


def _record_profile_for_gap(gap_key: str, score: int, layer: dict[str, Any]) -> dict[str, Any]:
    layer_name = str(layer.get("layer_name") or (layer.get("layer_metadata") or {}).get("layer_name") or "Discovered Layer")
    lower_name = layer_name.lower()
    if gap_key == "traffic_counts":
        return {
            "categories": ["transportation", "traffic", "aadt"],
            "intended_gaps": ["traffic_counts", "transportation_context"],
            "source_status": "reference",
            "approval_status": "candidate",
            "limitations": "Reference/context only until traffic-count vintage and AADT fields are reviewed.",
        }
    if gap_key == "stip_projects":
        return {
            "categories": ["transportation", "stip", "planned_projects"],
            "intended_gaps": ["stip_projects", "transportation_context"],
            "source_status": "reference",
            "approval_status": "candidate",
            "limitations": "Transportation project context only; not development approval or parcel suitability by itself.",
        }
    if gap_key == "current_development_pipeline":
        return {
            "categories": ["development_pipeline_proxy", "plan_review", "development"],
            "intended_gaps": ["current_development_pipeline"],
            "source_status": "proxy",
            "approval_status": "candidate",
            "limitations": "Proxy/context only unless the source owner confirms it as an official current development pipeline.",
        }
    if gap_key == "current_planning_cases":
        coverage = " Coverage may be limited; confirm municipality and countywide coverage." if "concord" in lower_name else ""
        return {
            "categories": ["planning", "planning_cases", "rezoning"],
            "intended_gaps": ["current_planning_cases"],
            "source_status": "active",
            "approval_status": "candidate" if score < 90 else "needs_review",
            "limitations": f"Planning case authority, case status, date fields, and coverage require review.{coverage}",
        }
    return {
        "categories": ["permit", "permits", "development"],
        "intended_gaps": ["current_permits"],
        "source_status": "active",
        "approval_status": "needs_review",
        "limitations": "Permit authority, currentness, status fields, and coverage require review before official use.",
    }


def discovered_layer_to_source_record(layer: dict[str, Any], score: dict[str, Any]) -> dict[str, Any]:
    """Build a reviewable external source seed/registry record from a verified discovered layer."""
    layer_url = str(layer.get("layer_url") or "")
    layer_name = str(layer.get("layer_name") or (layer.get("layer_metadata") or {}).get("layer_name") or "Discovered Layer")
    gap_key = str(score.get("gap_key") or "external_reference")
    profile = _record_profile_for_gap(gap_key, int(score.get("score") or 0), layer)
    source_key = discovered_layer_source_key(layer_url, layer_name, gap_key)
    service_url = layer_url.rsplit("/", 1)[0] if "/" in layer_url else None
    return {
        "source_key": source_key,
        "source_name": layer_name,
        "source_type": _source_type_from_url(layer_url),
        "base_url": service_url,
        "layer_url": layer_url,
        "priority": 60,
        "approval_status": profile["approval_status"],
        "source_status": profile["source_status"],
        "categories": profile["categories"],
        "intended_gaps": profile["intended_gaps"],
        "notes": (
            f"Discovered by AutoMap source discovery for {gap_key}; matched terms: "
            f"{', '.join(score.get('matched_terms') or []) or 'keyword metadata'}."
        ),
        "limitations": profile["limitations"],
    }


def discover_sources(
    *,
    keyword: str | None = None,
    roots: list[str] | None = None,
    min_score: int = 45,
    write_report: bool = True,
) -> dict[str, Any]:
    """Search known ArcGIS roots for candidate external source layers."""
    selected_roots = roots or DEFAULT_DISCOVERY_ROOTS
    selected_keywords = _keywords(keyword)
    service_matches: list[dict[str, Any]] = []
    inspected_services: list[dict[str, Any]] = []
    candidate_layers: list[dict[str, Any]] = []
    candidate_records: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    seen_services: set[str] = set()
    seen_layers: set[str] = set()

    for root in selected_roots:
        try:
            matches = search_services_by_keyword(root, selected_keywords)
        except Exception as exc:
            failures.append({"root_url": root, "error": str(exc)})
            continue
        for match in matches:
            service_url = match.get("service_url")
            if not service_url or service_url in seen_services:
                continue
            seen_services.add(service_url)
            service_matches.append(match)
            inspected = inspect_candidate_service(str(service_url), layer_keywords=selected_keywords)
            inspected = {**inspected, "root_url": root, "matched_keywords": match.get("matched_keywords") or []}
            inspected_services.append(inspected)
            for layer in inspected.get("layers") or []:
                layer_url = layer.get("layer_url")
                if not layer_url or layer_url in seen_layers:
                    continue
                seen_layers.add(layer_url)
                scores = _best_gap_scores(layer)
                best = scores[0] if scores else {"score": 0}
                if int(best.get("score") or 0) < min_score:
                    continue
                enriched = {
                    **layer,
                    "service_url": service_url,
                    "service_name": inspected.get("service_name"),
                    "gap_scores": scores,
                    "best_gap_score": best,
                }
                candidate_layers.append(enriched)
                candidate_records.append(discovered_layer_to_source_record(enriched, best))

    result: dict[str, Any] = {
        "discovered_at": datetime.now(UTC).isoformat(),
        "roots": selected_roots,
        "keywords": selected_keywords,
        "services_discovered": len(service_matches),
        "services_inspected": len(inspected_services),
        "candidate_layers": candidate_layers,
        "candidate_records": candidate_records,
        "candidate_count": len(candidate_records),
        "failures": failures,
        "downloaded_geometry": False,
    }
    if write_report:
        result["report_path"] = str(write_discovery_report(result))
    return result


def verify_external_source(source_key: str, schema_name: str = "automap") -> dict[str, Any]:
    """Verify one registered external source and upsert verified catalog rows if appropriate."""
    source = get_external_source(source_key, schema_name)
    inspected = inspect_external_source(source)
    updated = update_external_source_metadata(source_key, inspected["inspected_metadata"], schema_name)
    catalog_upserts = upsert_external_source_to_catalog(source_key, schema_name)
    return {
        "source_key": source_key,
        "source": updated,
        "catalog_upserts": catalog_upserts,
        "downloaded_geometry": False,
    }


def verify_all_external_sources(schema_name: str = "automap") -> dict[str, Any]:
    """Verify every registered external source with metadata-only checks."""
    results: list[dict[str, Any]] = []
    catalog_upserts = 0
    for source in list_external_sources(schema_name):
        result = verify_external_source(str(source["source_key"]), schema_name)
        results.append(result)
        catalog_upserts += int(result.get("catalog_upserts") or 0)
    return {
        "verified_sources": len(results),
        "catalog_upserts": catalog_upserts,
        "results": results,
        "downloaded_geometry": False,
    }


def discovery_summary_lines(result: dict[str, Any]) -> list[str]:
    """Render concise CLI output for discovery results."""
    lines = [
        f"services discovered: {result.get('services_discovered', 0)}",
        f"services inspected: {result.get('services_inspected', 0)}",
        f"candidate layers: {len(result.get('candidate_layers') or [])}",
        f"candidate records: {result.get('candidate_count', 0)}",
    ]
    if result.get("report_path"):
        lines.append(f"discovery report: {result['report_path']}")
    for record in (result.get("candidate_records") or [])[:20]:
        lines.append(
            f"- {record['source_key']} | {record['source_name']} | "
            f"{record['approval_status']} | {record['source_status']} | {', '.join(record.get('intended_gaps') or [])}"
        )
    return lines


def source_key_for_known_transportation(name: str) -> str:
    """Stable helper used by tests and future seed curation."""
    return f"verified_{slugify(name)}"
