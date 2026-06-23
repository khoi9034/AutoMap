import json

from app.parcel_context_engine import build_parcel_context_recipe, create_parcel_set, init_parcel_tables
from app.parcel_field_mapper import build_verified_parcel_field_map, identify_pin14_fields, identify_pin_fields
from app.parcel_input_parser import parse_parcel_input
from app.address_parcel_resolver import resolve_address_or_parcel_origin
from app.parcel_matcher import (
    build_parcel_where_clause,
    fetch_selected_parcel_geometry,
    infer_parcel_id_fields,
    match_parcels_by_address,
    match_parcels_by_identifier,
)
from app.parcel_reporter import generate_parcel_report


def mock_parcel_layer():
    return {
        "layer_key": "cabarrus_new_tax_parcels_0_tax_parcels",
        "layer_name": "Tax Parcels",
        "category": "parcel",
        "canonical_topic": "parcel",
        "is_verified": True,
        "is_active": True,
        "is_historical": False,
        "is_group_layer": False,
        "source_status": "active",
        "source_priority": 1,
        "layer_url": "https://example.test/Tax_Parcels/MapServer/0",
        "object_id_field": "OBJECTID",
        "fields": [
            {"name": "OBJECTID", "type": "esriFieldTypeOID", "alias": "OBJECTID"},
            {"name": "PIN14", "type": "esriFieldTypeString", "alias": "PIN14"},
            {"name": "PARCEL_ID", "type": "esriFieldTypeString", "alias": "Parcel ID"},
            {"name": "SITE_ADDRESS", "type": "esriFieldTypeString", "alias": "Site Address"},
        ],
    }


def parcel_context_catalog():
    return [
        mock_parcel_layer(),
        {
            "layer_key": "zoning",
            "layer_name": "Cabarrus County Zoning",
            "category": "zoning",
            "is_verified": True,
            "is_active": True,
            "is_historical": False,
            "is_group_layer": False,
            "source_status": "active",
            "source_priority": 1,
            "layer_url": "https://example.test/Zoning/0",
        },
        {
            "layer_key": "flood_100",
            "layer_name": "FloodPlain100year",
            "category": "flood",
            "is_verified": True,
            "is_active": True,
            "is_historical": False,
            "is_group_layer": False,
            "source_status": "active",
            "source_priority": 1,
            "layer_url": "https://example.test/Flood/2",
        },
        {
            "layer_key": "schools",
            "layer_name": "Elementary School District",
            "category": "schools",
            "is_verified": True,
            "is_active": True,
            "is_historical": False,
            "is_group_layer": False,
            "source_status": "active",
            "source_priority": 1,
            "layer_url": "https://example.test/Schools/0",
        },
        {
            "layer_key": "roads",
            "layer_name": "Road Centerlines",
            "category": "transportation",
            "is_verified": True,
            "is_active": True,
            "is_historical": False,
            "is_group_layer": False,
            "source_status": "active",
            "source_priority": 1,
            "layer_url": "https://example.test/Roads/0",
        },
        {
            "layer_key": "accela_proxy",
            "layer_name": "Plan Reviews",
            "category": "development_activity_proxy",
            "is_verified": True,
            "is_active": True,
            "is_historical": False,
            "is_group_layer": False,
            "source_status": "proxy",
            "approval_status": "approved",
            "source_key": "cabarrus_accela_plan_review_proxy",
            "source_priority": 3,
            "layer_url": "https://example.test/Accela/0",
            "known_limitations": "Proxy only; not final permit approval.",
        },
    ]


def stored_parcel_set():
    return {
        "parcel_set_id": "parcel_set_test",
        "raw_input": "5528-12-3456",
        "input_type": "pin",
        "parsed_identifiers": [{"identifier_type": "pin", "value": "5528-12-3456", "normalized_value": "5528-12-3456"}],
        "matched_parcels": [{"pin": "5528-12-3456", "source_layer_key": "cabarrus_new_tax_parcels_0_tax_parcels"}],
        "unmatched_identifiers": [],
        "match_status": "matched",
        "source_layer_key": "cabarrus_new_tax_parcels_0_tax_parcels",
        "matched_count": 1,
        "warnings": [],
        "downloaded_geometry": False,
    }


class MockSpatialQueryClient:
    def __init__(self, count=1):
        self.count = count
        self.feature_queries = []

    def query_count(self, layer_url, *, where=None, **kwargs):
        return {"count": self.count, "where": where, "return_geometry": False}

    def query_features(self, layer_url, *, where=None, out_fields="*", return_geometry=True, **kwargs):
        self.feature_queries.append({"where": where, "return_geometry": return_geometry})
        feature = {
            "type": "Feature",
            "properties": {
                "OBJECTID": 1,
                "PIN14": "55281234567890",
                "PARCEL_ID": "5528-12-3456",
                "SITE_ADDRESS": "65 CHURCH ST S",
            },
            "geometry": {"type": "Polygon", "coordinates": [[[-80, 35], [-80, 36], [-79, 36], [-80, 35]]]},
        }
        return {
            "status": "ok",
            "features": [feature],
            "feature_collection": {"type": "FeatureCollection", "features": [feature]},
            "count": self.count,
        }

    def query_features_by_object_ids(self, layer_url, *, object_ids, out_fields="*", return_geometry=True, **kwargs):
        self.feature_queries.append({"object_ids": object_ids, "return_geometry": return_geometry})
        return self.query_features(layer_url, where=f"OBJECTID IN ({','.join(str(item) for item in object_ids)})", return_geometry=return_geometry)


def test_parcel_parser_extracts_pin_pin14_and_address():
    result = parse_parcel_input("PIN14: 55281234567890, parcel 5528-12-3456, 65 Church St S")
    identifiers = result["parsed_identifiers"]

    assert result["parcel_intent"] is True
    assert any(item["identifier_type"] == "pin14" for item in identifiers)
    assert any(item["identifier_type"] == "pin" for item in identifiers)
    assert result["address_candidates"][0]["identifier_type"] == "address"


def test_address_prompt_parses_as_address_not_parcel_id():
    result = parse_parcel_input("my address 793 bartram ave")

    assert result["input_type"] == "address"
    assert result["address_candidates"][0]["value"].lower() == "793 bartram ave"
    assert result["parsed_identifiers"] == []


def test_bare_street_address_is_likely_address_not_parcel_id():
    result = parse_parcel_input("793 bartram ave")

    assert result["input_type"] == "address"
    assert result["address_candidates"]
    assert result["parsed_identifiers"] == []


def test_labeled_parcel_still_parses_as_pin():
    result = parse_parcel_input("parcel 5528-12-3456")

    assert result["input_type"] == "pin"
    assert result["parsed_identifiers"][0]["identifier_type"] == "pin"


def test_address_resolver_does_not_use_owner_lookup_by_default(monkeypatch):
    monkeypatch.setattr(
        "app.address_parcel_resolver.resolve_verified_address",
        lambda address, **kwargs: {
            "status": "unmatched",
            "match_status": "unmatched",
            "matched_address_candidates": [],
            "matched_parcel_candidates": [],
            "candidate_matches": [],
            "warnings": ["Address not found in Cabarrus County records."],
            "downloaded_geometry": False,
            "can_preview": False,
            "owner_lookup_used": False,
        },
    )

    result = resolve_address_or_parcel_origin("my address 793 bartram ave")

    assert result["origin_type"] == "address"
    assert result["match_status"] == "unmatched"
    assert result["owner_lookup_used"] is False
    assert "Address not found" in " ".join(result["warnings"])


def test_owner_lookup_is_privacy_sensitive_and_needs_review():
    result = parse_parcel_input("Find parcels owned by Smith")

    assert result["owner_lookup_requested"] is True
    assert result["privacy_sensitive"] is True
    assert result["needs_review"] is True
    assert "Owner-name lookup" in result["warnings"][0]


def test_parcel_matcher_uses_real_fields_and_return_geometry_false(monkeypatch):
    monkeypatch.setattr("app.parcel_matcher.load_field_profiles", lambda layer_keys, schema_name="automap": {})
    client = MockSpatialQueryClient()
    identifier = parse_parcel_input("5528-12-3456")["parsed_identifiers"][0]

    result = match_parcels_by_identifier([identifier], layer_catalog=[mock_parcel_layer()], client=client)

    assert result["matched_count"] == 1
    assert result["match_status"] == "matched"
    assert client.feature_queries[0]["return_geometry"] is False
    assert result["downloaded_geometry"] is False


def test_field_mapper_identifies_pin_and_pin14_fields(monkeypatch):
    profiles = [
        {"field_name": "PIN", "field_alias": "PIN", "field_type": "esriFieldTypeString"},
        {"field_name": "PIN14", "field_alias": "PIN14", "field_type": "esriFieldTypeString"},
        {"field_name": "OBJECTID", "field_alias": "OBJECTID", "field_type": "esriFieldTypeOID", "is_object_id": True},
    ]

    assert identify_pin_fields(profiles)[0]["field_name"] == "PIN"
    assert identify_pin14_fields(profiles)[0]["field_name"] == "PIN14"

    monkeypatch.setattr("app.parcel_field_mapper.find_tax_parcel_layer", lambda: mock_parcel_layer())
    monkeypatch.setattr("app.parcel_field_mapper.load_field_profiles", lambda layer_keys, schema_name="automap": {mock_parcel_layer()["layer_key"]: profiles})
    monkeypatch.setattr("app.parcel_field_mapper._store_field_map", lambda rows, schema_name="automap": len(rows))

    field_map = build_verified_parcel_field_map()

    assert field_map["fields_by_role"]["pin"] == ["PIN"]
    assert field_map["fields_by_role"]["pin14"] == ["PIN14"]
    assert field_map["fields_by_role"]["object_id"] == ["OBJECTID"]


def test_build_where_clause_does_not_invent_fields(monkeypatch):
    monkeypatch.setattr("app.parcel_matcher.load_field_profiles", lambda layer_keys, schema_name="automap": {})
    field_map = infer_parcel_id_fields(mock_parcel_layer())
    identifier = {"identifier_type": "pin14", "normalized_value": "55281234567890"}
    where_clause, warnings = build_parcel_where_clause([identifier], field_map)

    assert "PIN14" in where_clause
    assert "REPLACE(REPLACE(UPPER(PIN14)" in where_clause
    assert warnings == []
    no_field_clause, no_field_warnings = build_parcel_where_clause([{"identifier_type": "owner", "normalized_value": "SMITH"}], field_map)
    assert no_field_clause is None
    assert no_field_warnings


def test_normalized_pin_matching_removes_hyphens(monkeypatch):
    monkeypatch.setattr("app.parcel_matcher.load_field_profiles", lambda layer_keys, schema_name="automap": {})
    field_map = infer_parcel_id_fields(mock_parcel_layer())
    identifier = {"identifier_type": "pin", "value": "5528-12-3456", "normalized_value": "5528-12-3456"}

    where_clause, warnings = build_parcel_where_clause([identifier], field_map)

    assert warnings == []
    assert "5528123456" in where_clause
    assert "REPLACE(REPLACE(UPPER(" in where_clause


def test_multiple_matches_trigger_needs_review(monkeypatch):
    monkeypatch.setattr("app.parcel_matcher.load_field_profiles", lambda layer_keys, schema_name="automap": {})
    client = MockSpatialQueryClient(count=2)
    identifier = parse_parcel_input("5528-12-3456")["parsed_identifiers"][0]

    result = match_parcels_by_identifier([identifier], layer_catalog=[mock_parcel_layer()], client=client)

    assert result["match_status"] == "needs_review"
    assert result["multiple_match_identifiers"]
    assert result["candidate_matches"]


def test_address_matching_returns_candidates_when_ambiguous(monkeypatch):
    monkeypatch.setattr("app.parcel_matcher.build_verified_address_field_map", lambda schema_name="automap": {
        "layer_key": "addresses",
        "layer_url": "https://example.test/Addresses/0",
        "fields_by_role": {
            "object_id": ["OBJECTID"],
            "full_address": ["FULL_ADDRESS"],
            "pin": [],
            "pin14": [],
            "parcel_id": [],
        },
        "warnings": [],
    })
    monkeypatch.setattr("app.parcel_matcher.load_field_profiles", lambda layer_keys, schema_name="automap": {})
    client = MockSpatialQueryClient(count=2)
    address = {"identifier_type": "address", "value": "65 Church St S", "normalized_value": "65 CHURCH ST S"}

    result = match_parcels_by_address([address], layer_catalog=[mock_parcel_layer()], client=client)

    assert result["address_candidates"]
    assert result["match_status"] in {"needs_review", "unmatched", "partial"}


def test_parcel_set_creation_works_with_mocked_matcher(monkeypatch):
    monkeypatch.setattr(
        "app.parcel_context_engine.match_parcels_by_identifier",
        lambda identifiers, **kwargs: {
            "source_layer_key": "cabarrus_new_tax_parcels_0_tax_parcels",
            "matched_parcels": [{"pin": "5528-12-3456"}],
            "unmatched_identifiers": [],
            "match_status": "matched",
            "warnings": [],
            "downloaded_geometry": False,
        },
    )

    result = create_parcel_set("5528-12-3456", layer_catalog=[mock_parcel_layer()], persist=False)

    assert result["match_status"] == "matched"
    assert result["matched_count"] == 1
    assert result["downloaded_geometry"] is False


def test_parcel_context_recipe_selects_tax_parcels_first_and_requested_context(monkeypatch):
    stored = stored_parcel_set()
    monkeypatch.setattr("app.parcel_context_engine.get_parcel_set", lambda parcel_set_id, schema_name="automap": stored)

    recipe = build_parcel_context_recipe(
        stored["parcel_set_id"],
        requested_topics=["zoning", "flood", "schools", "transportation"],
        raw_prompt="Make a map of parcel 5528-12-3456 and show zoning, floodplain, schools, and roads.",
        layer_catalog=parcel_context_catalog(),
    )

    categories = [layer["category"] for layer in recipe["selected_layers"]]
    assert categories[0] == "parcel"
    assert {"zoning", "flood", "schools", "transportation"}.issubset(set(categories))
    assert recipe["parcel_context"]["parcel_set_id"] == stored["parcel_set_id"]
    assert "current_permits" not in recipe["missing_data_needed"]


def test_parcel_context_adds_selected_parcel_derived_layer(monkeypatch):
    stored = {**stored_parcel_set(), "geometry_output_path": "outputs/parcel_context/test/selected_parcels.geojson"}
    monkeypatch.setattr("app.parcel_context_engine.get_parcel_set", lambda parcel_set_id, schema_name="automap": stored)

    recipe = build_parcel_context_recipe(
        stored["parcel_set_id"],
        requested_topics=["zoning"],
        raw_prompt="Make a map of parcel 5528-12-3456 and show zoning.",
        layer_catalog=parcel_context_catalog(),
    )

    assert recipe["map_title"] == "Selected Parcels Context Map"
    assert recipe["selected_layers"][0]["derived_local_parcel_output"] is True
    assert recipe["parcel_context"]["geometry_output_path"].endswith("selected_parcels.geojson")


def test_nearby_prompt_requires_distance_question(monkeypatch):
    stored = stored_parcel_set()
    monkeypatch.setattr("app.parcel_context_engine.get_parcel_set", lambda parcel_set_id, schema_name="automap": stored)

    recipe = build_parcel_context_recipe(
        stored["parcel_set_id"],
        raw_prompt="Show parcel 5528-12-3456 near roads.",
        layer_catalog=parcel_context_catalog(),
    )

    assert "nearby_distance_missing" in recipe["request_intelligence"]["ambiguity_flags"]
    assert recipe["request_intelligence"]["clarifying_questions"]


def test_current_permits_remains_missing_and_proxy_labeled(monkeypatch):
    stored = stored_parcel_set()
    monkeypatch.setattr("app.parcel_context_engine.get_parcel_set", lambda parcel_set_id, schema_name="automap": stored)

    recipe = build_parcel_context_recipe(
        stored["parcel_set_id"],
        requested_topics=["development"],
        raw_prompt="Map my parcels and show permits or planning activity around them.",
        layer_catalog=parcel_context_catalog(),
    )
    serialized = json.dumps(recipe).lower()

    assert "current_permits" in recipe["missing_data_needed"]
    assert "proxy" in serialized
    assert "cfs_dev" not in serialized
    assert "database_url" not in serialized


def test_parcel_tables_created_in_automap_schema(monkeypatch):
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

    monkeypatch.setattr("app.parcel_context_engine.get_engine", lambda: FakeEngine())

    init_parcel_tables()

    joined = "\n".join(statements).lower()
    assert "parcel_sets" in joined
    assert "parcel_context_sessions" in joined
    assert "geometry_output_path" in joined
    assert "automap" in joined
    assert "cfs_dev" not in joined


def test_selected_parcel_geojson_output_validates_on_small_match(monkeypatch, tmp_path):
    stored = {
        **stored_parcel_set(),
        "matched_parcels": [{"object_id": 1, "pin": "5528-12-3456", "source_layer_key": "cabarrus_new_tax_parcels_0_tax_parcels"}],
    }
    monkeypatch.setattr("app.parcel_matcher.load_field_profiles", lambda layer_keys, schema_name="automap": {})
    monkeypatch.setattr("app.parcel_matcher._output_root", lambda: tmp_path)

    result = fetch_selected_parcel_geometry(stored, layer_catalog=[mock_parcel_layer()], client=MockSpatialQueryClient())

    assert result["status"] == "ok"
    assert result["downloaded_geometry"] is True
    geojson = json.loads((tmp_path / result["output_folder"].split("/")[-1] / "selected_parcels.geojson").read_text(encoding="utf-8"))
    assert geojson["type"] == "FeatureCollection"


def test_geometry_fetch_blocks_over_safe_limit():
    stored = {**stored_parcel_set(), "matched_count": 101, "matched_parcels": [{"object_id": index} for index in range(101)]}

    result = fetch_selected_parcel_geometry(stored, layer_catalog=[mock_parcel_layer()], client=MockSpatialQueryClient())

    assert result["status"] == "blocked"
    assert result["downloaded_geometry"] is False
    assert "exceeds selected parcel geometry limit" in result["warnings"][0]


def test_parcel_report_writes_required_files(monkeypatch, tmp_path):
    stored = stored_parcel_set()
    monkeypatch.setattr("app.parcel_reporter.get_parcel_set", lambda parcel_set_id, schema_name="automap": stored)
    monkeypatch.setattr("app.parcel_context_engine.get_parcel_set", lambda parcel_set_id, schema_name="automap": stored)
    monkeypatch.setattr("app.parcel_reporter._output_root", lambda: tmp_path)

    report = generate_parcel_report(stored["parcel_set_id"])

    assert report["validation"]["is_valid"] is True
    report_folder = tmp_path / report["report_id"]
    assert (report_folder / "parcel_context_report.html").exists()
    assert (report_folder / "parcel_layer_summary.csv").exists()
    combined = "\n".join(path.read_text(encoding="utf-8") for path in report_folder.iterdir() if path.is_file()).lower()
    assert "draft" in combined
    assert "no arcgis item" in combined
    assert "database_url" not in combined
