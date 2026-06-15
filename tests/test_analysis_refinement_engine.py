import json
from pathlib import Path

import pytest

from app import analysis_refinement_engine as refinement


TARGET_LAYER = {
    "layer_key": "parcels",
    "layer_name": "Tax Parcels",
    "category": "parcel",
    "layer_url": "https://example.test/parcels/MapServer/0",
    "service_url": "https://example.test/parcels/MapServer",
    "layer_id": 0,
    "object_id_field": "OBJECTID",
    "fields": [
        {"name": "OBJECTID", "type": "esriFieldTypeOID"},
        {"name": "ACRES", "type": "esriFieldTypeDouble", "alias": "Acres"},
        {"name": "ZONING_GEN", "type": "esriFieldTypeString", "alias": "General Zoning"},
    ],
}


def blocked_receipt(*, optimized_count=3314, chunk_counts=None):
    chunks = [
        {"chunk_id": f"chunk_{index + 1}", "deduplicated_candidate_count": count}
        for index, count in enumerate(chunk_counts or [1800, 1514])
    ]
    return {
        "status": "blocked",
        "raw_prompt": "Show parcels in Concord that are in the 100-year floodplain.",
        "blocked_reasons": ["Optimized candidate parcel count 3314 exceeds safety limit 2000."],
        "broad_count": 110221,
        "optimized_candidate_count": optimized_count,
        "query_strategy": "chunked_geometry_first",
        "max_feature_limits": {"run_max_features": 2000, "hard_max_features": 5000},
        "target_layer": TARGET_LAYER,
        "constraint_layer": {
            "layer_key": "flood100",
            "layer_name": "FloodPlain100year",
            "category": "flood",
        },
        "optimized_query_plan": {
            "strategy": "chunked_geometry_first",
            "strategy_explanation": "Server-side floodplain geometry chunks narrow parcel ObjectIDs first.",
            "broad_count": 110221,
            "optimized_candidate_count": optimized_count,
            "chunks_planned": len(chunks),
            "chunk_receipts": chunks,
            "target_layer": TARGET_LAYER,
            "constraint_layer": {
                "layer_key": "flood100",
                "layer_name": "FloodPlain100year",
                "category": "flood",
            },
            "safety_limits": {"max_download_features_per_layer": 2000, "hard_max_download_features": 5000},
        },
        "narrowing_suggestions": ["Add acreage, zoning, or smaller geography filters."],
    }


def blocked_run(**receipt_overrides):
    receipt = blocked_receipt(**receipt_overrides)
    return {
        "analysis_run_id": "analysis_blocked_1",
        "raw_prompt": receipt["raw_prompt"],
        "status": "blocked",
        "recipe_json": {"map_title": "Concord Floodplain Parcels"},
        "operation_type": "select_by_intersection",
        "selected_layer_keys": ["parcels", "municipal", "flood100"],
        "input_counts": {},
        "output_count": 0,
        "output_geojson_path": None,
        "analysis_receipt": receipt,
        "warnings": [],
    }


def install_memory_store(monkeypatch):
    store = {}

    def fake_store(session, schema_name="automap"):
        copied = json.loads(json.dumps(session, default=str))
        store[copied["session_id"]] = copied
        return copied

    def fake_get(session_id, schema_name="automap"):
        if session_id not in store:
            raise FileNotFoundError(session_id)
        return json.loads(json.dumps(store[session_id], default=str))

    monkeypatch.setattr(refinement, "_store_session", fake_store)
    monkeypatch.setattr(refinement, "get_refinement_session", fake_get)
    return store


def install_catalog(monkeypatch):
    monkeypatch.setattr(refinement, "load_catalog_records", lambda: [TARGET_LAYER])
    monkeypatch.setattr(refinement, "load_field_profiles", lambda layer_keys=None: {})


def test_init_refinement_tables_uses_additive_automap_table(monkeypatch):
    statements = []

    class FakeConnection:
        def execute(self, statement, params=None):
            statements.append(str(statement))

    class FakeBegin:
        def __enter__(self):
            return FakeConnection()

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeEngine:
        def begin(self):
            return FakeBegin()

    monkeypatch.setattr(refinement, "get_engine", lambda: FakeEngine())

    refinement.init_refinement_tables()

    joined = "\n".join(statements)
    assert "analysis_refinement_sessions" in joined
    assert "CREATE TABLE IF NOT EXISTS" in joined
    assert "ALTER TABLE" in joined
    assert "cfs_dev" not in joined.lower()


def test_blocked_analysis_creates_refinement_session(monkeypatch):
    install_memory_store(monkeypatch)
    install_catalog(monkeypatch)
    monkeypatch.setattr(refinement, "get_analysis_run", lambda analysis_run_id: blocked_run())

    session = refinement.create_refinement_session_from_blocked_run("analysis_blocked_1")
    option_ids = {option["option_id"] for option in session["options"]}

    assert session["status"] == "open"
    assert session["broad_count"] == 110221
    assert session["optimized_count"] == 3314
    assert session["safety_limit"] == 2000
    assert {"summary_only", "split_batches", "attribute_filter", "smaller_geography", "object_id_only"}.issubset(option_ids)


def test_summary_only_option_is_recommended_and_safe(monkeypatch):
    install_catalog(monkeypatch)

    options = refinement.generate_refinement_options(blocked_receipt(), blocked_run())
    summary = next(option for option in options if option["option_id"] == "summary_only")

    assert summary["recommended"] is True
    assert summary["safety_level"] == "safe"
    assert "no GeoJSON" in summary["expected_output"]


def test_attribute_filter_options_only_use_real_profiled_fields(monkeypatch):
    install_catalog(monkeypatch)

    options = refinement.generate_refinement_options(blocked_receipt(), blocked_run())
    attribute = next(option for option in options if option["option_id"] == "attribute_filter")
    serialized = json.dumps(attribute).lower()

    assert "acres" in serialized
    assert "zoning_gen" in serialized
    assert "vacant" not in serialized


def test_split_batch_plan_enforces_hard_max(monkeypatch):
    install_catalog(monkeypatch)

    options = refinement.generate_refinement_options(
        blocked_receipt(optimized_count=6000, chunk_counts=[1500, 1500, 1500, 1500]),
        blocked_run(optimized_count=6000, chunk_counts=[1500, 1500, 1500, 1500]),
    )
    split = next(option for option in options if option["option_id"] == "split_batches")

    assert split["safety_level"] == "blocked"
    assert split["suggested_parameters"]["total_candidate_count"] == 6000


def test_selected_option_is_stored(monkeypatch):
    install_memory_store(monkeypatch)
    install_catalog(monkeypatch)
    monkeypatch.setattr(refinement, "get_analysis_run", lambda analysis_run_id: blocked_run())
    session = refinement.create_refinement_session_from_blocked_run("analysis_blocked_1")

    selected = refinement.select_refinement_option(session["session_id"], "summary_only", {"reviewer": "local"})

    assert selected["status"] == "selected"
    assert selected["selected_option"]["option_id"] == "summary_only"
    assert selected["selected_parameters"] == {"reviewer": "local"}


def test_summary_only_executes_without_geometry_download(monkeypatch, tmp_path):
    install_memory_store(monkeypatch)
    install_catalog(monkeypatch)
    monkeypatch.setattr(refinement, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(refinement, "get_analysis_run", lambda analysis_run_id: blocked_run())
    session = refinement.create_refinement_session_from_blocked_run("analysis_blocked_1")
    refinement.select_refinement_option(session["session_id"], "summary_only", {})

    executed = refinement.execute_refined_analysis(session["session_id"])
    result = executed["refined_result"]
    output_folder = tmp_path / result["output_folder"]

    assert executed["status"] == "completed"
    assert result["mode"] == "summary_only"
    assert result["summary"]["geometry_downloaded"] is False
    assert not (output_folder / "analysis_result.geojson").exists()
    assert (output_folder / "refinement_summary.json").exists()
    assert (output_folder / "refinement_summary.md").exists()
    assert (output_folder / "refinement_receipt.json").exists()
    assert refinement.validate_refinement_output(output_folder)["is_valid"] is True


def test_summary_only_outputs_have_no_secrets_or_protected_database_refs(monkeypatch, tmp_path):
    install_memory_store(monkeypatch)
    install_catalog(monkeypatch)
    monkeypatch.setattr(refinement, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(refinement, "get_analysis_run", lambda analysis_run_id: blocked_run())
    session = refinement.create_refinement_session_from_blocked_run("analysis_blocked_1")
    refinement.select_refinement_option(session["session_id"], "summary_only", {})

    executed = refinement.execute_refined_analysis(session["session_id"])
    combined = ""
    for file_path in (tmp_path / executed["refined_result"]["output_folder"]).glob("*"):
        combined += file_path.read_text(encoding="utf-8").lower()

    assert "database_url" not in combined
    assert "password" not in combined
    assert "secret" not in combined
    assert "cfs_dev" not in combined
    assert "no arcgis item was created" in combined


def test_non_blocked_run_cannot_create_refinement(monkeypatch):
    run = blocked_run()
    run["status"] = "completed"
    monkeypatch.setattr(refinement, "get_analysis_run", lambda analysis_run_id: run)

    with pytest.raises(ValueError):
        refinement.create_refinement_session_from_blocked_run("analysis_completed")
