import json
from pathlib import Path

from app import analysis_report_exporter as exporter
from app import analysis_summary_engine as summary_engine
from app import spatial_query_client
from app.analysis_summary_models import ANALYSIS_REPORT_REQUIRED_FILES


TARGET_LAYER = {
    "layer_key": "parcels",
    "layer_name": "Tax Parcels",
    "category": "parcel",
    "role": "base_layer",
    "layer_url": "https://example.test/arcgis/rest/services/OpenData/Tax_Parcels/MapServer/0",
    "source_status": "active",
    "fields": [
        {"name": "OBJECTID", "type": "esriFieldTypeOID"},
        {"name": "ZONING_GEN", "type": "esriFieldTypeString", "alias": "General Zoning"},
        {"name": "ACRES", "type": "esriFieldTypeDouble", "alias": "Acres"},
    ],
}


def sample_analysis_run() -> dict:
    receipt = {
        "status": "blocked",
        "raw_prompt": "Show parcels in Concord that are in the 100-year floodplain.",
        "operation_type": "select_by_intersection",
        "blocked_reasons": ["Optimized candidate parcel count 3314 exceeds safety limit 2000."],
        "broad_count": 110221,
        "optimized_candidate_count": 3314,
        "query_strategy": "chunked_geometry_first",
        "max_feature_limits": {"run_max_features": 2000, "hard_max_features": 5000},
        "target_layer": TARGET_LAYER,
        "constraint_layer": {"layer_key": "flood100", "layer_name": "FloodPlain100year", "category": "flood"},
        "optimized_query_plan": {
            "strategy": "chunked_geometry_first",
            "broad_count": 110221,
            "optimized_candidate_count": 3314,
            "chunks_planned": 2,
            "chunk_receipts": [
                {"chunk_id": "chunk_1", "deduplicated_candidate_count": 1800},
                {"chunk_id": "chunk_2", "deduplicated_candidate_count": 1514},
            ],
            "safety_limits": {"max_download_features_per_layer": 2000, "hard_max_download_features": 5000},
            "narrowing_suggestions": ["Add acreage, zoning, or smaller geography filters."],
        },
    }
    return {
        "analysis_run_id": "analysis_blocked_1",
        "raw_prompt": receipt["raw_prompt"],
        "status": "blocked",
        "recipe_json": {
            "map_title": "Concord Floodplain Parcels",
            "selected_layers": [TARGET_LAYER, {"layer_key": "flood100", "layer_name": "FloodPlain100year"}],
            "missing_data_needed": ["current_planning_cases"],
        },
        "operation_type": "select_by_intersection",
        "output_count": 0,
        "output_geojson_path": None,
        "analysis_receipt": receipt,
        "warnings": ["Analysis blocked by feature safety limit."],
    }


def sample_refinement_session() -> dict:
    return {
        "session_id": "refine_1",
        "source_analysis_run_id": "analysis_blocked_1",
        "raw_prompt": "Show parcels in Concord that are in the 100-year floodplain.",
        "blocked_reason": "Optimized candidate parcel count 3314 exceeds safety limit 2000.",
        "broad_count": 110221,
        "optimized_count": 3314,
        "safety_limit": 2000,
        "selected_option": {"option_id": "summary_only", "option_type": "summary_only"},
        "selected_parameters": {},
        "refined_result": {
            "mode": "summary_only",
            "status": "completed",
            "summary": {
                "geometry_downloaded": False,
                "geojson_created": False,
                "optimized_count": 3314,
                "narrowing_suggestions": ["Try an acreage threshold."],
            },
        },
        "status": "completed",
    }


class FakeGroupedClient:
    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls = []

    def query_grouped_statistics(self, layer_url, field_name, where=None, max_groups=50):
        self.calls.append(
            {
                "layer_url": layer_url,
                "field_name": field_name,
                "where": where,
                "max_groups": max_groups,
                "return_geometry": False,
            }
        )
        if self.fail:
            raise ValueError("statistics unsupported")
        return {
            "field_name": field_name,
            "rows": [{"group": "commercial", "count": 12}],
            "return_geometry": False,
            "request_method": "GET",
        }


def install_summary_fakes(monkeypatch):
    monkeypatch.setattr(summary_engine, "get_analysis_run", lambda analysis_run_id: sample_analysis_run())
    monkeypatch.setattr(summary_engine, "get_refinement_session", lambda session_id: sample_refinement_session())
    monkeypatch.setattr(summary_engine, "load_catalog_records", lambda: [TARGET_LAYER])
    monkeypatch.setattr(
        summary_engine,
        "load_field_profiles",
        lambda layer_keys=None: {
            "parcels": [
                {"field_name": "ZONING_GEN", "field_type": "esriFieldTypeString", "field_alias": "General Zoning"},
                {"field_name": "ACRES", "field_type": "esriFieldTypeDouble", "field_alias": "Acres"},
            ]
        },
    )
    monkeypatch.setattr(summary_engine, "load_value_profiles", lambda layer_keys=None: {})


def test_summary_engine_builds_count_and_safety_summary(monkeypatch):
    install_summary_fakes(monkeypatch)

    report = summary_engine.build_analysis_summary_from_run("analysis_blocked_1", query_client=FakeGroupedClient())

    assert report.broad_count == 110221
    assert report.optimized_count == 3314
    assert report.safety_limit == 2000
    assert report.analysis_status == "blocked"
    assert report.geometry_downloaded is False
    assert any(section.summary_type == "count_summary" for section in report.sections)


def test_grouped_summary_uses_return_geometry_false(monkeypatch):
    install_summary_fakes(monkeypatch)
    client = FakeGroupedClient()

    report = summary_engine.build_analysis_summary_from_run("analysis_blocked_1", query_client=client)

    assert client.calls
    assert all(call["return_geometry"] is False for call in client.calls)
    assert any(row.get("return_geometry") is False for row in report.grouped_summaries)
    assert any(row.get("status") == "ok" for row in report.grouped_summaries)


def test_unsupported_statistics_query_is_handled_safely(monkeypatch):
    install_summary_fakes(monkeypatch)

    report = summary_engine.build_analysis_summary_from_run("analysis_blocked_1", query_client=FakeGroupedClient(fail=True))

    assert any(row.get("status") == "unsupported" for row in report.grouped_summaries)
    assert report.geometry_downloaded is False


def test_spatial_query_client_caps_grouped_statistics_rows(monkeypatch):
    def fake_fetch(layer_url, params, timeout=30, prefer_post=False):
        features = [{"attributes": {"ZONING_GEN": f"group_{index}", "feature_count": index}} for index in range(20)]
        return {"features": features}, {"request_method": "GET"}

    monkeypatch.setattr(spatial_query_client, "_fetch_layer_query", fake_fetch)

    result = spatial_query_client.SpatialQueryClient().query_grouped_statistics(
        "https://example.test/layer/0",
        "ZONING_GEN",
        max_groups=5,
    )

    assert result["return_geometry"] is False
    assert result["group_count"] == 5
    assert result["server_row_count"] == 20
    assert result["truncated"] is True


def test_report_exporter_creates_required_files_and_preserves_warnings(monkeypatch, tmp_path):
    install_summary_fakes(monkeypatch)
    monkeypatch.setattr(exporter, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(exporter, "_record_history", lambda package, report_data, schema_name="automap": None)
    summary = summary_engine.build_analysis_summary_from_run("analysis_blocked_1", query_client=FakeGroupedClient())

    package = exporter.export_analysis_report(summary)

    assert package.validation["is_valid"] is True
    for file_name in ANALYSIS_REPORT_REQUIRED_FILES:
        assert (package.report_path / file_name).exists()
    csv_text = (package.report_path / "layer_summary.csv").read_text(encoding="utf-8")
    report_data = json.loads((package.report_path / "analysis_report.json").read_text(encoding="utf-8"))
    warning_report = json.loads((package.report_path / "warning_summary.json").read_text(encoding="utf-8"))
    html = (package.report_path / "analysis_report.html").read_text(encoding="utf-8")

    assert "Tax Parcels" in csv_text
    assert "FloodPlain100year" in csv_text
    assert report_data["broad_count"] == 110221
    assert report_data["geometry_downloaded"] is False
    assert "Analysis blocked by feature safety limit" in json.dumps(warning_report)
    assert "draft-only" in html.lower()
    assert "cfs_dev" not in (package.report_path / "analysis_report.md").read_text(encoding="utf-8").lower()


def test_report_validation_catches_missing_files_and_protected_markers(monkeypatch, tmp_path):
    install_summary_fakes(monkeypatch)
    monkeypatch.setattr(exporter, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(exporter, "_record_history", lambda package, report_data, schema_name="automap": None)
    package = exporter.export_analysis_report(
        summary_engine.build_analysis_summary_from_run("analysis_blocked_1", query_client=FakeGroupedClient())
    )

    (package.report_path / "summary_tables.json").unlink()
    missing = exporter.validate_analysis_report(package.report_path)
    assert missing["is_valid"] is False
    assert any("summary_tables.json" in error for error in missing["errors"])

    (package.report_path / "summary_tables.json").write_text("{}", encoding="utf-8")
    (package.report_path / "warning_summary.json").write_text("DATABASE_URL=bad cfs_dev", encoding="utf-8")
    protected = exporter.validate_analysis_report(package.report_path)
    assert protected["is_valid"] is False
    assert any("protected marker" in error for error in protected["errors"])


def test_refinement_report_marks_geometry_avoided(monkeypatch):
    install_summary_fakes(monkeypatch)

    report = summary_engine.build_analysis_summary_from_refinement("refine_1", query_client=FakeGroupedClient())

    assert report.source_refinement_session_id == "refine_1"
    assert report.selected_refinement_option == "summary_only"
    assert report.geometry_downloaded is False
    assert report.geojson_created is False


def test_report_history_table_is_additive_and_uses_automap_schema(monkeypatch):
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

    monkeypatch.setattr(exporter, "get_engine", lambda: FakeEngine())

    exporter.init_analysis_report_history_table()

    joined = "\n".join(statements)
    assert "analysis_report_history" in joined
    assert "CREATE TABLE IF NOT EXISTS" in joined
    assert "ALTER TABLE" in joined
    assert "cfs_dev" not in joined.lower()


def test_analysis_report_outputs_remain_ignored_by_git():
    gitignore = Path(".gitignore").read_text(encoding="utf-8")

    assert "outputs/*" in gitignore
