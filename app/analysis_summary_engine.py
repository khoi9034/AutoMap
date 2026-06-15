"""Build count/statistics-only summaries for AutoMap analysis results."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from typing import Any
from uuid import uuid4

from app.analysis_refinement_engine import get_refinement_session
from app.analysis_result_store import get_analysis_run
from app.analysis_summary_models import AnalysisSummaryReport, AnalysisSummarySection, AnalysisSummaryType
from app.field_profiler import load_field_profiles, load_value_profiles
from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import slugify
from app.spatial_query_client import SpatialQueryClient


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _optimized_plan(receipt: dict[str, Any]) -> dict[str, Any]:
    return _json_dict(receipt.get("optimized_query_plan"))


def _first_int(*values: Any) -> int | None:
    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return None


def _broad_count(receipt: dict[str, Any], session: dict[str, Any] | None = None) -> int | None:
    optimized = _optimized_plan(receipt)
    return _first_int(
        session.get("broad_count") if session else None,
        receipt.get("broad_count"),
        optimized.get("broad_count"),
        (_json_dict(receipt.get("input_counts")).get("optimizer") or {}).get("broad_count")
        if isinstance(_json_dict(receipt.get("input_counts")).get("optimizer"), dict)
        else None,
    )


def _optimized_count(receipt: dict[str, Any], session: dict[str, Any] | None = None) -> int | None:
    optimized = _optimized_plan(receipt)
    return _first_int(
        session.get("optimized_count") if session else None,
        receipt.get("optimized_candidate_count"),
        optimized.get("optimized_candidate_count"),
        (_json_dict(receipt.get("input_counts")).get("optimizer") or {}).get("optimized_candidate_count")
        if isinstance(_json_dict(receipt.get("input_counts")).get("optimizer"), dict)
        else None,
    )


def _safety_limit(receipt: dict[str, Any], session: dict[str, Any] | None = None) -> int | None:
    optimized = _optimized_plan(receipt)
    limits = _json_dict(receipt.get("max_feature_limits")) or _json_dict(optimized.get("safety_limits"))
    return _first_int(
        session.get("safety_limit") if session else None,
        limits.get("run_max_features"),
        limits.get("max_download_features_per_layer"),
        limits.get("default_max_features"),
    )


def _strategy(receipt: dict[str, Any], summary: dict[str, Any] | None = None) -> str | None:
    optimized = _optimized_plan(receipt)
    return str(
        (summary or {}).get("strategy")
        or receipt.get("query_strategy")
        or optimized.get("strategy")
        or ""
    ) or None


def _constraint_count(receipt: dict[str, Any], summary: dict[str, Any] | None = None) -> int | None:
    optimized = _optimized_plan(receipt)
    return _first_int(
        (summary or {}).get("constraint_feature_count"),
        receipt.get("constraint_feature_count"),
        optimized.get("constraint_feature_count"),
    )


def _chunks(receipt: dict[str, Any], summary: dict[str, Any] | None = None) -> tuple[int | None, list[dict[str, Any]]]:
    optimized = _optimized_plan(receipt)
    chunk_rows = _json_list((summary or {}).get("chunk_receipts")) or _json_list(optimized.get("chunk_receipts")) or _json_list(receipt.get("chunk_receipts"))
    return _first_int((summary or {}).get("chunks_planned"), receipt.get("chunks_used"), optimized.get("chunks_planned"), len(chunk_rows) if chunk_rows else None), [
        row for row in chunk_rows if isinstance(row, dict)
    ]


def _selected_layers(run: dict[str, Any]) -> list[dict[str, Any]]:
    recipe = _json_dict(run.get("recipe_json"))
    layers = [layer for layer in recipe.get("selected_layers") or [] if isinstance(layer, dict)]
    if layers:
        return layers
    receipt = _json_dict(run.get("analysis_receipt"))
    rows = []
    for key in ["target_layer", "geography_layer", "constraint_layer", "attribute_layer"]:
        layer = _json_dict(receipt.get(key)) or _json_dict(_optimized_plan(receipt).get(key))
        if layer:
            rows.append(layer)
    return rows


def _definition_expressions(run: dict[str, Any]) -> list[dict[str, Any]]:
    recipe = _json_dict(run.get("recipe_json"))
    rows: list[dict[str, Any]] = []
    for layer_key, plan in (recipe.get("filter_plan") or {}).items():
        if isinstance(plan, dict):
            expression = plan.get("draft_where_clause") or plan.get("definition_expression")
            if expression:
                rows.append({"layer_key": layer_key, "definition_expression": expression})
    receipt = _json_dict(run.get("analysis_receipt"))
    for label, expression in (_json_dict(receipt.get("where_clauses"))).items():
        if expression:
            rows.append({"layer_key": label, "definition_expression": expression})
    return rows


def _missing_data(run: dict[str, Any]) -> list[str]:
    recipe = _json_dict(run.get("recipe_json"))
    rows = []
    for item in recipe.get("missing_data_needed") or []:
        rows.append(json.dumps(item, default=str) if isinstance(item, dict) else str(item))
    for item in recipe.get("analysis_plan", {}).get("blockers") or []:
        if "missing" in str(item).lower():
            rows.append(str(item))
    return _dedupe(rows)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            rows.append(text)
            seen.add(text)
    return rows


def _warning_groups(run: dict[str, Any], session: dict[str, Any] | None = None) -> dict[str, list[str]]:
    receipt = _json_dict(run.get("analysis_receipt"))
    groups = {
        "safety": [],
        "missing_data": [],
        "analysis": [],
        "refinement": [],
        "unsupported": [],
    }
    for item in [*(_json_list(run.get("warnings"))), *(_json_list(receipt.get("warnings"))), *(_json_list(receipt.get("blocked_reasons")))]:
        text = str(item)
        lowered = text.lower()
        if "missing" in lowered:
            groups["missing_data"].append(text)
        elif "unsupported" in lowered:
            groups["unsupported"].append(text)
        elif "limit" in lowered or "block" in lowered or "safe" in lowered:
            groups["safety"].append(text)
        else:
            groups["analysis"].append(text)
    if session:
        if session.get("blocked_reason"):
            groups["refinement"].append(str(session["blocked_reason"]))
        result = _json_dict(session.get("refined_result"))
        for item in _json_list(result.get("blocked_reasons")):
            groups["refinement"].append(str(item))
    return {key: _dedupe(values) for key, values in groups.items()}


def _target_layer(run: dict[str, Any]) -> dict[str, Any]:
    receipt = _json_dict(run.get("analysis_receipt"))
    layer = _json_dict(receipt.get("target_layer")) or _json_dict(_optimized_plan(receipt).get("target_layer"))
    if layer.get("layer_key"):
        for record in load_catalog_records():
            if record.get("layer_key") == layer.get("layer_key"):
                merged = dict(record)
                merged.update({key: value for key, value in layer.items() if value is not None})
                return merged
    for selected in _selected_layers(run):
        if selected.get("category") == "parcel":
            return selected
    return layer


def _field_name(field: dict[str, Any]) -> str:
    return str(field.get("field_name") or field.get("name") or "")


def _field_type(field: dict[str, Any]) -> str:
    return str(field.get("field_type") or field.get("type") or "")


def _candidate_group_fields(layer: dict[str, Any]) -> list[dict[str, Any]]:
    layer_key = layer.get("layer_key")
    fields = [field for field in layer.get("fields") or [] if isinstance(field, dict)]
    profile_rows = load_field_profiles([layer_key]) if layer_key else {}
    profiled = profile_rows.get(layer_key) or []
    by_name: dict[str, dict[str, Any]] = {}
    for field in fields:
        name = _field_name(field)
        if name:
            by_name[name] = dict(field)
    for profile in profiled:
        name = _field_name(profile)
        if name:
            merged = dict(by_name.get(name, {}))
            merged.update(profile)
            by_name[name] = merged
    candidates: list[dict[str, Any]] = []
    for field in by_name.values():
        name = _field_name(field)
        alias = str(field.get("field_alias") or field.get("alias") or "")
        field_type = _field_type(field)
        search = f"{name} {alias}".lower()
        if not name or field.get("is_object_id") or field.get("is_geometry_field"):
            continue
        if any(term in search for term in ["zone", "zoning", "use", "class", "code", "type", "municip", "district", "city", "town"]):
            candidates.append({**field, "summary_group": "categorical"})
        elif any(term in search for term in ["acre", "area", "landunits"]) and any(term in field_type.lower() for term in ["double", "integer", "smallinteger", "single"]):
            candidates.append({**field, "summary_group": "numeric_bucket_candidate"})
    return candidates[:6]


def build_grouped_attribute_summaries(
    run: dict[str, Any],
    *,
    query_client: SpatialQueryClient | None = None,
    enabled: bool = True,
) -> list[dict[str, Any]]:
    """Try safe returnGeometry=false grouped summaries for the target layer."""
    layer = _target_layer(run)
    layer_url = layer.get("layer_url") or layer.get("rest_url")
    layer_key = layer.get("layer_key")
    if not enabled or not layer_url:
        return [
            {
                "summary_type": AnalysisSummaryType.GROUPED_ATTRIBUTE_SUMMARY.value,
                "status": "unsupported",
                "layer_key": layer_key,
                "reason": "Grouped summaries were not requested or target layer URL is unavailable.",
                "return_geometry": False,
            }
        ]
    client = query_client or SpatialQueryClient()
    value_profiles = load_value_profiles([layer_key]) if layer_key else {}
    rows: list[dict[str, Any]] = []
    for field in _candidate_group_fields(layer):
        name = _field_name(field)
        if not name:
            continue
        if field.get("summary_group") == "numeric_bucket_candidate":
            rows.append(
                {
                    "summary_type": AnalysisSummaryType.GROUPED_ATTRIBUTE_SUMMARY.value,
                    "status": "unsupported",
                    "layer_key": layer_key,
                    "field_name": name,
                    "field_alias": field.get("field_alias") or field.get("alias"),
                    "reason": "Numeric bucket summaries require reviewed bucket where clauses in v2.3.",
                    "return_geometry": False,
                }
            )
            continue
        try:
            result = client.query_grouped_statistics(layer_url, name, where="1=1", max_groups=25)
            rows.append(
                {
                    "summary_type": AnalysisSummaryType.GROUPED_ATTRIBUTE_SUMMARY.value,
                    "status": "ok",
                    "layer_key": layer_key,
                    "layer_name": layer.get("layer_name"),
                    "field_name": name,
                    "field_alias": field.get("field_alias") or field.get("alias"),
                    "rows": result.get("rows") or [],
                    "return_geometry": result.get("return_geometry") is False,
                    "request_method": result.get("request_method"),
                    "sample_values": (value_profiles.get((layer_key, name)) or {}).get("sample_values") if layer_key else None,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "summary_type": AnalysisSummaryType.GROUPED_ATTRIBUTE_SUMMARY.value,
                    "status": "unsupported",
                    "layer_key": layer_key,
                    "field_name": name,
                    "field_alias": field.get("field_alias") or field.get("alias"),
                    "reason": str(exc),
                    "return_geometry": False,
                }
            )
    if not rows:
        rows.append(
            {
                "summary_type": AnalysisSummaryType.GROUPED_ATTRIBUTE_SUMMARY.value,
                "status": "unsupported",
                "layer_key": layer_key,
                "reason": "No real profiled grouping fields were available.",
                "return_geometry": False,
            }
        )
    return rows


def _base_report_id(prefix: str) -> str:
    return f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}"


def build_analysis_summary_from_run(
    analysis_run_id: str,
    *,
    query_client: SpatialQueryClient | None = None,
    include_grouped_statistics: bool = True,
) -> AnalysisSummaryReport:
    """Build a report summary from a stored analysis run."""
    run = get_analysis_run(analysis_run_id)
    receipt = _json_dict(run.get("analysis_receipt"))
    broad = _broad_count(receipt)
    optimized = _optimized_count(receipt)
    limit = _safety_limit(receipt)
    chunks_planned, chunk_rows = _chunks(receipt)
    grouped = build_grouped_attribute_summaries(run, query_client=query_client, enabled=include_grouped_statistics)
    status = str(run.get("status") or receipt.get("status") or "")
    report = AnalysisSummaryReport(
        report_id=_base_report_id("analysis_report"),
        report_title=f"AutoMap Analysis Report - {slugify(str(run.get('raw_prompt') or analysis_run_id)).replace('_', ' ').title()}",
        source_type="analysis_run",
        source_analysis_run_id=analysis_run_id,
        raw_prompt=str(run.get("raw_prompt") or receipt.get("raw_prompt") or ""),
        analysis_status=status,
        operation_type=str(run.get("operation_type") or receipt.get("operation_type") or ""),
        strategy_used=_strategy(receipt),
        broad_count=broad,
        optimized_count=optimized,
        safety_limit=limit,
        geometry_downloaded=bool(run.get("output_geojson_path")),
        geojson_created=bool(run.get("output_geojson_path")),
        selected_layers=_selected_layers(run),
        definition_expressions=_definition_expressions(run),
        warnings=_warning_groups(run),
        missing_data=_missing_data(run),
        narrowing_suggestions=_json_list(receipt.get("narrowing_suggestions")) or _json_list(_optimized_plan(receipt).get("narrowing_suggestions")),
        grouped_summaries=grouped,
    )
    report.sections = [
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.COUNT_SUMMARY,
            title="Count Summary",
            rows=[
                {
                    "broad_count": broad,
                    "optimized_candidate_count": optimized,
                    "safety_limit": limit,
                    "blocked": status == "blocked",
                }
            ],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.CONSTRAINT_SUMMARY,
            title="Constraint Summary",
            rows=[{"constraint_feature_count": _constraint_count(receipt)}],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.CHUNK_SUMMARY,
            title="Chunk Summary",
            rows=chunk_rows,
            metadata={"chunks_planned": chunks_planned},
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.SAFETY_SUMMARY,
            title="Safety Summary",
            rows=[{"safety_limit": limit, "geometry_downloaded": bool(run.get("output_geojson_path")), "geojson_created": bool(run.get("output_geojson_path"))}],
            notes=_json_list(receipt.get("blocked_reasons")),
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.GROUPED_ATTRIBUTE_SUMMARY,
            title="Grouped Attribute Summaries",
            status="ok" if any(row.get("status") == "ok" for row in grouped) else "unsupported",
            rows=grouped,
            notes=["Grouped summaries use ArcGIS REST statistics with returnGeometry=false."],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.MISSING_DATA_SUMMARY,
            title="Missing Data Summary",
            rows=[{"missing_data": item} for item in _missing_data(run)],
        ),
    ]
    return report


def build_analysis_summary_from_refinement(
    refinement_session_id: str,
    *,
    query_client: SpatialQueryClient | None = None,
    include_grouped_statistics: bool = True,
) -> AnalysisSummaryReport:
    """Build a report summary from a stored analysis refinement session."""
    session = get_refinement_session(refinement_session_id)
    source_run_id = str(session.get("source_analysis_run_id") or "")
    if not source_run_id:
        raise ValueError("Refinement session is missing source_analysis_run_id.")
    run = get_analysis_run(source_run_id)
    receipt = _json_dict(run.get("analysis_receipt"))
    result = _json_dict(session.get("refined_result"))
    result_summary = _json_dict(result.get("summary"))
    selected_option = _json_dict(session.get("selected_option")).get("option_id")
    grouped = build_grouped_attribute_summaries(run, query_client=query_client, enabled=include_grouped_statistics)
    report = AnalysisSummaryReport(
        report_id=_base_report_id("analysis_report"),
        report_title=f"AutoMap Analysis Report - {slugify(str(session.get('raw_prompt') or refinement_session_id)).replace('_', ' ').title()}",
        source_type="analysis_refinement",
        source_analysis_run_id=source_run_id,
        source_refinement_session_id=refinement_session_id,
        raw_prompt=str(session.get("raw_prompt") or run.get("raw_prompt") or ""),
        analysis_status=str(session.get("status") or result.get("status") or ""),
        operation_type=str(run.get("operation_type") or receipt.get("operation_type") or ""),
        strategy_used=_strategy(receipt, result_summary),
        broad_count=_broad_count(receipt, session),
        optimized_count=_optimized_count(receipt, session),
        safety_limit=_safety_limit(receipt, session),
        geometry_downloaded=bool(result_summary.get("geometry_downloaded") or result.get("geometry_downloaded")),
        geojson_created=bool(result_summary.get("geojson_created") or result.get("output_geojson_path")),
        selected_refinement_option=str(selected_option or ""),
        selected_layers=_selected_layers(run),
        definition_expressions=_definition_expressions(run),
        warnings=_warning_groups(run, session),
        missing_data=_missing_data(run),
        narrowing_suggestions=_json_list(result_summary.get("narrowing_suggestions")) or _json_list(receipt.get("narrowing_suggestions")) or _json_list(_optimized_plan(receipt).get("narrowing_suggestions")),
        grouped_summaries=grouped,
    )
    chunks_planned, chunk_rows = _chunks(receipt, result_summary)
    report.sections = [
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.REFINEMENT_SUMMARY,
            title="Refinement Summary",
            rows=[
                {
                    "selected_refinement_option": selected_option,
                    "geometry_downloaded": report.geometry_downloaded,
                    "geojson_created": report.geojson_created,
                    "output_folder": result.get("output_folder"),
                }
            ],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.COUNT_SUMMARY,
            title="Count Summary",
            rows=[
                {
                    "broad_count": report.broad_count,
                    "optimized_candidate_count": report.optimized_count,
                    "safety_limit": report.safety_limit,
                    "blocked": True,
                }
            ],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.CONSTRAINT_SUMMARY,
            title="Constraint Summary",
            rows=[{"constraint_feature_count": _constraint_count(receipt, result_summary)}],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.CHUNK_SUMMARY,
            title="Chunk Summary",
            rows=chunk_rows,
            metadata={"chunks_planned": chunks_planned},
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.GROUPED_ATTRIBUTE_SUMMARY,
            title="Grouped Attribute Summaries",
            status="ok" if any(row.get("status") == "ok" for row in grouped) else "unsupported",
            rows=grouped,
            notes=["Grouped summaries use ArcGIS REST statistics with returnGeometry=false when supported."],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.SAFETY_SUMMARY,
            title="Safety Summary",
            rows=[
                {
                    "safety_limit": report.safety_limit,
                    "geometry_downloaded": report.geometry_downloaded,
                    "geojson_created": report.geojson_created,
                    "published": False,
                }
            ],
            notes=[str(session.get("blocked_reason") or "")],
        ),
        AnalysisSummarySection(
            summary_type=AnalysisSummaryType.MISSING_DATA_SUMMARY,
            title="Missing Data Summary",
            rows=[{"missing_data": item} for item in report.missing_data],
        ),
    ]
    return report
