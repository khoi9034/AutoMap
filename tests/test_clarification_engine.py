import json

from app.clarification_engine import (
    answer_clarification_session,
    build_refined_request_context,
    create_clarification_session,
    get_clarification_session,
    refine_recipe_from_answers,
)


def record(layer_key, layer_name, category, *, aliases=None, priority=1, status="active", service_name=None, layer_id=0):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "aliases": aliases or [category],
        "description": "",
        "planning_use_cases": [category],
        "canonical_topic": category,
        "source_priority": priority,
        "source_status": status,
        "source_key": "cabarrus_new_opendata" if priority == 1 else "cabarrus_legacy_opendata",
        "service_name": service_name or layer_name,
        "service_url": f"https://example.com/{service_name or layer_name}/MapServer",
        "layer_url": f"https://example.com/{service_name or layer_name}/MapServer/{layer_id}",
        "geometry_type": "esriGeometryPolygon",
        "layer_id": layer_id,
        "is_verified": True,
        "is_group_layer": False,
        "is_feature_layer": True,
        "is_historical": False,
        "historical_year": None,
        "record_count": 1,
        "fields": [],
    }


def sample_catalog():
    return [
        record("parcels", "Tax Parcels", "parcel", aliases=["parcel", "parcels", "property"], service_name="Tax_Parcels"),
        record("municipal", "MunicipalDistrict", "jurisdiction", aliases=["municipal", "municipality", "jurisdiction"], service_name="MunicipalDistrict"),
        record("floodway", "FloodWay", "flood", aliases=["flood", "floodway"], service_name="Flood_Hazard_Areas", layer_id=0),
        record("flood500", "FloodPlain500year", "flood", aliases=["flood", "500 year flood"], service_name="Flood_Hazard_Areas", layer_id=1),
        record("flood100", "FloodPlain100year", "flood", aliases=["flood", "floodplain", "100 year flood"], service_name="Flood_Hazard_Areas", layer_id=2),
        record("elem", "Elementary School District", "schools", service_name="School_Districts", layer_id=0),
        record("middle", "Middle School District", "schools", service_name="School_Districts", layer_id=1),
        record("high", "High School District", "schools", service_name="School_Districts", layer_id=2),
    ]


def test_create_clarification_session_from_ambiguous_prompt_generates_questions():
    session = create_clarification_session(
        "Show development pressure near schools and flood zones in Concord.",
        layer_catalog=sample_catalog(),
        persist=False,
    )
    question_ids = {question["question_id"] for question in session["questions"]}

    assert session["status"] == "open"
    assert {"near_distance", "flood_layer_scope", "missing_development_data_decision"}.issubset(question_ids)


def test_recent_prompt_generates_recent_question():
    session = create_clarification_session(
        "Map recent permits near Kannapolis.",
        layer_catalog=sample_catalog(),
        persist=False,
    )
    question_ids = {question["question_id"] for question in session["questions"]}

    assert "recent_time_range" in question_ids
    assert "missing_development_data_decision" in question_ids


def test_build_refined_context_records_distance_and_missing_data_decision():
    session = create_clarification_session(
        "Show current permits near Kannapolis.",
        layer_catalog=sample_catalog(),
        persist=False,
    )
    answers = [
        {"question_id": "near_distance", "answer_value": "0.5_miles", "answer_label": "0.5 miles"},
        {"question_id": "missing_development_data_decision", "answer_value": "mark_missing", "answer_label": "Mark missing"},
    ]
    session["answers"] = answers

    context = build_refined_request_context(session)

    assert context["proximity"]["school_distance"]["label"] == "0.5 miles"
    assert context["missing_data_decisions"]["development"] == "mark_missing"
    assert "near_distance_threshold_missing" in context["resolved_ambiguity_flags"]


def test_database_session_insert_and_refine_updates_recipe():
    session = create_clarification_session(
        "Show development pressure near schools and flood zones in Concord.",
        layer_catalog=sample_catalog(),
    )
    answer_clarification_session(
        session["session_id"],
        [
            {"question_id": "near_distance", "answer_value": "0.5_miles"},
            {"question_id": "flood_layer_scope", "answer_value": ["floodway", "100_year"]},
            {"question_id": "missing_development_data_decision", "answer_value": "mark_missing"},
        ],
    )

    refined_session = refine_recipe_from_answers(session["session_id"], layer_catalog=sample_catalog())
    reloaded = get_clarification_session(session["session_id"])
    refined_recipe = refined_session["refined_recipe"]
    flood_layer_names = {
        layer["layer_name"] for layer in refined_recipe["selected_layers"]
        if layer["category"] == "flood"
    }

    assert reloaded["status"] == "refined"
    assert flood_layer_names == {"FloodWay", "FloodPlain100year"}
    assert "flood500" in refined_session["changes_summary"]["layers_removed"]
    assert refined_recipe["clarification"]["applied_refinements"]["proximity"]["distance"]["label"] == "0.5 miles"
    assert "development" in refined_recipe["missing_data_needed"]


def test_refined_recipe_preserves_trusted_catalog_only_and_no_forbidden_references():
    catalog = sample_catalog()
    session = create_clarification_session(
        "Show development pressure near schools and flood zones in Concord.",
        layer_catalog=catalog,
    )
    answer_clarification_session(
        session["session_id"],
        {
            "near_distance": "0.5_miles",
            "flood_layer_scope": ["floodway", "100_year"],
            "missing_development_data_decision": "mark_missing",
        },
    )
    refined = refine_recipe_from_answers(session["session_id"], layer_catalog=catalog)
    refined_recipe = refined["refined_recipe"]
    catalog_keys = {item["layer_key"] for item in catalog}
    serialized = json.dumps(refined_recipe).lower()

    assert {layer["layer_key"] for layer in refined_recipe["selected_layers"]}.issubset(catalog_keys)
    assert "cfs_dev" not in serialized
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "arcgis_password" not in serialized
