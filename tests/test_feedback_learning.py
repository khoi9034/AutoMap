import json

from app.default_suggester import suggest_clarification_defaults, suggest_layer_preferences
from app.feedback_learning import learn_from_approved_packet, record_recipe_feedback
from app.pattern_library import (
    extract_pattern_from_approved_packet,
    get_pattern,
    list_clarification_defaults,
    upsert_approved_pattern,
)
from app.pattern_matcher import find_similar_patterns, score_pattern_similarity
from app.recipe_engine import build_recipe


def record(layer_key, layer_name, category, *, aliases=None, service_name=None, layer_id=0):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "aliases": aliases or [category],
        "description": "",
        "planning_use_cases": [category],
        "canonical_topic": category,
        "source_priority": 1,
        "source_status": "active",
        "source_key": "cabarrus_new_opendata",
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
        record("parcels", "Tax Parcels", "parcel", aliases=["parcel", "parcels"], service_name="Tax_Parcels"),
        record("municipal", "MunicipalDistrict", "jurisdiction", aliases=["municipal", "jurisdiction"], service_name="MunicipalDistrict"),
        record("floodway", "FloodWay", "flood", aliases=["flood", "floodway"], service_name="Flood_Hazard_Areas", layer_id=0),
        record("flood500", "FloodPlain500year", "flood", aliases=["flood", "500 year flood"], service_name="Flood_Hazard_Areas", layer_id=1),
        record("flood100", "FloodPlain100year", "flood", aliases=["flood", "100 year flood"], service_name="Flood_Hazard_Areas", layer_id=2),
        record("elem", "Elementary School District", "schools", service_name="School_Districts", layer_id=0),
        record("middle", "Middle School District", "schools", service_name="School_Districts", layer_id=1),
        record("high", "High School District", "schools", service_name="School_Districts", layer_id=2),
    ]


def write_approved_packet(tmp_path):
    prompt = "Show development pressure near schools and flood zones in Concord."
    recipe = build_recipe(prompt, sample_catalog(), persist_data_gaps=False)
    recipe["clarification"] = {
        "answers": [
            {"question_id": "near_distance", "answer_value": "0.5_miles", "answer_label": "0.5 miles"},
            {
                "question_id": "flood_layer_scope",
                "answer_value": ["floodway", "100_year"],
                "answer_label": "Floodway + 100-year floodplain",
            },
            {
                "question_id": "missing_development_data_decision",
                "answer_value": "mark_missing",
                "answer_label": "Mark current development activity as missing",
            },
        ]
    }
    packet = tmp_path / "approved_packet"
    packet.mkdir()
    receipt = {
        "decision": "approved",
        "final_publish_ready": True,
        "approved_at": "2026-06-15T12:00:00+00:00",
        "resolved_warnings": [{"warning_id": "near_distance", "action": "resolved"}],
        "accepted_warnings": [],
        "kept_non_blocking_warnings": [],
        "accepted_risks": ["Use 0.5 miles for near schools in this draft."],
        "missing_data_decisions": [{"item": "development", "decision": "mark_missing"}],
        "reviewer_notes": ["Approved as local draft pattern."],
    }
    (packet / "approved_recipe.json").write_text(json.dumps(recipe), encoding="utf-8")
    (packet / "approval_receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    (packet / "approval_file.json").write_text(json.dumps({"decision": "approved"}), encoding="utf-8")
    (packet / "approved_warnings.json").write_text(json.dumps({"final_publish_ready": True}), encoding="utf-8")
    return packet


def test_approved_packet_extracts_pattern_and_preserves_decisions(tmp_path):
    packet = write_approved_packet(tmp_path)
    pattern = extract_pattern_from_approved_packet(packet)

    assert pattern["final_publish_ready"] is True
    assert pattern["primary_intent"] == "development_pressure"
    assert "flood100" in pattern["selected_layer_keys"]
    assert pattern["missing_data_decisions"][0]["decision"] == "mark_missing"
    assert "0.5 miles" in json.dumps(pattern["clarification_answers"])


def test_pattern_stored_in_database_and_default_suggested(tmp_path):
    packet = write_approved_packet(tmp_path)
    pattern = upsert_approved_pattern(extract_pattern_from_approved_packet(packet))
    reloaded = get_pattern(pattern["pattern_key"])
    defaults = list_clarification_defaults(limit=100)

    assert reloaded["pattern_key"] == pattern["pattern_key"]
    assert any(default.get("answer_label") == "0.5 miles" for default in defaults)
    assert pattern["clarification_defaults_upserted"] >= 1


def test_similar_prompt_finds_pattern_and_layer_preferences(tmp_path):
    packet = write_approved_packet(tmp_path)
    pattern = upsert_approved_pattern(extract_pattern_from_approved_packet(packet))
    recipe = build_recipe("Show development pressure near schools and flood zones in Concord.", sample_catalog(), persist_data_gaps=False)
    similar = find_similar_patterns(recipe["user_intent"], recipe["request_intelligence"])
    preferences = suggest_layer_preferences(recipe["user_intent"], recipe["request_intelligence"])

    assert any(item["pattern_key"] == pattern["pattern_key"] for item in similar)
    assert any(item["layer_key"] in {"flood100", "floodway"} for item in preferences["preferred_layers"])
    assert recipe["learned_context"]["similar_patterns"]


def test_clarification_default_suggested_from_pattern(tmp_path):
    packet = write_approved_packet(tmp_path)
    upsert_approved_pattern(extract_pattern_from_approved_packet(packet))
    recipe = build_recipe("Show development pressure near schools and flood zones in Concord.", sample_catalog(), persist_data_gaps=False)
    questions = [
        {"question_id": "near_distance", "question_text": "What distance should count as near?"},
        {"question_id": "flood_layer_scope", "question_text": "Which flood hazard layers should be included?"},
    ]

    suggestions = suggest_clarification_defaults(recipe["user_intent"], questions, recipe["request_intelligence"])

    assert suggestions["near_distance"]["answer_label"] == "0.5 miles"
    assert suggestions["near_distance"]["default_source"]


def test_learning_flow_records_feedback_and_does_not_invent_layers(tmp_path):
    packet = write_approved_packet(tmp_path)
    pattern = learn_from_approved_packet(packet)
    feedback = record_recipe_feedback(
        pattern["raw_prompt"],
        {"selected_layers": [{"layer_key": "flood100"}]},
        "needs_changes",
        {"note": "test feedback"},
        source_packet_path=packet,
    )
    serialized = json.dumps({"pattern": pattern, "feedback": feedback}).lower()

    assert set(pattern["preferred_layer_keys"]).issubset({item["layer_key"] for item in sample_catalog()})
    assert feedback["feedback_type"] == "needs_changes"
    assert "cfs_dev" not in serialized
    assert "arcgis_password" not in serialized


def test_historical_pattern_does_not_override_current_request():
    historical_pattern = {
        "pattern_key": "historical_2014",
        "raw_prompt": "Show 2014 parcels and zoning.",
        "normalized_prompt": "show 2014 parcels and zoning",
        "primary_intent": "historical_comparison",
        "secondary_intents": [],
        "topics": ["parcel", "zoning"],
        "geographies": [],
        "final_publish_ready": True,
        "is_active": True,
    }
    current_intelligence = {
        "primary_intent": "zoning_review",
        "detected_intents": ["zoning_review"],
        "secondary_intents": [],
    }

    assert score_pattern_similarity(historical_pattern, current_intelligence, raw_prompt="Show current parcels and zoning.") < 0.28
