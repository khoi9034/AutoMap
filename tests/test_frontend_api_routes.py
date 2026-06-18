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
        "/api/scenarios",
        "/api/scenarios/{scenario_id}",
        "/api/scenarios/{scenario_id}/report",
        "/api/scenarios/report",
        "/api/scenarios/{scenario_id}/variants",
        "/api/scenario-variants/{variant_id}",
        "/api/scenario-comparisons",
        "/api/scenarios/{scenario_id}/to-recipe",
        "/api/scenario-variants/{variant_id}/to-recipe",
        "/api/parcels/parse",
        "/api/parcels/profile-fields",
        "/api/parcels/match",
        "/api/parcels/sets",
        "/api/parcels/sets/{parcel_set_id}",
        "/api/parcels/{parcel_set_id}/fetch-geometry",
        "/api/parcels/context",
        "/api/parcels/{parcel_set_id}/report",
        "/api/proximity",
        "/api/proximity/nearest",
        "/api/proximity/route-draft",
        "/api/proximity/results",
        "/api/proximity/results/{proximity_result_id}",
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
        "/api/composer/generate",
        "/api/composer/adjust",
        "/api/composer/export",
        "/api/composer/{composer_session_id}",
        "/api/tables/plan",
        "/api/tables/preview",
        "/api/tables/export",
        "/api/tables/requests",
        "/api/tables/requests/{table_request_id}",
        "/api/tables/exports",
        "/api/tables/exports/{export_id}",
        "/api/exhibits",
        "/api/exhibits/generate",
        "/api/exhibits/{exhibit_id}",
        "/api/exhibits/{exhibit_id}/html",
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


def test_api_scenario_routes_are_json_and_sanitized(monkeypatch):
    scenario = {
        "scenario_id": "scenario_test",
        "raw_prompt": "Map commercial growth opportunities.",
        "scenario_type": "commercial_growth_suitability",
        "scenario_title": "Commercial Growth Suitability",
        "source_coverage": {"warnings": ["proxy/context source only"]},
        "DATABASE_URL": "postgresql://secret",
    }
    monkeypatch.setattr("app.api_routes.build_scenario", lambda prompt: scenario)
    monkeypatch.setattr("app.api_routes.list_scenarios", lambda limit=50: [scenario])
    monkeypatch.setattr("app.api_routes.get_scenario", lambda scenario_id: scenario)
    monkeypatch.setattr(
        "app.api_routes.create_scenario_variant",
        lambda scenario_id, payload: {
            "variant_id": "variant_test",
            "source_scenario_id": scenario_id,
            "variant_name": payload.get("variant_name"),
            "safety_warnings": ["proxy context only"],
        },
    )
    monkeypatch.setattr(
        "app.api_routes.list_scenario_variants",
        lambda scenario_id=None, limit=50: [{"variant_id": "variant_test", "source_scenario_id": scenario_id}],
    )
    monkeypatch.setattr(
        "app.api_routes.get_scenario_variant",
        lambda variant_id: {"variant_id": variant_id, "source_scenario_id": "scenario_test", "variant_name": "Road access"},
    )
    monkeypatch.setattr(
        "app.api_routes.compare_scenarios",
        lambda scenario_ids, variant_ids: {
            "comparison_id": "comparison_test",
            "scenario_ids": scenario_ids,
            "variant_ids": variant_ids,
            "recommended_review_focus": ["review weights"],
        },
    )
    monkeypatch.setattr(
        "app.api_routes.build_recipe_from_scenario",
        lambda scenario_id, variant_id=None: {
            "scenario_id": scenario_id,
            "variant_id": variant_id,
            "published": False,
            "recipe": {"map_title": "Scenario Draft Recipe", "needs_review": True},
        },
    )
    monkeypatch.setattr(
        "app.api_routes.generate_scenario_report",
        lambda scenario_id: {
            "scenario_id": scenario_id,
            "report_folder": "outputs/scenario_reports/mock",
            "validation": {"is_valid": True},
        },
    )
    client = TestClient(create_app())

    created = client.post("/api/scenarios", json={"prompt": "Map commercial growth opportunities."})
    listed = client.get("/api/scenarios")
    detail = client.get("/api/scenarios/scenario_test")
    report = client.post("/api/scenarios/scenario_test/report", json={})
    variant = client.post("/api/scenarios/scenario_test/variants", json={"variant_name": "Road access priority"})
    variants = client.get("/api/scenarios/scenario_test/variants")
    variant_detail = client.get("/api/scenario-variants/variant_test")
    comparison = client.post("/api/scenario-comparisons", json={"scenario_ids": ["scenario_test"], "variant_ids": ["variant_test"]})
    recipe = client.post("/api/scenarios/scenario_test/to-recipe", json={"variant_id": "variant_test"})
    variant_recipe = client.post("/api/scenario-variants/variant_test/to-recipe", json={})
    serialized = json.dumps(
        [
            created.json(),
            listed.json(),
            detail.json(),
            report.json(),
            variant.json(),
            variants.json(),
            variant_detail.json(),
            comparison.json(),
            recipe.json(),
            variant_recipe.json(),
        ]
    ).lower()

    assert created.status_code == 200
    assert listed.status_code == 200
    assert detail.status_code == 200
    assert report.status_code == 200
    assert variant.status_code == 200
    assert variants.status_code == 200
    assert variant_detail.status_code == 200
    assert comparison.status_code == 200
    assert recipe.status_code == 200
    assert variant_recipe.status_code == 200
    assert "commercial_growth_suitability" in serialized
    assert "variant_test" in serialized
    assert "comparison_test" in serialized
    assert "database_url" not in serialized


def test_api_parcel_routes_are_json_and_sanitized(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.parse_parcel_input",
        lambda raw_input: {
            "raw_input": raw_input,
            "input_type": "pin",
            "parsed_identifiers": [{"identifier_type": "pin", "value": "5528-12-3456"}],
            "DATABASE_URL": "postgresql://secret",
        },
    )
    monkeypatch.setattr(
        "app.api_routes.create_parcel_set",
        lambda raw_input: {
            "parcel_set_id": "parcel_set_test",
            "match_status": "unmatched",
            "matched_count": 0,
            "unmatched_identifiers": [{"value": raw_input}],
            "candidate_matches": [],
            "warnings": ["needs review"],
            "geometry_output_path": None,
            "downloaded_geometry": False,
        },
    )
    monkeypatch.setattr(
        "app.api_routes.build_verified_parcel_field_map",
        lambda: {"layer_key": "tax_parcels", "fields_by_role": {"pin": ["PIN"]}, "stored_rows": 1},
    )
    monkeypatch.setattr(
        "app.api_routes.build_verified_address_field_map",
        lambda: {"layer_key": "addresses", "fields_by_role": {"full_address": ["FULLADDR"]}, "stored_rows": 1},
    )
    monkeypatch.setattr(
        "app.api_routes.fetch_selected_parcels",
        lambda parcel_set_id: {
            "parcel_set_id": parcel_set_id,
            "status": "blocked",
            "geometry_output_path": None,
            "downloaded_geometry": False,
            "warnings": ["No matched parcels."],
        },
    )
    monkeypatch.setattr("app.api_routes.list_parcel_sets", lambda limit=50: [{"parcel_set_id": "parcel_set_test"}])
    monkeypatch.setattr("app.api_routes.get_parcel_set", lambda parcel_set_id: {"parcel_set_id": parcel_set_id})
    monkeypatch.setattr(
        "app.api_routes.create_parcel_context_session",
        lambda prompt, requested_topics=None, nearby_distance=None: {
            "session_id": "parcel_context_test",
            "parcel_set_id": "parcel_set_test",
            "context_recipe": {"map_title": "Parcel Context Map", "needs_review": True},
            "warnings": ["draft only"],
        },
    )
    monkeypatch.setattr(
        "app.api_routes.generate_parcel_report",
        lambda parcel_set_id: {
            "report_id": "parcel_report_test",
            "parcel_set_id": parcel_set_id,
            "published": False,
            "DATABASE_URL": "postgresql://secret",
        },
    )
    client = TestClient(create_app())

    parsed = client.post("/api/parcels/parse", json={"raw_input": "5528-12-3456"})
    profiled = client.post("/api/parcels/profile-fields", json={})
    matched = client.post("/api/parcels/match", json={"raw_input": "5528-12-3456"})
    created = client.post("/api/parcels/sets", json={"raw_input": "5528-12-3456"})
    listed = client.get("/api/parcels/sets")
    detail = client.get("/api/parcels/sets/parcel_set_test")
    fetched = client.post("/api/parcels/parcel_set_test/fetch-geometry", json={})
    context = client.post("/api/parcels/context", json={"prompt": "Make a map of parcel 5528-12-3456"})
    report = client.post("/api/parcels/parcel_set_test/report", json={})
    serialized = json.dumps([
        parsed.json(),
        profiled.json(),
        matched.json(),
        created.json(),
        listed.json(),
        detail.json(),
        fetched.json(),
        context.json(),
        report.json(),
    ]).lower()

    assert parsed.status_code == 200
    assert profiled.status_code == 200
    assert matched.status_code == 200
    assert created.status_code == 200
    assert listed.status_code == 200
    assert detail.status_code == 200
    assert fetched.status_code == 200
    assert context.status_code == 200
    assert report.status_code == 200
    assert "parcel_set_test" in serialized
    assert "parcel_context_test" in serialized
    assert "database_url" not in serialized


def test_api_proximity_routes_are_json_and_sanitized(monkeypatch):
    monkeypatch.setattr(
        "app.api_routes.run_proximity_request",
        lambda prompt: {
            "proximity_result_id": "prox_result_test",
            "status": "needs_review",
            "raw_prompt": prompt,
            "warnings": ["Road-network routing requires an approved routing/network service."],
            "DATABASE_URL": "postgresql://secret",
        },
    )
    monkeypatch.setattr(
        "app.api_routes.run_nearest_facility",
        lambda origin_input, target_type: {
            "proximity_result_id": "prox_result_nearest",
            "origin_input": origin_input,
            "target_type": target_type,
            "distance_value": 1.2,
            "published": False,
        },
    )
    monkeypatch.setattr(
        "app.api_routes.run_route_draft",
        lambda origin_input, destination_input, raw_prompt=None: {
            "proximity_result_id": "prox_result_route",
            "origin_input": origin_input,
            "destination_input": destination_input,
            "route_status": "straight_line_reference",
            "route_mode": "straight_line_reference",
            "warnings": ["not a road route"],
            "published": False,
        },
    )
    monkeypatch.setattr("app.api_routes.list_proximity_results", lambda limit=50: [{"proximity_result_id": "prox_result_test"}])
    monkeypatch.setattr("app.api_routes.get_proximity_result", lambda result_id: {"proximity_result_id": result_id})
    client = TestClient(create_app())

    prompt = client.post("/api/proximity", json={"prompt": "How far is parcel 1 from nearest school?"})
    nearest = client.post("/api/proximity/nearest", json={"origin_input": "parcel 1", "target_type": "nearest_school"})
    route = client.post(
        "/api/proximity/route-draft",
        json={"origin_input": "65 Church St S", "destination_input": "123 Main St"},
    )
    listed = client.get("/api/proximity/results")
    detail = client.get("/api/proximity/results/prox_result_test")
    serialized = json.dumps([prompt.json(), nearest.json(), route.json(), listed.json(), detail.json()]).lower()

    assert prompt.status_code == 200
    assert nearest.status_code == 200
    assert route.status_code == 200
    assert listed.status_code == 200
    assert detail.status_code == 200
    assert "straight_line_reference" in serialized
    assert "confirm-publish" not in serialized
    assert "database_url" not in serialized
    assert "secret" not in serialized
    assert "secret" not in serialized
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized


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
        "app.api_routes.discover_sources",
        lambda keyword=None: {
            "services_discovered": 1,
            "services_inspected": 1,
            "candidate_count": 1,
            "candidate_records": [{**source, "layer_url": "https://example.test/AADT/FeatureServer/0"}],
            "downloaded_geometry": False,
        },
    )
    monkeypatch.setattr(
        "app.api_routes.verify_external_source",
        lambda source_key: {"source_key": source_key, "source": {**source, "inspected_metadata": {"is_verified": True}}, "catalog_upserts": 1, "downloaded_geometry": False},
    )
    monkeypatch.setattr(
        "app.api_routes.verify_all_external_sources",
        lambda: {"verified_sources": 1, "catalog_upserts": 1, "results": [], "downloaded_geometry": False},
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
    discovered = client.post("/api/external-sources/discover", json={"keyword": "aadt"})
    verified = client.post("/api/external-sources/verify", json={"source_key": "cabarrus_accela_plan_review_proxy"})
    verified_all = client.post("/api/external-sources/verify-all")
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
            "discovered": discovered.json(),
            "verified": verified.json(),
            "verified_all": verified_all.json(),
            "candidates": candidates.json(),
            "resolved": resolved.json(),
        }
    ).lower()

    assert listed.status_code == 200
    assert loaded.status_code == 200
    assert inspected.status_code == 200
    assert discovered.status_code == 200
    assert verified.status_code == 200
    assert verified_all.status_code == 200
    assert candidates.status_code == 200
    assert resolved.status_code == 200
    assert inspected.json()["catalog_upserts"] == 0
    assert discovered.json()["downloaded_geometry"] is False
    assert verified.json()["catalog_upserts"] == 1
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
