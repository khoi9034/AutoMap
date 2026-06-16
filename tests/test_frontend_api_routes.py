import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.web_ui import create_app


def test_api_status_is_json_and_sanitized(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.get_system_status",
        lambda: {
            "version": "1.5.0",
            "database_connected": True,
            "DATABASE_URL": "postgresql://secret-password",
            "protected_note": "cfs_dev should never leave the API",
            "real_publish_enabled": False,
        },
    )
    client = TestClient(create_app())

    response = client.get("/api/status")
    serialized = json.dumps(response.json()).lower()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["version"] == "1.5.0"
    assert "database_url" not in serialized
    assert "secret" not in serialized
    assert "password" not in serialized
    assert "cfs" not in serialized
    assert "cfs_dev" not in serialized


def test_cors_allows_local_next_frontend():
    client = TestClient(create_app())

    response = client.options(
        "/api/status",
        headers={
            "Origin": "http://localhost:3010",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3010"


def test_no_real_publish_endpoint_exposed():
    client = TestClient(create_app())
    paths = client.get("/openapi.json").json()["paths"]
    serialized_paths = json.dumps(paths).lower()

    assert "/api/publish-dry-run" in paths
    assert "/api/portal-smoke-test-dry-run" in paths
    assert "confirm-publish" not in serialized_paths
    assert "publish-draft-webmap" not in serialized_paths


def test_frontend_workflow_api_routes_exist():
    client = TestClient(create_app())
    paths = client.get("/openapi.json").json()["paths"]

    expected_paths = {
        "/api/status",
        "/api/catalog/search",
        "/api/data-gaps",
        "/api/data-gaps/{gap_key}/candidates",
        "/api/data-gaps/resolve",
        "/api/external-sources",
        "/api/external-sources/load",
        "/api/external-sources/inspect",
        "/api/history",
        "/api/packets",
        "/api/reports",
        "/api/reports/{report_id}",
        "/api/analysis/plan",
        "/api/analysis/execute",
        "/api/analysis/runs",
        "/api/analysis/runs/{analysis_run_id}",
        "/api/analysis/refinements",
        "/api/analysis/refinements/{session_id}",
        "/api/analysis/refinements/{session_id}/select",
        "/api/analysis/refinements/{session_id}/execute",
        "/api/analysis/reports",
        "/api/analysis/reports/from-refinement",
        "/api/analysis/reports/{report_id}",
        "/api/patterns",
        "/api/patterns/{pattern_key}",
        "/api/patterns/learn-from-approved",
        "/api/feedback/recipe",
        "/api/clarification-defaults",
        "/api/clarification",
        "/api/clarification/start",
        "/api/clarification/{session_id}",
        "/api/clarification/{session_id}/answer",
        "/api/clarification/{session_id}/refine",
        "/api/clarification/{session_id}/learn",
        "/api/preview-config/{packet_id}",
        "/api/recipe",
        "/api/review-packet",
        "/api/webmap-draft",
        "/api/adjustment-template",
        "/api/apply-adjustments",
        "/api/approval-template",
        "/api/apply-approval",
        "/api/generate-report",
        "/api/publish-dry-run",
        "/api/portal-smoke-test-dry-run",
    }

    assert expected_paths.issubset(set(paths))


def test_api_analysis_routes_are_json_and_sanitized(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.build_analysis_plan",
        lambda prompt, max_features=2000: {
            "raw_prompt": prompt,
            "executable": True,
            "operation_type": "select_by_intersection",
            "recommended_execution_plan": ["Count first", "Write local GeoJSON"],
        },
    )
    monkeypatch.setattr(
        "app.api_routes.execute_analysis",
        lambda prompt, max_features=2000: {
            "analysis_run_id": "analysis_1",
            "status": "completed",
            "operation_type": "select_by_intersection",
            "output_count": 3,
            "output_geojson_path": "outputs/analysis/sample/analysis_result.geojson",
            "analysis_receipt": {"published": False, "protected_external_database_touched": False},
        },
    )
    monkeypatch.setattr(
        "app.api_routes.list_analysis_runs",
        lambda limit=50: [{"analysis_run_id": "analysis_1", "status": "completed"}],
    )
    monkeypatch.setattr(
        "app.api_routes.get_analysis_run",
        lambda analysis_run_id: {"analysis_run_id": analysis_run_id, "status": "completed"},
    )
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    planned = client.post("/api/analysis/plan", json={"prompt": "Show parcels in Concord floodplain"})
    executed = client.post("/api/analysis/execute", json={"prompt": "Show parcels in Concord floodplain"})
    listed = client.get("/api/analysis/runs")
    detail = client.get("/api/analysis/runs/analysis_1")
    serialized = json.dumps(
        {"planned": planned.json(), "executed": executed.json(), "listed": listed.json(), "detail": detail.json()}
    ).lower()

    assert planned.status_code == 200
    assert executed.status_code == 200
    assert listed.status_code == 200
    assert detail.status_code == 200
    assert executed.json()["analysis_result"]["status"] == "completed"
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "database_url" not in serialized
    assert "cfs_dev" not in serialized


def test_api_external_source_routes_are_json_and_sanitized(monkeypatch):
    source = {
        "source_key": "cabarrus_accela_plan_review_proxy",
        "source_name": "Plan Review Proxy",
        "approval_status": "candidate",
        "source_status": "proxy",
        "intended_gaps": ["current_development_pipeline"],
        "inspected_metadata": {"inspection_status": "reference_only", "downloaded_geometry": False},
    }
    monkeypatch.setattr("app.api_routes.list_external_sources", lambda: [source])
    monkeypatch.setattr("app.api_routes.load_seed_external_sources", lambda: {"loaded": 1, "sources": [source]})
    monkeypatch.setattr(
        "app.api_routes.inspect_registered_external_sources",
        lambda: {"inspected": 1, "catalog_upserts": 0, "sources": [source]},
    )
    monkeypatch.setattr(
        "app.api_routes.map_gap_to_candidate_sources",
        lambda gap_key: [{**source, "gap_key": gap_key, "source_score": 80, "classified_limitations": ["Proxy/context only."]}],
    )
    monkeypatch.setattr(
        "app.api_routes.resolve_gap_with_source",
        lambda gap_key, source_key, resolution_status=None, notes=None: {
            "resolution": {
                "gap_key": gap_key,
                "source_key": source_key,
                "resolution_status": resolution_status or "needs_review",
            }
        },
    )
    client = TestClient(create_app())

    listed = client.get("/api/external-sources")
    loaded = client.post("/api/external-sources/load")
    inspected = client.post("/api/external-sources/inspect")
    candidates = client.get("/api/data-gaps/current_development_pipeline/candidates")
    resolved = client.post(
        "/api/data-gaps/resolve",
        json={
            "gap_key": "current_development_pipeline",
            "source_key": "cabarrus_accela_plan_review_proxy",
            "resolution_status": "needs_review",
        },
    )
    serialized = json.dumps(
        {
            "listed": listed.json(),
            "loaded": loaded.json(),
            "inspected": inspected.json(),
            "candidates": candidates.json(),
            "resolved": resolved.json(),
        }
    ).lower()

    assert listed.status_code == 200
    assert loaded.status_code == 200
    assert inspected.status_code == 200
    assert candidates.status_code == 200
    assert resolved.status_code == 200
    assert inspected.json()["catalog_upserts"] == 0
    assert candidates.json()["candidates"][0]["source_status"] == "proxy"
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "database_url" not in serialized
    assert "cfs_dev" not in serialized


def test_api_analysis_refinement_routes_are_json_and_sanitized(monkeypatch):
    session = {
        "session_id": "refine_1",
        "source_analysis_run_id": "analysis_1",
        "status": "open",
        "options": [{"option_id": "summary_only", "safety_level": "safe"}],
        "refined_result": {},
    }
    monkeypatch.setattr("app.api_routes.create_refinement_session_from_blocked_run", lambda analysis_run_id: session)
    monkeypatch.setattr("app.api_routes.list_refinement_sessions", lambda limit=50: [session])
    monkeypatch.setattr("app.api_routes.get_refinement_session", lambda session_id: {**session, "session_id": session_id})
    monkeypatch.setattr(
        "app.api_routes.select_refinement_option",
        lambda session_id, option_id, parameters: {
            **session,
            "session_id": session_id,
            "status": "selected",
            "selected_option": {"option_id": option_id},
            "selected_parameters": parameters,
        },
    )
    monkeypatch.setattr(
        "app.api_routes.execute_refined_analysis",
        lambda session_id: {
            **session,
            "session_id": session_id,
            "status": "completed",
            "selected_option": {"option_id": "summary_only"},
            "refined_result": {"summary": {"geometry_downloaded": False}},
        },
    )
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    created = client.post("/api/analysis/refinements", json={"analysis_run_id": "analysis_1"})
    listed = client.get("/api/analysis/refinements")
    detail = client.get("/api/analysis/refinements/refine_1")
    selected = client.post(
        "/api/analysis/refinements/refine_1/select",
        json={"option_id": "summary_only", "parameters": {}},
    )
    executed = client.post("/api/analysis/refinements/refine_1/execute")
    serialized = json.dumps(
        {
            "created": created.json(),
            "listed": listed.json(),
            "detail": detail.json(),
            "selected": selected.json(),
            "executed": executed.json(),
        }
    ).lower()

    assert created.status_code == 200
    assert listed.status_code == 200
    assert detail.status_code == 200
    assert selected.status_code == 200
    assert executed.status_code == 200
    assert executed.json()["refinement_session"]["status"] == "completed"
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "database_url" not in serialized
    assert "cfs_dev" not in serialized


def test_api_analysis_report_routes_are_json_and_sanitized(monkeypatch):
    package = {
        "report_id": "analysis_report_1",
        "report_folder": "outputs/analysis_reports/sample",
        "report_title": "Analysis Report",
        "source_type": "analysis_refinement",
        "source_analysis_run_id": "analysis_1",
        "source_refinement_session_id": "refine_1",
        "files": [{"name": "analysis_report.html", "path": "outputs/analysis_reports/sample/analysis_report.html"}],
        "validation": {"is_valid": True},
    }

    class Package:
        report_id = "analysis_report_1"
        report_path = Path("outputs/analysis_reports/sample")
        report_title = "Analysis Report"
        source_type = "analysis_refinement"
        source_analysis_run_id = "analysis_1"
        source_refinement_session_id = "refine_1"
        files = {"analysis_report.html": "outputs/analysis_reports/sample/analysis_report.html"}
        validation = {"is_valid": True}

    monkeypatch.setattr("app.api_routes.generate_analysis_report", lambda analysis_run_id: Package())
    monkeypatch.setattr("app.api_routes.generate_analysis_report_from_refinement", lambda refinement_session_id: Package())
    monkeypatch.setattr("app.api_routes.list_analysis_reports", lambda limit=50: [package])
    monkeypatch.setattr("app.api_routes.get_analysis_report", lambda report_id: {**package, "report_id": report_id})
    client = TestClient(create_app())

    generated = client.post("/api/analysis/reports", json={"analysis_run_id": "analysis_1"})
    generated_refinement = client.post(
        "/api/analysis/reports/from-refinement",
        json={"refinement_session_id": "refine_1"},
    )
    listed = client.get("/api/analysis/reports")
    detail = client.get("/api/analysis/reports/analysis_report_1")
    serialized = json.dumps(
        {
            "generated": generated.json(),
            "generated_refinement": generated_refinement.json(),
            "listed": listed.json(),
            "detail": detail.json(),
        }
    ).lower()

    assert generated.status_code == 200
    assert generated_refinement.status_code == 200
    assert listed.status_code == 200
    assert detail.status_code == 200
    assert listed.json()["analysis_reports"][0]["report_id"] == "analysis_report_1"
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "database_url" not in serialized
    assert "cfs_dev" not in serialized


def test_api_learning_routes_are_json_and_sanitized(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.list_patterns",
        lambda limit=50: [{"pattern_key": "pattern_1", "raw_prompt": "Show flood near schools"}],
    )
    monkeypatch.setattr(
        "app.api_routes.list_clarification_defaults",
        lambda limit=50: [{"default_key": "near_distance", "answer_label": "0.5 miles"}],
    )
    monkeypatch.setattr(
        "app.api_routes.recent_feedback",
        lambda limit=50: [{"id": 1, "feedback_type": "approved"}],
    )
    monkeypatch.setattr(
        "app.api_routes.get_pattern",
        lambda pattern_key: {"pattern_key": pattern_key, "raw_prompt": "Show flood near schools"},
    )
    monkeypatch.setattr(
        "app.api_routes.learn_from_approved_packet",
        lambda path: {"pattern_key": "pattern_1", "source_approved_packet": path, "final_publish_ready": True},
    )
    monkeypatch.setattr(
        "app.api_routes.record_recipe_feedback",
        lambda raw_prompt, recipe, feedback_type, feedback_json, source_packet_path=None: {
            "id": 1,
            "raw_prompt": raw_prompt,
            "feedback_type": feedback_type,
        },
    )
    monkeypatch.setattr(
        "app.api_routes.learn_from_clarification_session",
        lambda session_id: {"id": 2, "feedback_type": "clarification_answered", "session_id": session_id},
    )
    client = TestClient(create_app())

    patterns = client.get("/api/patterns")
    detail = client.get("/api/patterns/pattern_1")
    learned = client.post("/api/patterns/learn-from-approved", json={"approved_packet_folder": "outputs/review_packets_approved/sample"})
    feedback = client.post(
        "/api/feedback/recipe",
        json={"raw_prompt": "Show flood", "recipe": {}, "feedback_type": "approved", "feedback_json": {}},
    )
    defaults = client.get("/api/clarification-defaults")
    clarification_learned = client.post("/api/clarification/clarify_1/learn")
    serialized = json.dumps(
        {
            "patterns": patterns.json(),
            "detail": detail.json(),
            "learned": learned.json(),
            "feedback": feedback.json(),
            "defaults": defaults.json(),
            "clarification_learned": clarification_learned.json(),
        }
    ).lower()

    assert patterns.status_code == 200
    assert detail.status_code == 200
    assert learned.status_code == 200
    assert feedback.status_code == 200
    assert defaults.status_code == 200
    assert clarification_learned.status_code == 200
    assert learned.json()["pattern"]["pattern_key"] == "pattern_1"
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "database_url" not in serialized
    assert "cfs" not in serialized


def test_api_clarification_routes_are_json_and_sanitized(monkeypatch):
    calls = []

    def fake_start(prompt):
        calls.append(("start", prompt))
        return {
            "session_id": "clarify-1",
            "raw_prompt": prompt,
            "status": "open",
            "initial_recipe": {
                "map_title": "Development pressure near schools",
                "request_intelligence": {"detected_intents": ["development_pressure", "school_district_lookup"]},
            },
            "questions": [
                {
                    "question_id": "near_distance",
                    "question_text": "What distance should count as near?",
                    "question_type": "distance",
                    "options": [{"value": "0.5_miles", "label": "0.5 miles"}],
                }
            ],
            "answers": [],
        }

    def fake_answer(session_id, answers, answered_by="local_reviewer"):
        calls.append(("answer", session_id, answers, answered_by))
        return {
            "session_id": session_id,
            "status": "answered",
            "answers": answers,
            "questions": [],
        }

    def fake_refine(session_id):
        calls.append(("refine", session_id))
        return {
            "session_id": session_id,
            "status": "refined",
            "refined_request_context": {"proximity": {"distance": {"label": "0.5 miles"}}},
            "refined_recipe": {
                "map_title": "Development pressure near schools",
                "clarification": {
                    "session_id": session_id,
                    "applied_refinements": {"proximity": {"distance": {"label": "0.5 miles"}}},
                },
            },
            "changes_summary": {"filters_improved": ["Near schools distance set to 0.5 miles."]},
        }

    monkeypatch.setattr("app.api_routes.create_clarification_session", fake_start)
    monkeypatch.setattr("app.api_routes.answer_clarification_session", fake_answer)
    monkeypatch.setattr("app.api_routes.refine_recipe_from_answers", fake_refine)
    monkeypatch.setattr("app.api_routes.get_clarification_session", lambda session_id: fake_refine(session_id))
    monkeypatch.setattr("app.api_routes.list_clarification_sessions", lambda limit=50: [fake_refine("clarify-1")])
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    started = client.post("/api/clarification/start", json={"prompt": "Show development pressure near schools"})
    answered = client.post(
        "/api/clarification/clarify-1/answer",
        json={
            "answers": [
                {
                    "question_id": "near_distance",
                    "answer_value": "0.5_miles",
                    "answer_label": "0.5 miles",
                }
            ]
        },
    )
    refined = client.post("/api/clarification/clarify-1/refine", json={})
    listed = client.get("/api/clarification")

    serialized = json.dumps(
        {
            "started": started.json(),
            "answered": answered.json(),
            "refined": refined.json(),
            "listed": listed.json(),
        }
    ).lower()

    assert started.status_code == 200
    assert answered.status_code == 200
    assert refined.status_code == 200
    assert listed.status_code == 200
    assert started.json()["session_id"] == "clarify-1"
    assert refined.json()["refined_recipe"]["clarification"]["session_id"] == "clarify-1"
    assert ("start", "Show development pressure near schools") in calls
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "database_url" not in serialized
    assert "cfs" not in serialized


def test_api_status_includes_sanitized_port_separation(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.get_system_status",
        lambda: {
            "version": "1.5.0",
            "database_connected": True,
            "ports": {"frontend": 3010, "backend_api": 8010, "reserved": [3000, 8000]},
            "real_publish_enabled": False,
        },
    )
    client = TestClient(create_app())

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["ports"] == {"frontend": 3010, "backend_api": 8010, "reserved": [3000, 8000]}


def test_api_publish_dry_run_cannot_real_publish(monkeypatch):
    calls = []

    def fake_publish(path, dry_run=True, confirm_publish=False):
        calls.append({"path": path, "dry_run": dry_run, "confirm_publish": confirm_publish})
        return {
            "status": "dry_run",
            "created_item": False,
            "real_publish_attempted": False,
            "shared_public": False,
            "shared_organization": False,
            "cfs_database_not_touched": True,
        }

    monkeypatch.setattr("app.api_routes.publish_webmap_draft", fake_publish)
    client = TestClient(create_app())

    response = client.post("/api/publish-dry-run", json={"approved_packet_folder": "outputs/review_packets_approved/sample"})
    serialized = json.dumps(response.json()).lower()

    assert response.status_code == 200
    assert calls == [
        {
            "path": "outputs/review_packets_approved/sample",
            "dry_run": True,
            "confirm_publish": False,
        }
    ]
    assert response.json()["result"]["status"] == "dry_run"
    assert "cfs" not in serialized


def test_api_portal_smoke_test_dry_run_cannot_real_publish(monkeypatch):
    calls = []

    def fake_smoke(path, confirm_publish=False):
        calls.append({"path": path, "confirm_publish": confirm_publish})
        return {
            "dry_run": True,
            "real_publish_attempted": False,
            "item_created": False,
            "blocked": False,
            "cfs_untouched_statement": "Protected external database was not touched.",
        }

    monkeypatch.setattr("app.api_routes.run_publish_smoke_test", fake_smoke)
    client = TestClient(create_app())

    response = client.post(
        "/api/portal-smoke-test-dry-run",
        json={"approved_packet_folder": "outputs/review_packets_approved/sample"},
    )
    serialized = json.dumps(response.json()).lower()

    assert response.status_code == 200
    assert calls == [{"path": "outputs/review_packets_approved/sample", "confirm_publish": False}]
    assert response.json()["result"]["dry_run"] is True
    assert response.json()["result"]["item_created"] is False
    assert "cfs" not in serialized


def test_api_recipe_returns_json(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.build_recipe",
        lambda prompt: {
            "map_title": "Flood parcel review",
            "user_intent": prompt,
            "parsed_request": {"topics": ["parcel", "flood"], "geography_terms": ["Concord"]},
            "selected_layers": [{"layer_name": "FloodPlain100year", "source_status": "active"}],
            "missing_data_needed": [],
            "confidence_score": 0.91,
        },
    )
    monkeypatch.setattr("app.api_routes.data_gap_records_from_recipe", lambda recipe: [])
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    response = client.post("/api/recipe", json={"prompt": "Show parcels in Concord floodplain"})

    assert response.status_code == 200
    assert response.json()["recipe"]["map_title"] == "Flood parcel review"
    assert response.json()["recipe"]["selected_layers"][0]["layer_name"] == "FloodPlain100year"


def test_api_review_packet_returns_stable_identifiers(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.build_review_packet",
        lambda prompt: {
            "recipe": {
                "map_title": "Flood parcel review",
                "selected_layers": [],
                "missing_data_needed": [],
                "review_reasons": [],
            },
            "webmap_json": {"title": "Flood parcel review", "operationalLayers": []},
            "warnings": {"preview_warnings": ["Draft only."]},
        },
    )
    monkeypatch.setattr(
        "app.api_routes.save_review_packet",
        lambda prompt, recipe, webmap: Path("outputs/review_packets/frontend_packet"),
    )
    monkeypatch.setattr("app.api_routes.validate_review_packet", lambda path: {"is_valid": True})
    monkeypatch.setattr("app.api_routes.build_layer_review_table", lambda recipe, webmap: [])
    monkeypatch.setattr("app.api_routes.record_request_history", lambda **kwargs: 1)
    client = TestClient(create_app())

    response = client.post("/api/review-packet", json={"prompt": "Show parcels in Concord floodplain"})

    assert response.status_code == 200
    assert response.json()["packet_id"] == "frontend_packet"
    assert response.json()["packet_path"] == "outputs\\review_packets\\frontend_packet" or response.json()["packet_path"] == "outputs/review_packets/frontend_packet"
    assert response.json()["preview_url"]
