"""User-guided refinement for blocked AutoMap analysis runs."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.analysis_models import AnalysisLayerRef
from app.analysis_refinement_models import (
    AnalysisRefinementOption,
    AnalysisRefinementOptionType,
    AnalysisRefinementSafetyLevel,
    AnalysisRefinementSession,
)
from app.analysis_result_store import get_analysis_run
from app.analysis_safety import load_analysis_safety_limits, narrowing_suggestions
from app.db import _quote_identifier, get_engine
from app.field_profiler import load_field_profiles
from app.layer_catalog_store import load_catalog_records
from app.layer_semantics import slugify
from app.spatial_query_client import SpatialQueryClient
from app.spatial_query_optimizer import optimize_intersection_query_plan
from app.ui_models import output_file_url, repo_root


REFINEMENT_OUTPUT_ROOT = Path("outputs/analysis_refinements")
PROTECTED_REFINEMENT_MARKERS = {
    ".env",
    "arcgis_password",
    "arcgis_username",
    "database_url",
    "password",
    "postgres_admin_url",
    "secret",
    "token",
    "cfs_dev",
}


def _refinement_table(schema_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.analysis_refinement_sessions"


def init_refinement_tables(schema_name: str = "automap") -> None:
    """Create additive AutoMap refinement tables safely."""
    table = _refinement_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(schema_name)};"))
        connection.execute(
            text(
                f"""
                CREATE TABLE IF NOT EXISTS {table} (
                    id serial PRIMARY KEY,
                    session_id text UNIQUE,
                    source_analysis_run_id text,
                    raw_prompt text,
                    blocked_reason text,
                    broad_count integer,
                    optimized_count integer,
                    safety_limit integer,
                    options jsonb DEFAULT '[]'::jsonb,
                    selected_option jsonb DEFAULT '{{}}'::jsonb,
                    selected_parameters jsonb DEFAULT '{{}}'::jsonb,
                    refined_plan jsonb DEFAULT '{{}}'::jsonb,
                    refined_result jsonb DEFAULT '{{}}'::jsonb,
                    status text DEFAULT 'open',
                    created_at timestamptz DEFAULT now(),
                    updated_at timestamptz DEFAULT now()
                );
                """
            )
        )
        for column, column_type in {
            "session_id": "text UNIQUE",
            "source_analysis_run_id": "text",
            "raw_prompt": "text",
            "blocked_reason": "text",
            "broad_count": "integer",
            "optimized_count": "integer",
            "safety_limit": "integer",
            "options": "jsonb DEFAULT '[]'::jsonb",
            "selected_option": "jsonb DEFAULT '{}'::jsonb",
            "selected_parameters": "jsonb DEFAULT '{}'::jsonb",
            "refined_plan": "jsonb DEFAULT '{}'::jsonb",
            "refined_result": "jsonb DEFAULT '{}'::jsonb",
            "status": "text DEFAULT 'open'",
            "created_at": "timestamptz DEFAULT now()",
            "updated_at": "timestamptz DEFAULT now()",
        }.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))


def _output_root() -> Path:
    root = REFINEMENT_OUTPUT_ROOT
    return root if root.is_absolute() else repo_root() / root


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


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


def _store_session(session: dict[str, Any], schema_name: str = "automap") -> dict[str, Any]:
    init_refinement_tables(schema_name)
    table = _refinement_table(schema_name)
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    session_id, source_analysis_run_id, raw_prompt, blocked_reason,
                    broad_count, optimized_count, safety_limit, options,
                    selected_option, selected_parameters, refined_plan, refined_result,
                    status, updated_at
                )
                VALUES (
                    :session_id, :source_analysis_run_id, :raw_prompt, :blocked_reason,
                    :broad_count, :optimized_count, :safety_limit, CAST(:options AS jsonb),
                    CAST(:selected_option AS jsonb), CAST(:selected_parameters AS jsonb),
                    CAST(:refined_plan AS jsonb), CAST(:refined_result AS jsonb),
                    :status, now()
                )
                ON CONFLICT (session_id) DO UPDATE SET
                    source_analysis_run_id = EXCLUDED.source_analysis_run_id,
                    raw_prompt = EXCLUDED.raw_prompt,
                    blocked_reason = EXCLUDED.blocked_reason,
                    broad_count = EXCLUDED.broad_count,
                    optimized_count = EXCLUDED.optimized_count,
                    safety_limit = EXCLUDED.safety_limit,
                    options = EXCLUDED.options,
                    selected_option = EXCLUDED.selected_option,
                    selected_parameters = EXCLUDED.selected_parameters,
                    refined_plan = EXCLUDED.refined_plan,
                    refined_result = EXCLUDED.refined_result,
                    status = EXCLUDED.status,
                    updated_at = now();
                """
            ),
            {
                "session_id": session.get("session_id"),
                "source_analysis_run_id": session.get("source_analysis_run_id"),
                "raw_prompt": session.get("raw_prompt"),
                "blocked_reason": session.get("blocked_reason"),
                "broad_count": session.get("broad_count"),
                "optimized_count": session.get("optimized_count"),
                "safety_limit": session.get("safety_limit"),
                "options": json.dumps(session.get("options") or [], default=str),
                "selected_option": json.dumps(session.get("selected_option") or {}, default=str),
                "selected_parameters": json.dumps(session.get("selected_parameters") or {}, default=str),
                "refined_plan": json.dumps(session.get("refined_plan") or {}, default=str),
                "refined_result": json.dumps(session.get("refined_result") or {}, default=str),
                "status": session.get("status") or "open",
            },
        )
    return session


def _row_to_session(row: Any) -> dict[str, Any]:
    data = dict(row)
    for key in ["options", "selected_option", "selected_parameters", "refined_plan", "refined_result"]:
        if key == "options":
            data[key] = _json_list(data.get(key))
        else:
            data[key] = _json_dict(data.get(key))
    for key in ["created_at", "updated_at"]:
        if data.get(key) is not None:
            data[key] = str(data[key])
    return data


def get_refinement_session(session_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Return one refinement session."""
    init_refinement_tables(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT *
                FROM {_refinement_table(schema_name)}
                WHERE session_id = :session_id;
                """
            ),
            {"session_id": session_id},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"Analysis refinement session not found: {session_id}")
    return _row_to_session(row)


def list_refinement_sessions(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List recent refinement sessions."""
    init_refinement_tables(schema_name)
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT *
                FROM {_refinement_table(schema_name)}
                ORDER BY updated_at DESC, id DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
        return [_row_to_session(row) for row in rows]


def _analysis_receipt_from_run(run: dict[str, Any]) -> dict[str, Any]:
    return _json_dict(run.get("analysis_receipt"))


def _recipe_from_run(run: dict[str, Any]) -> dict[str, Any]:
    return _json_dict(run.get("recipe_json"))


def _optimized_plan(receipt: dict[str, Any]) -> dict[str, Any]:
    return _json_dict(receipt.get("optimized_query_plan"))


def _broad_count(receipt: dict[str, Any]) -> int | None:
    value = receipt.get("broad_count") or _optimized_plan(receipt).get("broad_count")
    return int(value) if isinstance(value, (int, float)) else None


def _optimized_count(receipt: dict[str, Any]) -> int | None:
    value = receipt.get("optimized_candidate_count") or _optimized_plan(receipt).get("optimized_candidate_count")
    return int(value) if isinstance(value, (int, float)) else None


def _safety_limit(receipt: dict[str, Any]) -> int:
    optimized = _optimized_plan(receipt)
    limits = _json_dict(receipt.get("max_feature_limits")) or _json_dict(optimized.get("safety_limits"))
    return int(
        limits.get("run_max_features")
        or limits.get("max_download_features_per_layer")
        or load_analysis_safety_limits()["max_download_features_per_layer"]
    )


def _blocked_reason(receipt: dict[str, Any]) -> str:
    reasons = _json_list(receipt.get("blocked_reasons"))
    if reasons:
        return str(reasons[0])
    optimized = _optimized_plan(receipt)
    reasons = _json_list(optimized.get("blocked_reasons"))
    return str(reasons[0]) if reasons else "Analysis exceeded safety limits."


def _target_layer_key(receipt: dict[str, Any]) -> str | None:
    target = _json_dict(receipt.get("target_layer")) or _json_dict(_optimized_plan(receipt).get("target_layer"))
    return target.get("layer_key")


def _target_layer_from_run(run: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    target_key = _target_layer_key(receipt)
    for record in load_catalog_records():
        if record.get("layer_key") == target_key:
            return record
    target = _json_dict(receipt.get("target_layer")) or _json_dict(_optimized_plan(receipt).get("target_layer"))
    return target


def _candidate_fields(layer_record: dict[str, Any]) -> list[dict[str, Any]]:
    layer_key = layer_record.get("layer_key")
    fields = [field for field in layer_record.get("fields") or [] if isinstance(field, dict)]
    profile_rows = load_field_profiles([layer_key]) if layer_key else {}
    profiled = profile_rows.get(layer_key) or []
    by_name = {field.get("name"): field for field in fields if field.get("name")}
    for profile in profiled:
        name = profile.get("field_name")
        if not name:
            continue
        by_name.setdefault(
            name,
            {
                "name": name,
                "alias": profile.get("field_alias"),
                "type": profile.get("field_type"),
            },
        )
    return list(by_name.values())


def _attribute_suggestions(layer_record: dict[str, Any]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for field in _candidate_fields(layer_record):
        name = str(field.get("name") or "")
        alias = str(field.get("alias") or "")
        field_type = str(field.get("type") or "")
        search = f"{name} {alias}".lower()
        if not name:
            continue
        if any(term in search for term in ["acre", "area", "landunits"]):
            suggestions.append(
                {
                    "field_name": name,
                    "label": f"{alias or name} over 1 acre",
                    "where": f"{name} > 1",
                    "reason": "Real acreage/area field found on the target layer.",
                    "field_type": field_type,
                }
            )
            suggestions.append(
                {
                    "field_name": name,
                    "label": f"{alias or name} over 5 acres",
                    "where": f"{name} > 5",
                    "reason": "Real acreage/area field found on the target layer.",
                    "field_type": field_type,
                }
            )
        elif any(term in search for term in ["zone", "zoning", "use", "class", "code", "type"]):
            suggestions.append(
                {
                    "field_name": name,
                    "label": f"Filter by {alias or name}",
                    "where": f"{name} = '<review_value>'",
                    "reason": "Real category field found on the target layer.",
                    "field_type": field_type,
                }
            )
        elif any(term in search for term in ["municip", "district", "city", "town"]):
            suggestions.append(
                {
                    "field_name": name,
                    "label": f"Filter by {alias or name}",
                    "where": f"{name} = '<review_value>'",
                    "reason": "Real geography/district field found on the target layer.",
                    "field_type": field_type,
                }
            )
    return suggestions[:8]


def generate_refinement_options(blocked_receipt: dict[str, Any], run: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Generate deterministic refinement options for a blocked analysis receipt."""
    receipt = _json_dict(blocked_receipt)
    optimized_count = _optimized_count(receipt)
    broad_count = _broad_count(receipt)
    safety_limit = _safety_limit(receipt)
    optimized = _optimized_plan(receipt)
    chunks = _json_list(optimized.get("chunk_receipts"))
    limits = load_analysis_safety_limits(safety_limit)
    options: list[AnalysisRefinementOption] = [
        AnalysisRefinementOption(
            option_id="summary_only",
            option_type=AnalysisRefinementOptionType.SUMMARY_ONLY,
            label="Return summary only",
            description="Return counts, strategy details, chunks, and review notes without downloading parcel geometry.",
            estimated_count=optimized_count,
            expected_output="local Markdown/JSON summary; no GeoJSON",
            safety_level=AnalysisRefinementSafetyLevel.SAFE,
            tradeoffs=["No parcel geometries or map layer are produced.", "Best for scoping and leadership review."],
            recommended=True,
        )
    ]

    if chunks:
        max_chunk = max(int(chunk.get("deduplicated_candidate_count") or 0) for chunk in chunks)
        total = int(optimized_count or 0)
        options.append(
            AnalysisRefinementOption(
                option_id="split_batches",
                option_type=AnalysisRefinementOptionType.SPLIT_BATCHES,
                label="Split into smaller batches",
                description="Plan reviewable batches from existing optimizer chunks instead of one large geometry download.",
                estimated_count=optimized_count,
                expected_output="batch_plan.json and batch_receipt.json",
                safety_level=(
                    AnalysisRefinementSafetyLevel.REVIEW_NEEDED
                    if max_chunk <= safety_limit and total <= limits["hard_max_download_features"]
                    else AnalysisRefinementSafetyLevel.BLOCKED
                ),
                required_user_input=["Select one safe batch to execute later if geometry is needed."],
                suggested_parameters={
                    "max_batch_count": safety_limit,
                    "execute_first_batch": False,
                    "chunk_count": len(chunks),
                    "largest_chunk_count": max_chunk,
                    "total_candidate_count": total,
                },
                tradeoffs=[
                    "Does not silently download all batches.",
                    "A future one-batch execution should be reviewed before geometry download.",
                ],
            )
        )

    constraint_name = str((_json_dict(receipt.get("constraint_layer")) or _json_dict(optimized.get("constraint_layer"))).get("layer_name") or "")
    is_already_specific = any(term in constraint_name.lower() for term in ["100", "500", "floodway"])
    options.append(
        AnalysisRefinementOption(
            option_id="narrow_constraint",
            option_type=AnalysisRefinementOptionType.NARROW_CONSTRAINT,
            label="Narrow flood hazard subtype",
            description=(
                "Choose a narrower flood hazard subset."
                if not is_already_specific
                else "The current request already uses a specific flood hazard layer; another subtype would change the request."
            ),
            estimated_count=optimized_count,
            expected_output="refined plan only",
            safety_level=AnalysisRefinementSafetyLevel.REVIEW_NEEDED if not is_already_specific else AnalysisRefinementSafetyLevel.BLOCKED,
            required_user_input=["Select FloodWay, FloodPlain100year, FloodPlain500year, or a reviewed combination."],
            suggested_parameters={
                "choices": ["FloodWay", "FloodPlain100year", "FloodPlain500year", "FloodWay + FloodPlain100year"],
                "current_constraint_layer": constraint_name,
                "applicable": not is_already_specific,
            },
            tradeoffs=["Changing the flood hazard subtype changes the meaning of the map."],
        )
    )

    if run:
        layer_record = _target_layer_from_run(run, receipt)
        suggestions = _attribute_suggestions(layer_record)
        if suggestions:
            options.append(
                AnalysisRefinementOption(
                    option_id="attribute_filter",
                    option_type=AnalysisRefinementOptionType.ATTRIBUTE_FILTER,
                    label="Add a parcel attribute filter",
                    description="Use real target-layer fields to narrow candidate parcels before geometry download.",
                    estimated_count=optimized_count,
                    expected_output="refined count-only plan",
                    safety_level=AnalysisRefinementSafetyLevel.REVIEW_NEEDED,
                    required_user_input=["Choose a field and value/threshold."],
                    suggested_parameters={"filters": suggestions},
                    tradeoffs=["Filters can exclude relevant parcels if assumptions are too aggressive."],
                )
            )

    options.append(
        AnalysisRefinementOption(
            option_id="smaller_geography",
            option_type=AnalysisRefinementOptionType.SMALLER_GEOGRAPHY,
            label="Use a smaller geography",
            description="Split the requested geography into review tiles or choose a smaller area.",
            estimated_count=optimized_count,
            expected_output="tile guidance and refined plan",
            safety_level=AnalysisRefinementSafetyLevel.REVIEW_NEEDED,
            required_user_input=["Choose north, south, east, west, or a smaller named geography."],
            suggested_parameters={"tile_options": ["north", "south", "east", "west"], "manual_boundary_supported": False},
            tradeoffs=["Tile boundaries are operational review aids, not official municipal boundaries."],
        )
    )

    if optimized_count is not None and optimized_count <= limits["hard_max_download_features"]:
        options.append(
            AnalysisRefinementOption(
                option_id="object_id_only",
                option_type=AnalysisRefinementOptionType.OBJECT_ID_ONLY,
                label="Export ObjectID list only",
                description="Return selected parcel ObjectIDs without downloading parcel geometry.",
                estimated_count=optimized_count,
                expected_output="object_id_list.json if ObjectIDs are available",
                safety_level=AnalysisRefinementSafetyLevel.SAFE,
                tradeoffs=["Useful for audit/review, but not a map layer."],
            )
        )

    if not options:
        options.append(
            AnalysisRefinementOption(
                option_id="unsupported",
                option_type=AnalysisRefinementOptionType.UNSUPPORTED,
                label="Unsupported refinement",
                description="AutoMap could not identify a safe refinement path.",
                safety_level=AnalysisRefinementSafetyLevel.BLOCKED,
                tradeoffs=narrowing_suggestions(),
            )
        )
    return [option.to_dict() for option in options]


def create_refinement_session_from_blocked_run(analysis_run_id: str) -> dict[str, Any]:
    """Create a refinement session from a blocked analysis run."""
    run = get_analysis_run(analysis_run_id)
    receipt = _analysis_receipt_from_run(run)
    if (run.get("status") or receipt.get("status")) != "blocked":
        raise ValueError("Analysis refinement requires a blocked analysis run.")
    session = AnalysisRefinementSession(
        session_id=f"refine_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:8]}",
        source_analysis_run_id=analysis_run_id,
        raw_prompt=str(run.get("raw_prompt") or receipt.get("raw_prompt") or ""),
        blocked_reason=_blocked_reason(receipt),
        broad_count=_broad_count(receipt),
        optimized_count=_optimized_count(receipt),
        safety_limit=_safety_limit(receipt),
        options=generate_refinement_options(receipt, run),
    ).to_dict()
    return _store_session(session)


def select_refinement_option(session_id: str, option_id: str, parameters: dict[str, Any] | None = None) -> dict[str, Any]:
    """Store the selected refinement option and user parameters."""
    session = get_refinement_session(session_id)
    selected = next((option for option in session.get("options") or [] if option.get("option_id") == option_id), None)
    if not selected:
        raise ValueError(f"Refinement option not found: {option_id}")
    session["selected_option"] = selected
    session["selected_parameters"] = parameters or {}
    session["status"] = "selected"
    session["updated_at"] = datetime.now(UTC).isoformat()
    return _store_session(session)


def _summary_payload(session: dict[str, Any], run: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    optimized = _optimized_plan(receipt)
    return {
        "session_id": session["session_id"],
        "source_analysis_run_id": session["source_analysis_run_id"],
        "raw_prompt": session.get("raw_prompt"),
        "blocked_reason": session.get("blocked_reason"),
        "broad_count": session.get("broad_count"),
        "optimized_count": session.get("optimized_count"),
        "safety_limit": session.get("safety_limit"),
        "strategy": receipt.get("query_strategy") or optimized.get("strategy"),
        "strategy_explanation": receipt.get("strategy_explanation") or optimized.get("strategy_explanation"),
        "constraint_feature_count": receipt.get("constraint_feature_count") or optimized.get("constraint_feature_count"),
        "chunks_planned": receipt.get("chunks_used") or optimized.get("chunks_planned"),
        "chunk_receipts": optimized.get("chunk_receipts") or receipt.get("chunk_receipts") or [],
        "selected_object_id_count": receipt.get("object_ids_selected_count") or optimized.get("optimized_candidate_count"),
        "geometry_downloaded": False,
        "geojson_created": False,
        "published": False,
        "protected_external_database_touched": False,
        "narrowing_suggestions": receipt.get("narrowing_suggestions") or optimized.get("narrowing_suggestions") or narrowing_suggestions(),
        "available_attribute_filters": _attribute_suggestions(_target_layer_from_run(run, receipt)),
    }


def _write_refinement_outputs(
    session: dict[str, Any],
    *,
    summary: dict[str, Any],
    receipt: dict[str, Any],
    extra_files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    title = session.get("raw_prompt") or session["session_id"]
    folder = _output_root() / f"{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}_{slugify(title)[:90]}"
    folder.mkdir(parents=True, exist_ok=True)
    _write_json(folder / "refinement_summary.json", summary)
    _write_json(folder / "refinement_receipt.json", receipt)
    lines = [
        f"# AutoMap Analysis Refinement {session['session_id']}",
        "",
        f"- Source analysis run: {session['source_analysis_run_id']}",
        f"- Selected option: {(session.get('selected_option') or {}).get('option_id')}",
        f"- Broad count: {summary.get('broad_count')}",
        f"- Optimized count: {summary.get('optimized_count')}",
        f"- Safety limit: {summary.get('safety_limit')}",
        f"- Geometry downloaded: {summary.get('geometry_downloaded')}",
        "- Publishing: no ArcGIS item was created and nothing was uploaded.",
        "- Protected external planning database was not touched.",
        "",
        "## Narrowing Suggestions",
    ]
    lines.extend(f"- {item}" for item in summary.get("narrowing_suggestions") or [])
    (folder / "refinement_summary.md").write_text("\n".join(lines), encoding="utf-8")
    for file_name, payload in (extra_files or {}).items():
        _write_json(folder / file_name, payload)
    relative_folder = folder.relative_to(repo_root()).as_posix()
    files = {
        "refinement_summary_json": f"{relative_folder}/refinement_summary.json",
        "refinement_summary_md": f"{relative_folder}/refinement_summary.md",
        "refinement_receipt": f"{relative_folder}/refinement_receipt.json",
    }
    for file_name in extra_files or {}:
        files[file_name] = f"{relative_folder}/{file_name}"
    return {
        "output_folder": relative_folder,
        "files": files,
        "links": {key: output_file_url(path) for key, path in files.items()},
    }


def build_refined_analysis_plan(session_id: str) -> dict[str, Any]:
    """Build a refined analysis plan for the selected option."""
    session = get_refinement_session(session_id)
    option = session.get("selected_option") or {}
    if not option:
        raise ValueError("Select a refinement option before building a refined plan.")
    params = session.get("selected_parameters") or {}
    option_id = option.get("option_id")
    plan = {
        "session_id": session_id,
        "option_id": option_id,
        "option_type": option.get("option_type"),
        "parameters": params,
        "will_download_geometry": False,
        "safety_limit": session.get("safety_limit"),
        "estimated_count": option.get("estimated_count"),
        "status": "planned",
    }
    if option_id == "summary_only":
        plan.update({"execution_mode": "summary_only", "expected_output": "counts and review summary"})
    elif option_id == "split_batches":
        chunk_count = (option.get("suggested_parameters") or {}).get("chunk_count")
        plan.update({"execution_mode": "batch_plan_only", "batch_count": chunk_count, "expected_output": "batch plan"})
    elif option_id == "object_id_only":
        plan.update({"execution_mode": "object_id_only", "expected_output": "ObjectID list only"})
    else:
        plan.update({"execution_mode": "plan_only", "expected_output": option.get("expected_output")})
    session["refined_plan"] = plan
    session["status"] = "planned"
    _store_session(session)
    return plan


def _execute_summary_only(session: dict[str, Any], run: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    summary = _summary_payload(session, run, receipt)
    refinement_receipt = {
        "session_id": session["session_id"],
        "source_analysis_run_id": session["source_analysis_run_id"],
        "status": "completed",
        "mode": "summary_only",
        "geometry_downloaded": False,
        "geojson_created": False,
        "summary_only": True,
        "published": False,
        "protected_external_database_touched": False,
        "no_publish_statement": "No ArcGIS item was created, uploaded, shared, overwritten, or deleted.",
    }
    outputs = _write_refinement_outputs(session, summary=summary, receipt=refinement_receipt)
    return {
        "status": "completed",
        "mode": "summary_only",
        "summary": summary,
        "receipt": refinement_receipt,
        **outputs,
    }


def _execute_split_batches(session: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    optimized = _optimized_plan(receipt)
    chunks = _json_list(optimized.get("chunk_receipts"))
    hard_max = load_analysis_safety_limits(session.get("safety_limit"))["hard_max_download_features"]
    total = int(session.get("optimized_count") or 0)
    batch_plan = {
        "session_id": session["session_id"],
        "mode": "split_batches",
        "batch_count": len(chunks),
        "total_candidate_count": total,
        "hard_max_download_features": hard_max,
        "all_batches_auto_execute_allowed": total <= hard_max,
        "batches": chunks,
        "geometry_downloaded": False,
        "note": "v2.2 creates a safe batch plan only; one-batch geometry execution requires later explicit review.",
    }
    receipt_payload = {
        "session_id": session["session_id"],
        "status": "planned",
        "mode": "split_batches",
        "geometry_downloaded": False,
        "published": False,
        "protected_external_database_touched": False,
    }
    outputs = _write_refinement_outputs(
        session,
        summary=batch_plan,
        receipt=receipt_payload,
        extra_files={"batch_plan.json": batch_plan, "batch_receipt.json": receipt_payload},
    )
    return {"status": "planned", "mode": "split_batches", "batch_plan": batch_plan, "receipt": receipt_payload, **outputs}


def _execute_object_id_only(session: dict[str, Any], run: dict[str, Any], receipt: dict[str, Any]) -> dict[str, Any]:
    recipe = _recipe_from_run(run)
    optimized = _optimized_plan(receipt)
    target = _json_dict(optimized.get("target_layer"))
    geography = _json_dict(optimized.get("geography_layer"))
    constraint = _json_dict(optimized.get("constraint_layer"))
    if not (recipe and target and geography and constraint):
        raise ValueError("ObjectID-only export requires stored optimizer layer metadata.")
    plan = optimize_intersection_query_plan(
        recipe,
        AnalysisLayerRef.from_layer(target),
        AnalysisLayerRef.from_layer(geography),
        AnalysisLayerRef.from_layer(constraint),
        query_client=SpatialQueryClient(max_features=session.get("safety_limit") or 2000),
        max_features=session.get("safety_limit") or 2000,
        include_object_ids=True,
    )
    object_ids = plan.get("candidate_object_ids") or []
    hard_max = load_analysis_safety_limits(session.get("safety_limit"))["hard_max_download_features"]
    if len(object_ids) > hard_max:
        raise ValueError(f"ObjectID-only export count {len(object_ids)} exceeds hard max {hard_max}.")
    summary = {
        "session_id": session["session_id"],
        "mode": "object_id_only",
        "object_id_count": len(object_ids),
        "geometry_downloaded": False,
        "geojson_created": False,
    }
    receipt_payload = {
        **summary,
        "status": "completed",
        "published": False,
        "protected_external_database_touched": False,
        "no_publish_statement": "No ArcGIS item was created, uploaded, shared, overwritten, or deleted.",
    }
    outputs = _write_refinement_outputs(
        session,
        summary=summary,
        receipt=receipt_payload,
        extra_files={"object_id_list.json": {"object_ids": object_ids, "count": len(object_ids)}},
    )
    return {"status": "completed", "mode": "object_id_only", "summary": summary, "receipt": receipt_payload, **outputs}


def execute_refined_analysis(session_id: str) -> dict[str, Any]:
    """Execute the selected refinement option if it is safe and supported."""
    session = get_refinement_session(session_id)
    option = session.get("selected_option") or {}
    if not option:
        raise ValueError("Select a refinement option before executing refinement.")
    run = get_analysis_run(session["source_analysis_run_id"])
    receipt = _analysis_receipt_from_run(run)
    if not session.get("refined_plan"):
        session["refined_plan"] = build_refined_analysis_plan(session_id)
        session = get_refinement_session(session_id)
    option_id = option.get("option_id")
    if option_id == "summary_only":
        result = _execute_summary_only(session, run, receipt)
    elif option_id == "split_batches":
        result = _execute_split_batches(session, receipt)
    elif option_id == "object_id_only":
        result = _execute_object_id_only(session, run, receipt)
    else:
        result = {
            "status": "blocked",
            "mode": option_id,
            "blocked_reasons": ["This refinement option is planning-only in v2.2."],
            "geometry_downloaded": False,
            "published": False,
        }
    session["refined_result"] = result
    session["status"] = result.get("status") or "completed"
    session["updated_at"] = datetime.now(UTC).isoformat()
    return _store_session(session)


def summarize_refinement_result(session_id: str) -> dict[str, Any]:
    """Return a compact summary for a refinement session."""
    session = get_refinement_session(session_id)
    result = session.get("refined_result") or {}
    return {
        "session_id": session_id,
        "status": session.get("status"),
        "selected_option": (session.get("selected_option") or {}).get("option_id"),
        "broad_count": session.get("broad_count"),
        "optimized_count": session.get("optimized_count"),
        "safety_limit": session.get("safety_limit"),
        "output_folder": result.get("output_folder"),
        "geometry_downloaded": result.get("geometry_downloaded", False)
        or (result.get("summary") or {}).get("geometry_downloaded", False),
    }


def validate_refinement_output(refinement_folder: str | Path) -> dict[str, Any]:
    """Validate a local refinement output folder."""
    path = Path(refinement_folder)
    errors: list[str] = []
    if not path.exists():
        errors.append(f"Refinement folder not found: {path}")
    for file_name in ["refinement_summary.json", "refinement_summary.md", "refinement_receipt.json"]:
        if path.exists() and not (path / file_name).exists():
            errors.append(f"Missing required refinement output: {file_name}")
    combined = ""
    if path.exists():
        for file_path in path.glob("*"):
            if file_path.is_file():
                combined += file_path.read_text(encoding="utf-8", errors="ignore").lower()
    for marker in PROTECTED_REFINEMENT_MARKERS:
        if marker in combined:
            errors.append(f"Refinement output contains protected marker: {marker}")
    if path.exists() and (path / "refinement_summary.json").exists():
        try:
            summary = json.loads((path / "refinement_summary.json").read_text(encoding="utf-8"))
            receipt = (
                json.loads((path / "refinement_receipt.json").read_text(encoding="utf-8"))
                if (path / "refinement_receipt.json").exists()
                else {}
            )
            if receipt.get("mode") == "summary_only" and summary.get("geometry_downloaded") is True:
                errors.append("Summary-only refinement should not download geometry.")
        except json.JSONDecodeError:
            errors.append("Refinement output JSON could not be parsed.")
    return {"is_valid": not errors, "errors": errors, "refinement_folder": str(path)}
