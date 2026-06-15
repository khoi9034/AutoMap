"""Interactive clarification loop for AutoMap requests."""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
import json
from typing import Any
from uuid import uuid4

from sqlalchemy import text

from app.clarification_models import (
    ClarificationAnswer,
    ClarificationQuestion,
    ClarificationSession,
)
from app.db import _quote_identifier, get_engine
from app.filter_planner import build_filter_plan, validate_filter_plan
from app.recipe_engine import build_recipe


CLARIFICATION_SESSION_COLUMNS = {
    "session_id": "text UNIQUE",
    "raw_prompt": "text",
    "initial_recipe": "jsonb",
    "questions": "jsonb",
    "answers": "jsonb",
    "refined_prompt": "text",
    "refined_request_context": "jsonb",
    "refined_recipe": "jsonb",
    "changes_summary": "jsonb",
    "status": "text DEFAULT 'open'",
    "created_at": "timestamptz DEFAULT now()",
    "updated_at": "timestamptz DEFAULT now()",
}


def _qualified_table(schema_name: str, table_name: str) -> str:
    return f"{_quote_identifier(schema_name)}.{table_name}"


def ensure_clarification_sessions_table(schema_name: str = "automap") -> None:
    """Create or safely update the AutoMap clarification session table."""
    schema = _quote_identifier(schema_name)
    table = _qualified_table(schema_name, "clarification_sessions")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema};"))
        connection.execute(text(f"CREATE TABLE IF NOT EXISTS {table} (id serial PRIMARY KEY);"))
        for column, column_type in CLARIFICATION_SESSION_COLUMNS.items():
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {column_type};"))
        connection.execute(
            text(
                f"""
                CREATE UNIQUE INDEX IF NOT EXISTS clarification_sessions_session_id_uidx
                ON {table} (session_id);
                """
            )
        )


def _json_text(value: Any) -> str:
    return json.dumps(value, default=str)


def _load_jsonb(value: Any, fallback: Any) -> Any:
    if value is None:
        return fallback
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return fallback
    return value


def _row_to_session(row: dict[str, Any]) -> dict[str, Any]:
    return ClarificationSession(
        session_id=row["session_id"],
        raw_prompt=row.get("raw_prompt") or "",
        initial_recipe=_load_jsonb(row.get("initial_recipe"), {}),
        questions=_load_jsonb(row.get("questions"), []),
        answers=_load_jsonb(row.get("answers"), []),
        refined_prompt=row.get("refined_prompt"),
        refined_request_context=_load_jsonb(row.get("refined_request_context"), {}),
        refined_recipe=_load_jsonb(row.get("refined_recipe"), None),
        changes_summary=_load_jsonb(row.get("changes_summary"), {}),
        status=row.get("status") or "open",
        created_at=str(row.get("created_at") or ""),
        updated_at=str(row.get("updated_at") or ""),
    ).to_dict()


def _answer_value_text(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return value.get("label") or value.get("value") or json.dumps(value, default=str)
    return str(value)


def _question_from_base_question(item: dict[str, Any]) -> ClarificationQuestion | None:
    question = str(item.get("question") or "").lower()
    if "distance should count as near" in question:
        return ClarificationQuestion(
            question_id="near_distance",
            question_text="What distance should count as near?",
            question_type="distance",
            options=[
                {"value": "500_feet", "label": "500 feet", "distance": {"value": 500, "unit": "feet"}},
                {"value": "0.25_miles", "label": "0.25 miles", "distance": {"value": 0.25, "unit": "miles"}},
                {"value": "0.5_miles", "label": "0.5 miles", "distance": {"value": 0.5, "unit": "miles"}},
                {"value": "custom", "label": "Custom distance"},
            ],
            default_answer="0.5_miles",
            required=True,
            related_intent="proximity",
            related_filter="distance",
            blocking_level="review_needed",
            help_text="Used to make buffer/proximity steps explicit in the analysis plan.",
        )
    if "time range should count as recent" in question:
        return ClarificationQuestion(
            question_id="recent_time_range",
            question_text="What time range should count as recent?",
            question_type="date_range",
            options=[
                {"value": "last_1_year", "label": "Last 1 year"},
                {"value": "last_3_years", "label": "Last 3 years"},
                {"value": "last_5_years", "label": "Last 5 years"},
                {"value": "custom", "label": "Custom range"},
            ],
            default_answer="last_3_years",
            required=True,
            related_intent="development_activity",
            related_filter="date_range",
            blocking_level="review_needed",
            help_text="AutoMap still needs a verified date field before final use.",
        )
    if "zoning codes should count as commercial" in question:
        return ClarificationQuestion(
            question_id="commercial_zoning_codes",
            question_text="Which zoning codes should count as commercial?",
            question_type="multi_choice",
            options=[
                {"value": "general_commercial", "label": "Use general commercial categories"},
                {"value": "office_commercial", "label": "Office/commercial districts"},
                {"value": "custom", "label": "Custom zoning code list"},
            ],
            default_answer=["general_commercial"],
            required=False,
            related_intent="zoning_review",
            related_filter="zoning_code",
            blocking_level="review_needed",
            help_text="If available, AutoMap can draft a commercial-style ZONING_GEN filter.",
        )
    if "prioritize for suitability" in question:
        return ClarificationQuestion(
            question_id="suitability_priorities",
            question_text="Which factors should AutoMap prioritize for suitability?",
            question_type="multi_choice",
            options=[
                {"value": "zoning", "label": "Zoning"},
                {"value": "road_access", "label": "Road access"},
                {"value": "flood_avoidance", "label": "Flood avoidance"},
                {"value": "parcel_size", "label": "Parcel size"},
                {"value": "development_activity", "label": "Development activity"},
            ],
            default_answer=["zoning", "road_access", "flood_avoidance"],
            required=False,
            related_intent="growth_suitability",
            related_filter="suitability",
            blocking_level="review_needed",
            help_text="Suitability weights remain reviewer-defined in this phase.",
        )
    if "missing current development activity data" in question:
        return ClarificationQuestion(
            question_id="missing_development_data_decision",
            question_text="How should AutoMap handle missing current development activity data?",
            question_type="single_choice",
            options=[
                {"value": "mark_missing", "label": "Mark current development activity as missing"},
                {"value": "use_legacy_fallback", "label": "Use verified legacy fallback if available"},
                {"value": "continue_without_topic", "label": "Continue without development activity"},
                {"value": "stop_unsupported", "label": "Stop recipe as unsupported"},
            ],
            default_answer="mark_missing",
            required=True,
            related_intent="development_activity",
            related_filter="missing_data",
            blocking_level="review_needed",
            help_text="AutoMap records the decision and does not invent a current source.",
        )
    if "historical year" in question:
        return ClarificationQuestion(
            question_id="historical_year",
            question_text="Which historical year or archive period should be compared?",
            question_type="year",
            options=[
                {"value": 2014, "label": "2014"},
                {"value": 2015, "label": "2015"},
                {"value": "custom", "label": "Custom year"},
            ],
            default_answer=2014,
            required=True,
            related_intent="historical_comparison",
            related_filter="historical_year",
            blocking_level="review_needed",
            help_text="Only approved historical catalog layers can be used.",
        )
    return None


def _needs_flood_scope_question(recipe: dict[str, Any]) -> bool:
    parsed = recipe.get("parsed_request") or {}
    if parsed.get("topic_details", {}).get("flood_frequency"):
        return False
    selected_flood_layers = [
        layer for layer in recipe.get("selected_layers") or []
        if layer.get("category") == "flood"
    ]
    intents = set((recipe.get("request_intelligence") or {}).get("detected_intents") or [])
    return "flood_exposure" in intents and len(selected_flood_layers) > 1


def extract_clarification_questions(recipe: dict[str, Any]) -> list[dict[str, Any]]:
    """Build typed clarification questions from recipe intelligence."""
    source_questions = (recipe.get("request_intelligence") or {}).get("clarifying_questions") or []
    questions: list[ClarificationQuestion] = []
    seen: set[str] = set()
    for item in source_questions:
        model = _question_from_base_question(item)
        if model and model.question_id not in seen:
            questions.append(model)
            seen.add(model.question_id)

    if _needs_flood_scope_question(recipe) and "flood_layer_scope" not in seen:
        questions.append(
            ClarificationQuestion(
                question_id="flood_layer_scope",
                question_text="Which flood hazard layers should be included?",
                question_type="multi_choice",
                options=[
                    {"value": "floodway", "label": "Floodway"},
                    {"value": "100_year", "label": "100-year floodplain"},
                    {"value": "500_year", "label": "500-year floodplain"},
                    {"value": "all_flood_hazard", "label": "All flood hazard layers"},
                ],
                default_answer=["floodway", "100_year", "500_year"],
                required=True,
                related_intent="flood_exposure",
                related_filter="flood_scope",
                blocking_level="review_needed",
                help_text="Used to narrow broad flood-zone requests to the intended verified sublayers.",
            )
        )
        seen.add("flood_layer_scope")

    return [question.to_dict() for question in questions]


def _insert_session(session: ClarificationSession, schema_name: str = "automap") -> None:
    ensure_clarification_sessions_table(schema_name)
    table = _qualified_table(schema_name, "clarification_sessions")
    engine = get_engine()
    data = session.to_dict()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                INSERT INTO {table} (
                    session_id, raw_prompt, initial_recipe, questions, answers,
                    refined_prompt, refined_request_context, refined_recipe,
                    changes_summary, status, created_at, updated_at
                )
                VALUES (
                    :session_id, :raw_prompt, CAST(:initial_recipe AS jsonb),
                    CAST(:questions AS jsonb), CAST(:answers AS jsonb),
                    :refined_prompt, CAST(:refined_request_context AS jsonb),
                    CAST(:refined_recipe AS jsonb), CAST(:changes_summary AS jsonb),
                    :status, now(), now()
                )
                ON CONFLICT (session_id) DO UPDATE SET
                    raw_prompt = EXCLUDED.raw_prompt,
                    initial_recipe = EXCLUDED.initial_recipe,
                    questions = EXCLUDED.questions,
                    answers = EXCLUDED.answers,
                    refined_prompt = EXCLUDED.refined_prompt,
                    refined_request_context = EXCLUDED.refined_request_context,
                    refined_recipe = EXCLUDED.refined_recipe,
                    changes_summary = EXCLUDED.changes_summary,
                    status = EXCLUDED.status,
                    updated_at = now();
                """
            ),
            {
                **data,
                "initial_recipe": _json_text(data["initial_recipe"]),
                "questions": _json_text(data["questions"]),
                "answers": _json_text(data["answers"]),
                "refined_request_context": _json_text(data["refined_request_context"]),
                "refined_recipe": _json_text(data["refined_recipe"]),
                "changes_summary": _json_text(data["changes_summary"]),
            },
        )


def _update_session(session: dict[str, Any], schema_name: str = "automap") -> None:
    ensure_clarification_sessions_table(schema_name)
    table = _qualified_table(schema_name, "clarification_sessions")
    engine = get_engine()
    with engine.begin() as connection:
        connection.execute(
            text(
                f"""
                UPDATE {table}
                SET answers = CAST(:answers AS jsonb),
                    refined_prompt = :refined_prompt,
                    refined_request_context = CAST(:refined_request_context AS jsonb),
                    refined_recipe = CAST(:refined_recipe AS jsonb),
                    changes_summary = CAST(:changes_summary AS jsonb),
                    status = :status,
                    updated_at = now()
                WHERE session_id = :session_id;
                """
            ),
            {
                "session_id": session["session_id"],
                "answers": _json_text(session.get("answers") or []),
                "refined_prompt": session.get("refined_prompt"),
                "refined_request_context": _json_text(session.get("refined_request_context") or {}),
                "refined_recipe": _json_text(session.get("refined_recipe")),
                "changes_summary": _json_text(session.get("changes_summary") or {}),
                "status": session.get("status") or "open",
            },
        )


def create_clarification_session(
    raw_prompt: str,
    layer_catalog: list[dict[str, Any]] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Create a clarification session from a raw ambiguous prompt."""
    initial_recipe = build_recipe(raw_prompt, layer_catalog=layer_catalog, persist_data_gaps=persist)
    questions = extract_clarification_questions(initial_recipe)
    session = ClarificationSession(
        session_id=f"clarify_{uuid4().hex[:12]}",
        raw_prompt=raw_prompt,
        initial_recipe=initial_recipe,
        questions=questions,
        refined_prompt=raw_prompt,
        status="open" if questions else "no_questions",
    )
    if persist:
        _insert_session(session)
    return session.to_dict()


def get_clarification_session(session_id: str, schema_name: str = "automap") -> dict[str, Any]:
    """Load one clarification session by id."""
    ensure_clarification_sessions_table(schema_name)
    table = _qualified_table(schema_name, "clarification_sessions")
    engine = get_engine()
    with engine.connect() as connection:
        row = connection.execute(
            text(
                f"""
                SELECT session_id, raw_prompt, initial_recipe, questions, answers,
                       refined_prompt, refined_request_context, refined_recipe,
                       changes_summary, status, created_at, updated_at
                FROM {table}
                WHERE session_id = :session_id;
                """
            ),
            {"session_id": session_id},
        ).mappings().first()
    if not row:
        raise FileNotFoundError(f"Clarification session not found: {session_id}")
    return _row_to_session(dict(row))


def list_clarification_sessions(limit: int = 50, schema_name: str = "automap") -> list[dict[str, Any]]:
    """List recent clarification sessions."""
    ensure_clarification_sessions_table(schema_name)
    table = _qualified_table(schema_name, "clarification_sessions")
    engine = get_engine()
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                f"""
                SELECT session_id, raw_prompt, questions, answers, status,
                       changes_summary, created_at, updated_at
                FROM {table}
                ORDER BY updated_at DESC
                LIMIT :limit;
                """
            ),
            {"limit": limit},
        ).mappings()
    return [
        {
            **dict(row),
            "questions": _load_jsonb(row.get("questions"), []),
            "answers": _load_jsonb(row.get("answers"), []),
            "changes_summary": _load_jsonb(row.get("changes_summary"), {}),
        }
        for row in rows
    ]


def _question_lookup(session: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {question["question_id"]: question for question in session.get("questions") or []}


def _normalize_answers(
    session: dict[str, Any],
    answers: list[dict[str, Any]] | dict[str, Any],
    answered_by: str = "local_reviewer",
) -> list[dict[str, Any]]:
    question_lookup = _question_lookup(session)
    raw_answers = answers if isinstance(answers, list) else [
        {"question_id": key, "answer_value": value}
        for key, value in answers.items()
    ]
    normalized: list[dict[str, Any]] = []
    for item in raw_answers:
        question_id = item.get("question_id")
        if question_id not in question_lookup:
            raise ValueError(f"Unknown clarification question_id: {question_id}")
        question = question_lookup[question_id]
        value = item.get("answer_value")
        if value is None:
            value = question.get("default_answer")
        normalized.append(
            ClarificationAnswer(
                question_id=question_id,
                answer_value=value,
                answer_label=item.get("answer_label") or _answer_value_text(value),
                answered_by=item.get("answered_by") or answered_by,
            ).to_dict()
        )
    return normalized


def answer_clarification_session(
    session_id: str,
    answers: list[dict[str, Any]] | dict[str, Any],
    answered_by: str = "local_reviewer",
) -> dict[str, Any]:
    """Validate and save answers for an existing clarification session."""
    session = get_clarification_session(session_id)
    new_answers = _normalize_answers(session, answers, answered_by=answered_by)
    answer_by_id = {answer["question_id"]: answer for answer in session.get("answers") or []}
    for answer in new_answers:
        answer_by_id[answer["question_id"]] = answer
    session["answers"] = list(answer_by_id.values())
    session["status"] = "answered"
    session["updated_at"] = datetime.now(UTC).isoformat()
    _update_session(session)
    return session


def _answers_by_id(session: dict[str, Any], answers: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    source = answers if answers is not None else session.get("answers") or []
    return {answer["question_id"]: answer for answer in source}


def _option_label(question: dict[str, Any], value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(_option_label(question, item) for item in value)
    for option in question.get("options") or []:
        if option.get("value") == value:
            return str(option.get("label") or value)
    return _answer_value_text(value)


def _distance_from_answer(question: dict[str, Any], answer_value: Any) -> dict[str, Any]:
    if isinstance(answer_value, dict):
        return {
            "value": answer_value.get("value"),
            "unit": answer_value.get("unit") or answer_value.get("units"),
            "label": answer_value.get("label") or _answer_value_text(answer_value),
        }
    for option in question.get("options") or []:
        if option.get("value") == answer_value:
            distance = option.get("distance") or {}
            return {
                "value": distance.get("value"),
                "unit": distance.get("unit"),
                "label": option.get("label") or _answer_value_text(answer_value),
            }
    return {"value": answer_value, "unit": None, "label": _answer_value_text(answer_value)}


def build_refined_request_context(
    session: dict[str, Any],
    answers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Convert human answers into deterministic recipe refinement context."""
    question_lookup = _question_lookup(session)
    answers_by_id = _answers_by_id(session, answers)
    context: dict[str, Any] = {
        "proximity": {},
        "flood_scope": {},
        "time_range": None,
        "commercial_zoning": {},
        "missing_data_decisions": {},
        "suitability_priorities": [],
        "assumptions_from_user_answers": [],
        "resolved_ambiguity_flags": [],
    }

    for question_id, answer in answers_by_id.items():
        question = question_lookup.get(question_id, {})
        value = answer.get("answer_value")
        label = answer.get("answer_label") or _option_label(question, value)

        if question_id == "near_distance":
            distance = _distance_from_answer(question, value)
            context["proximity"]["distance"] = distance
            context["proximity"]["school_distance"] = distance
            context["assumptions_from_user_answers"].append(f"Near means {distance.get('label') or label}.")
            context["resolved_ambiguity_flags"].append("near_distance_threshold_missing")
        elif question_id == "recent_time_range":
            context["time_range"] = {"value": value, "label": label}
            context["assumptions_from_user_answers"].append(f"Recent means {label}.")
            context["resolved_ambiguity_flags"].append("recent_time_range_needed")
        elif question_id == "flood_layer_scope":
            values = value if isinstance(value, list) else [value]
            if "all_flood_hazard" in values:
                values = ["floodway", "100_year", "500_year"]
            context["flood_scope"] = {"values": values, "label": label}
            context["assumptions_from_user_answers"].append(f"Flood scope: {label}.")
        elif question_id == "commercial_zoning_codes":
            values = value if isinstance(value, list) else [value]
            context["commercial_zoning"] = {"values": values, "label": label}
            context["assumptions_from_user_answers"].append(f"Commercial zoning scope: {label}.")
            context["resolved_ambiguity_flags"].append("zoning_code_definition_needed")
        elif question_id == "missing_development_data_decision":
            context["missing_data_decisions"]["development"] = value
            context["missing_data_decisions"]["permits"] = value
            context["missing_data_decisions"]["planning cases"] = value
            context["assumptions_from_user_answers"].append(f"Missing development data decision: {label}.")
        elif question_id == "suitability_priorities":
            values = value if isinstance(value, list) else [value]
            context["suitability_priorities"] = values
            context["assumptions_from_user_answers"].append(f"Suitability priorities: {label}.")
            context["resolved_ambiguity_flags"].append("suitability_scoring_assumptions_needed")
        elif question_id == "historical_year":
            context["historical_year"] = value
            context["assumptions_from_user_answers"].append(f"Historical year: {label}.")

    return context


def _layer_matches_flood_scope(layer: dict[str, Any], values: list[str]) -> bool:
    name = str(layer.get("layer_name") or layer.get("layer_key") or "").lower()
    if layer.get("category") != "flood":
        return True
    if "floodway" in values and ("floodway" in name or "flood way" in name):
        return True
    if "100_year" in values and ("100" in name or "100year" in name):
        return True
    if "500_year" in values and ("500" in name or "500year" in name):
        return True
    return False


def _remove_review_reason(review_reasons: list[str], fragments: list[str]) -> list[str]:
    return [
        reason for reason in review_reasons
        if not any(fragment.lower() in reason.lower() for fragment in fragments)
    ]


def _sync_recipe_to_selected_layers(recipe: dict[str, Any]) -> None:
    selected_keys = {layer.get("layer_key") for layer in recipe.get("selected_layers") or [] if layer.get("layer_key")}
    for operation in recipe.get("spatial_operations") or []:
        if isinstance(operation.get("input_layers"), list):
            operation["input_layers"] = [
                layer_key for layer_key in operation["input_layers"]
                if layer_key in selected_keys
            ]
        if isinstance(operation.get("boundary_layers"), list):
            operation["boundary_layers"] = [
                layer_key for layer_key in operation["boundary_layers"]
                if layer_key in selected_keys
            ]
    recipe["symbology_recommendations"] = [
        item for item in recipe.get("symbology_recommendations") or []
        if item.get("layer_key") in selected_keys
    ]


def _apply_refinement_context(recipe: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    refined = deepcopy(recipe)
    applied: list[str] = []

    distance = (context.get("proximity") or {}).get("distance")
    if distance:
        label = distance.get("label") or _answer_value_text(distance)
        for operation in refined.get("spatial_operations") or []:
            if operation.get("operation") in {"proximity_search", "buffer_or_proximity"}:
                operation["distance"] = label
                operation["needs_review"] = False
                operation["notes"] = f"Use a reviewer-confirmed near distance of {label}."
                operation["description"] = f"Buffer or select nearby features using {label}."
        analysis_plan = refined.get("analysis_plan") or {}
        analysis_plan.setdefault("assumptions", []).append(f"Near means {label}.")
        refined["analysis_plan"] = analysis_plan
        intelligence = refined.get("request_intelligence") or {}
        intelligence["ambiguity_flags_resolved_by_clarification"] = sorted(
            set([*(intelligence.get("ambiguity_flags_resolved_by_clarification") or []), "near_distance_threshold_missing"])
        )
        intelligence["ambiguity_flags"] = [
            flag for flag in intelligence.get("ambiguity_flags") or []
            if flag != "near_distance_threshold_missing"
        ]
        refined["request_intelligence"] = intelligence
        refined["review_reasons"] = _remove_review_reason(
            refined.get("review_reasons") or [],
            ["Proximity distance", "near_distance_threshold_missing", "What distance should count as near"],
        )
        applied.append(f"Applied near distance: {label}")

    flood_values = (context.get("flood_scope") or {}).get("values") or []
    if flood_values:
        before_layers = refined.get("selected_layers") or []
        refined["selected_layers"] = [
            layer for layer in before_layers if _layer_matches_flood_scope(layer, flood_values)
        ]
        selected_flood_labels = (context.get("flood_scope") or {}).get("label") or ", ".join(flood_values)
        refined.setdefault("analysis_plan", {}).setdefault("assumptions", []).append(
            f"Flood scope limited to {selected_flood_labels}."
        )
        applied.append(f"Applied flood scope: {selected_flood_labels}")

    commercial = context.get("commercial_zoning") or {}
    if commercial.get("values"):
        values = commercial["values"]
        for layer_key, entry in (refined.get("filter_plan") or {}).items():
            if entry.get("category") == "zoning":
                field = entry.get("selected_field") or "ZONING_GEN"
                if "general_commercial" in values:
                    entry["selected_field"] = field
                    entry["draft_where_clause"] = f"{field} IN ('COMMERCIAL', 'OFFICE')"
                    entry["needs_review"] = False
                    entry["review_reason"] = "Commercial zoning scope was clarified by reviewer."
        refined["review_reasons"] = _remove_review_reason(
            refined.get("review_reasons") or [],
            ["Commercial zoning field/code", "Which zoning codes should count as commercial", "zoning_code_definition_needed"],
        )
        refined.setdefault("analysis_plan", {}).setdefault("assumptions", []).append(
            f"Commercial zoning scope: {commercial.get('label') or ', '.join(values)}."
        )
        applied.append("Applied commercial zoning answer.")

    time_range = context.get("time_range")
    if time_range:
        refined.setdefault("filters", []).append(
            {
                "type": "time",
                "field": None,
                "value": time_range.get("value"),
                "notes": f"Reviewer clarified recent as {time_range.get('label')}; date field still requires field review.",
            }
        )
        refined.setdefault("analysis_plan", {}).setdefault("assumptions", []).append(
            f"Recent means {time_range.get('label')}."
        )
        applied.append(f"Applied recent time range: {time_range.get('label')}.")

    missing_decisions = context.get("missing_data_decisions") or {}
    if missing_decisions:
        refined.setdefault("analysis_plan", {}).setdefault("assumptions", []).append(
            f"Missing data decisions recorded: {missing_decisions}."
        )
        if any(value == "continue_without_topic" for value in missing_decisions.values()):
            topics_to_remove = {topic for topic, value in missing_decisions.items() if value == "continue_without_topic"}
            refined["missing_data_needed"] = [
                topic for topic in refined.get("missing_data_needed") or []
                if topic not in topics_to_remove
            ]
            refined["review_reasons"] = [
                reason for reason in refined.get("review_reasons") or []
                if not any(topic in reason for topic in topics_to_remove)
            ]
        if any(value == "stop_unsupported" for value in missing_decisions.values()):
            refined.setdefault("analysis_plan", {}).setdefault("blockers", []).append(
                "Reviewer stopped recipe because requested missing data is unsupported."
            )
        applied.append("Recorded missing-data decision.")

    if context.get("suitability_priorities"):
        refined.setdefault("analysis_plan", {}).setdefault("assumptions", []).append(
            f"Suitability priorities: {', '.join(context['suitability_priorities'])}."
        )
        applied.append("Recorded suitability priorities.")

    if context.get("assumptions_from_user_answers"):
        intelligence = refined.get("request_intelligence") or {}
        intelligence["assumptions_from_user_answers"] = context["assumptions_from_user_answers"]
        intelligence["remaining_ambiguity_flags"] = intelligence.get("ambiguity_flags") or []
        refined["request_intelligence"] = intelligence

    _sync_recipe_to_selected_layers(refined)
    refined["filter_plan"] = build_filter_plan(refined)
    if commercial.get("values"):
        values = commercial["values"]
        for entry in (refined.get("filter_plan") or {}).values():
            if entry.get("category") == "zoning" and "general_commercial" in values:
                field = entry.get("selected_field") or "ZONING_GEN"
                entry["selected_field"] = field
                entry["draft_where_clause"] = f"{field} IN ('COMMERCIAL', 'OFFICE')"
                entry["needs_review"] = False
                entry["review_reason"] = "Commercial zoning scope was clarified by reviewer."
    validation = validate_filter_plan(refined)
    refined["validation"] = validation
    if validation.get("warnings"):
        refined["review_reasons"] = sorted(set([*(refined.get("review_reasons") or []), *validation["warnings"]]))

    refined["needs_review"] = bool(refined.get("review_reasons") or refined.get("missing_data_needed"))
    refined["_applied_refinements"] = applied
    return refined


def summarize_recipe_changes(initial_recipe: dict[str, Any], refined_recipe: dict[str, Any]) -> dict[str, Any]:
    """Summarize layer/filter/warning/spatial-operation changes."""
    initial_layers = {layer.get("layer_key"): layer for layer in initial_recipe.get("selected_layers") or []}
    refined_layers = {layer.get("layer_key"): layer for layer in refined_recipe.get("selected_layers") or []}
    initial_warning_set = set(initial_recipe.get("review_reasons") or [])
    refined_warning_set = set(refined_recipe.get("review_reasons") or [])
    initial_ops = {operation.get("operation") for operation in initial_recipe.get("spatial_operations") or []}
    refined_ops = {operation.get("operation") for operation in refined_recipe.get("spatial_operations") or []}

    changed_filters = []
    initial_filter_plan = initial_recipe.get("filter_plan") or {}
    refined_filter_plan = refined_recipe.get("filter_plan") or {}
    for layer_key, entry in refined_filter_plan.items():
        if entry != initial_filter_plan.get(layer_key):
            changed_filters.append(layer_key)

    return {
        "layers_added": sorted(key for key in refined_layers if key and key not in initial_layers),
        "layers_removed": sorted(key for key in initial_layers if key and key not in refined_layers),
        "filters_improved": sorted(changed_filters),
        "warnings_resolved": sorted(initial_warning_set - refined_warning_set),
        "warnings_remaining": sorted(refined_warning_set),
        "spatial_operations_added": sorted(operation for operation in refined_ops - initial_ops if operation),
        "spatial_operations_removed": sorted(operation for operation in initial_ops - refined_ops if operation),
        "applied_refinements": refined_recipe.get("_applied_refinements") or [],
    }


def _remaining_questions(session: dict[str, Any]) -> list[dict[str, Any]]:
    answered_ids = {answer["question_id"] for answer in session.get("answers") or []}
    return [
        question for question in session.get("questions") or []
        if question.get("question_id") not in answered_ids and question.get("required")
    ]


def refine_recipe_from_answers(
    session_id: str,
    layer_catalog: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Regenerate and refine a recipe using saved clarification answers."""
    session = get_clarification_session(session_id)
    context = build_refined_request_context(session)
    refined_recipe = build_recipe(session["raw_prompt"], layer_catalog=layer_catalog)
    refined_recipe = _apply_refinement_context(refined_recipe, context)
    changes_summary = summarize_recipe_changes(session["initial_recipe"], refined_recipe)
    remaining_questions = _remaining_questions(session)
    blockers = list((refined_recipe.get("analysis_plan") or {}).get("blockers") or [])
    if remaining_questions:
        blockers.append("Required clarification questions remain unanswered.")

    clarification = {
        "session_id": session_id,
        "questions": session.get("questions") or [],
        "answers": session.get("answers") or [],
        "applied_refinements": context,
        "changes_from_initial_recipe": changes_summary,
        "remaining_questions": remaining_questions,
        "unresolved_blockers": sorted(set(blockers)),
    }
    refined_recipe["clarification"] = clarification
    refined_recipe.get("request_intelligence", {})["remaining_ambiguity_flags"] = (
        refined_recipe.get("request_intelligence", {}).get("ambiguity_flags") or []
    )
    refined_recipe.pop("_applied_refinements", None)

    session["refined_prompt"] = session["raw_prompt"]
    session["refined_request_context"] = context
    session["refined_recipe"] = refined_recipe
    session["changes_summary"] = changes_summary
    session["status"] = "refined" if not remaining_questions else "answered"
    session["updated_at"] = datetime.now(UTC).isoformat()
    _update_session(session)
    return session
