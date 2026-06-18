import json

from app.table_query_engine import execute_table_export, init_table_request_tables, preview_table_rows, validate_table_recipe
from app.table_request_classifier import classify_table_request
from app.table_recipe_engine import build_table_recipe
from app.table_safety import evaluate_table_safety


def layer(layer_key, layer_name, category, *, historical=False, year=None, record_count=12):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "service_name": layer_name,
        "category": category,
        "canonical_topic": category,
        "aliases": [layer_name, category],
        "planning_use_cases": [category],
        "source_status": "legacy_historical" if historical else "active",
        "approval_status": "approved",
        "source_priority": 1,
        "is_public": True,
        "is_active": True,
        "is_verified": True,
        "is_historical": historical,
        "historical_year": year,
        "layer_url": f"https://example.test/{layer_key}/0",
        "record_count": record_count,
        "fields": [
            {"name": "PIN14", "alias": "PIN14"},
            {"name": "SITE_ADDRESS", "alias": "Site Address"},
            {"name": "PERMIT_NO", "alias": "Permit Number"},
            {"name": "PERMIT_TYPE", "alias": "Permit Type"},
            {"name": "YEAR", "alias": "Year"},
            {"name": "ZONE_CODE", "alias": "Zoning Code"},
        ],
    }


def catalog():
    return [
        layer("tax_parcels", "Tax Parcels", "parcel", record_count=120),
        layer("zoning", "Current Zoning", "zoning", record_count=80),
        layer("permits_2014", "Historical Permits 2014", "permits", historical=True, year=2014, record_count=30),
        layer("zoning_2014", "Historical Zoning 2014", "zoning", historical=True, year=2014, record_count=30),
    ]


def no_profiles(layer_keys, schema_name="automap"):
    return {key: [] for key in layer_keys}


def test_table_request_classifier_detects_parcel_and_export():
    result = classify_table_request("Give me a CSV table of parcels in Concord.")

    assert result["table_requested"] is True
    assert "parcel_table" in result["intents"]
    assert "data_export" in result["intents"]


def test_historical_permit_prompt_without_table_keyword_is_table_request():
    result = classify_table_request("Show historical permits from 2014.")

    assert result["table_requested"] is True
    assert "permit_table" in result["intents"]
    assert "historical_table" in result["intents"]
    assert result["historical_year"] == 2014


def test_historical_table_prompt_selects_legacy_layer(monkeypatch):
    monkeypatch.setattr("app.table_recipe_engine.load_field_profiles", no_profiles)

    recipe = build_table_recipe("Show historical permits from 2014.", layer_catalog=catalog())

    assert recipe["historical_year"] == 2014
    assert recipe["source_layers"][0]["layer_key"] == "permits_2014"
    assert recipe["source_layers"][0]["is_historical"] is True
    assert any("Historical/legacy" in warning for warning in recipe["warnings"])


def test_current_permit_table_keeps_gap_when_no_official_source(monkeypatch):
    monkeypatch.setattr("app.table_recipe_engine.load_field_profiles", no_profiles)

    recipe = build_table_recipe("Give me a permits table near Kannapolis.", layer_catalog=catalog())

    assert "current_permits" in recipe["missing_data_needed"]
    assert any("Official current permit source is unresolved" in warning for warning in recipe["warnings"])
    assert all(not layer["is_historical"] for layer in recipe["source_layers"])


def test_table_preview_uses_return_geometry_false(monkeypatch):
    monkeypatch.setattr("app.table_recipe_engine.load_field_profiles", no_profiles)
    recipe = build_table_recipe("Give me a table of parcels in Concord.", layer_catalog=catalog())
    preview = preview_table_rows(recipe)

    assert recipe["query_options"]["returnGeometry"] is False
    assert preview["returnGeometry"] is False
    assert preview["query_options"]["returnGeometry"] is False


def test_export_blocks_above_hard_limit():
    decision = evaluate_table_safety(6000, 10)

    assert decision.export_ready is False
    assert decision.safety_status == "blocked_by_count"


def test_table_recipe_validation_blocks_geometry(monkeypatch):
    monkeypatch.setattr("app.table_recipe_engine.load_field_profiles", no_profiles)
    recipe = build_table_recipe("Give me a table of parcels in Concord.", layer_catalog=catalog())
    recipe["query_options"]["returnGeometry"] = True

    validation = validate_table_recipe(recipe)

    assert validation["is_valid"] is False
    assert any("returnGeometry=false" in error for error in validation["errors"])


def test_csv_json_markdown_exports_written(monkeypatch, tmp_path):
    monkeypatch.setattr("app.table_recipe_engine.load_field_profiles", no_profiles)
    monkeypatch.setattr("app.table_exporter.TABLE_OUTPUT_ROOT", tmp_path)
    recipe = build_table_recipe("Give me a table of parcels in Concord.", layer_catalog=catalog())

    result = execute_table_export(recipe)

    assert result["export_id"]
    assert result["returnGeometry"] is False
    file_names = {file["name"] for file in result["files"]}
    assert {"table_export.csv", "table_export.json", "table_summary.md", "export_manifest.json"}.issubset(file_names)


def test_no_invented_owner_fields_or_secrets(monkeypatch):
    monkeypatch.setattr("app.table_recipe_engine.load_field_profiles", no_profiles)
    recipe = build_table_recipe("Give planning a parcel list with zoning context.", layer_catalog=catalog())
    serialized = json.dumps(recipe).lower()

    assert "owner" not in [field["name"].lower() for field in recipe["selected_fields"]]
    assert "cfs_dev" not in serialized
    assert "database_url" not in serialized
    assert "secret" not in serialized


def test_table_request_tables_created_in_automap_schema(monkeypatch):
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

    monkeypatch.setattr("app.table_query_engine.get_engine", lambda: FakeEngine())

    init_table_request_tables()

    joined = "\n".join(statements).lower()
    assert "table_requests" in joined
    assert "table_export_history" in joined
    assert "automap" in joined
    assert "cfs_dev" not in joined
