import json
from pathlib import Path

from app.intent_classifier import classify_intents
from app.prompt_parser import parse_prompt
from app.proximity_engine import classify_proximity_request
from app.recipe_engine import build_recipe
from app.request_brain import build_request_plan, normalize_request_text
from app.request_intelligence import build_request_intelligence
from app.spatial_intent_planner import plan_spatial_intent
from app.table_request_classifier import classify_table_request
from app.visible_map_qa import visible_map_qa


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "request_intelligence_prompts.json"
PRESET_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "automap_presets.json"


def catalog_record(
    layer_key,
    layer_name,
    category,
    *,
    source_priority=1,
    source_status="active",
    aliases=None,
    service_name=None,
    is_historical=False,
    historical_year=None,
    layer_id=0,
):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "aliases": aliases or [category],
        "description": "",
        "planning_use_cases": [category],
        "canonical_topic": category,
        "source_priority": source_priority,
        "source_status": source_status,
        "source_key": "cabarrus_new_opendata" if source_priority == 1 else "cabarrus_legacy_opendata",
        "service_name": service_name or layer_name,
        "service_url": f"https://example.com/{layer_key}/MapServer",
        "layer_url": f"https://example.com/{layer_key}/MapServer/{layer_id}",
        "geometry_type": "esriGeometryPolygon",
        "layer_id": layer_id,
        "is_verified": True,
        "is_group_layer": False,
        "is_feature_layer": True,
        "is_historical": is_historical,
        "historical_year": historical_year,
        "record_count": 1,
        "fields": [],
    }


def sample_catalog():
    return [
        catalog_record("new_parcels", "Tax Parcels", "parcel", aliases=["parcel", "parcels", "property", "tax parcel"], service_name="Tax_Parcels"),
        catalog_record("legacy_parcels", "Tax Parcels", "parcel", source_priority=2, source_status="legacy", service_name="opendata"),
        catalog_record("municipal", "MunicipalDistrict", "jurisdiction", aliases=["municipal", "municipality", "jurisdiction"], service_name="MunicipalDistrict"),
        catalog_record("floodway", "FloodWay", "flood", aliases=["flood", "floodway"], service_name="Flood_Hazard_Areas", layer_id=0),
        catalog_record("flood500", "FloodPlain500year", "flood", aliases=["flood", "500 year flood"], service_name="Flood_Hazard_Areas", layer_id=1),
        catalog_record("flood100", "FloodPlain100year", "flood", aliases=["flood", "floodplain", "100 year flood"], service_name="Flood_Hazard_Areas", layer_id=2),
        catalog_record("elem", "Elementary School District", "schools", service_name="School_Districts", layer_id=0),
        catalog_record("middle", "Middle School District", "schools", service_name="School_Districts", layer_id=1),
        catalog_record("high", "High School District", "schools", service_name="School_Districts", layer_id=2),
        catalog_record("concord_zoning", "Concord Zoning", "zoning", aliases=["zoning", "commercial zoning"], service_name="Zoning_By_Municipalities"),
        catalog_record("county_zoning", "Cabarrus County Zoning", "zoning", aliases=["zoning"], service_name="Cabarrus_County_Zoning"),
        catalog_record("roads", "Cabarrus County Centerlines", "transportation", aliases=["roads", "streets", "centerlines"], service_name="Cabarrus_County_Centerlines"),
        catalog_record("hydro", "CabarrusHydro", "environmental", aliases=["hydrology", "streams", "water"], service_name="Hydrology"),
        catalog_record("facilities", "County Facilities", "public_facilities", aliases=["county facilities", "public facilities"], service_name="County_Facilities"),
        catalog_record("legacy_parcels_2014", "Tax Parcels 2014", "parcel", source_priority=2, source_status="legacy_historical", is_historical=True, historical_year=2014),
        catalog_record("legacy_zoning_2014", "Zoning 2014", "zoning", source_priority=2, source_status="legacy_historical", is_historical=True, historical_year=2014),
    ]


def test_request_intelligence_fixture_has_at_least_30_prompts():
    prompts = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(prompts) >= 30


def test_fixture_prompts_classify_expected_intents_and_topics():
    prompts = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    for item in prompts:
        parsed = parse_prompt(item["prompt"])
        intelligence = build_request_intelligence(item["prompt"], parsed)["request_intelligence"]
        detected = set(intelligence["detected_intents"])

        assert set(item.get("expected_intents", [])).issubset(detected), item["prompt"]
        assert set(item.get("expected_topics", [])).issubset(set(parsed["topics"])), item["prompt"]


def test_spatial_planner_detects_near_intersect_and_review_questions():
    prompt = "Show parcels near floodplain and schools in Concord."
    parsed = parse_prompt(prompt)
    classification = classify_intents(prompt, parsed)
    spatial_plan = plan_spatial_intent(prompt, parsed, classification)
    bundle = build_request_intelligence(prompt, parsed)

    operations = {step["operation"] for step in spatial_plan["spatial_steps"]}
    questions = [item["question"] for item in bundle["request_intelligence"]["clarifying_questions"]]

    assert "buffer_or_proximity" in operations
    assert "intersect" in operations
    assert "What distance should count as near?" in questions


def test_recipe_includes_request_intelligence_and_analysis_plan():
    recipe = build_recipe("Show parcels in Concord that are in the 100-year floodplain.", sample_catalog(), persist_data_gaps=False)

    assert "request_intelligence" in recipe
    assert "analysis_plan" in recipe
    assert {"property_lookup", "flood_exposure"}.issubset(set(recipe["request_intelligence"]["detected_intents"]))
    assert {"parcel", "flood", "jurisdiction"}.issubset(set(recipe["analysis_plan"]["required_layers"]))
    assert any(layer["why_selected"] for layer in recipe["selected_layers"])
    assert any(layer["why_not_legacy"] for layer in recipe["selected_layers"])


def test_request_brain_normalizes_typos_and_extracts_zoning_parameters():
    prompt = "show commercial zonign aorund concord with bearny major roads"
    normalized = normalize_request_text(prompt)
    parsed = parse_prompt(prompt)
    plan = build_request_plan(prompt, parsed)

    assert normalized["normalized_text"] == "show commercial zoning around concord with nearby major roads"
    assert {"zoning", "transportation"}.issubset(set(parsed["topics"]))
    assert parsed["geography_terms"][0]["name"] == "Concord"
    assert plan["request_type"] == "zoning_context"
    assert plan["parameters"]["geography"] == "Concord"
    assert "commercial zoning" in plan["parameters"]["subtype_filter"]
    assert "roads" in plan["context_layers"]
    recipe = build_recipe(prompt, sample_catalog(), persist_data_gaps=False)
    assert recipe["request_plan"]["request_type"] == "zoning_context"


def test_commercial_zoning_variants_do_not_depend_on_exact_preset_wording():
    prompts = [
        "map commercial zoning near Concord roads",
        "show business zoning in Concord near major roads",
        "show commercial zoning around Concord",
        "show zoning and major roads in Concord",
        "show commercial zones near major roads in Cabarrus County",
    ]
    for prompt in prompts:
        parsed = parse_prompt(prompt)
        plan = build_request_plan(prompt, parsed)
        recipe = build_recipe(prompt, sample_catalog(), persist_data_gaps=False)
        selected_categories = {layer["category"] for layer in recipe["selected_layers"]}

        assert plan["request_type"] == "zoning_context", prompt
        assert "zoning" in selected_categories, prompt
        if "road" in prompt:
            assert "transportation" in selected_categories, prompt


def test_visible_map_qa_summarizes_counts_extent_and_fallbacks():
    class FakeClient:
        def query_count(self, layer_url, **kwargs):
            if "zoning" in layer_url and kwargs.get("where"):
                return {"count": 12}
            if "roads" in layer_url:
                return {"count": 44}
            return {"count": 5}

        def query_extent(self, layer_url, **kwargs):
            return {"extent": {"xmin": -80.62, "ymin": 35.35, "xmax": -80.52, "ymax": 35.44, "spatialReference": {"wkid": 4326}}}

    recipe = build_recipe("show commercial zoning around Concord with nearby major roads", sample_catalog(), persist_data_gaps=False)
    preview = {
        "initial_extent": {"xmin": -80.72, "ymin": 35.30, "xmax": -80.46, "ymax": 35.49, "spatialReference": {"wkid": 4326}},
        "context_layers": [
            {
                "layer_key": "county_zoning",
                "title": "Cabarrus County Zoning",
                "category": "zoning",
                "url": "https://example.test/zoning/0",
                "definition_expression": "ZONING_GEN IN ('COMMERCIAL', 'OFFICE')",
                "visibility": True,
            },
            {
                "layer_key": "roads",
                "title": "Road Centerlines",
                "category": "transportation",
                "url": "https://example.test/roads/0",
                "visibility": True,
            },
        ],
    }

    qa = visible_map_qa(preview, recipe, query_client=FakeClient())

    assert qa["visible_feature_total"] == 56
    assert qa["visible_extent"]["xmin"] < -80.62
    assert qa["visible_feature_summary"][0]["expected_role"] == "zoning"
    assert qa["visible_feature_summary"][1]["expected_role"] == "roads"


def test_visible_map_qa_broadens_empty_commercial_filter():
    class FakeClient:
        def query_count(self, layer_url, **kwargs):
            if kwargs.get("where"):
                return {"count": 0}
            return {"count": 27}

        def query_extent(self, layer_url, **kwargs):
            return {"extent": None}

    recipe = build_recipe("show commercial zoning around Concord", sample_catalog(), persist_data_gaps=False)
    preview = {
        "initial_extent": {"xmin": -80.72, "ymin": 35.30, "xmax": -80.46, "ymax": 35.49, "spatialReference": {"wkid": 4326}},
        "context_layers": [
            {
                "layer_key": "county_zoning",
                "title": "Cabarrus County Zoning",
                "category": "zoning",
                "url": "https://example.test/zoning/0",
                "definition_expression": "ZONING_GEN = 'COMMERCIAL'",
                "visibility": True,
            }
        ],
    }

    qa = visible_map_qa(preview, recipe, query_client=FakeClient())

    assert qa["visible_feature_total"] == 27
    assert qa["fallback_used"] is True
    assert "Commercial zoning values were not confidently identified" in qa["warnings"][0]


def test_current_new_layers_preferred_over_legacy_with_explanations():
    recipe = build_recipe("Show parcels in Concord.", sample_catalog(), persist_data_gaps=False)
    selected_keys = {layer["layer_key"] for layer in recipe["selected_layers"]}

    assert "new_parcels" in selected_keys
    assert "legacy_parcels" not in selected_keys
    assert any(rejected.get("superseded_by_new_opendata") for rejected in recipe["rejected_layers"])


def test_historical_layers_selected_only_when_year_requested():
    current_recipe = build_recipe("Show parcels and zoning.", sample_catalog(), persist_data_gaps=False)
    historical_recipe = build_recipe("Show 2014 parcels and zoning.", sample_catalog(), persist_data_gaps=False)

    assert "legacy_parcels_2014" not in {layer["layer_key"] for layer in current_recipe["selected_layers"]}
    assert {"legacy_parcels_2014", "legacy_zoning_2014"}.issubset(
        {layer["layer_key"] for layer in historical_recipe["selected_layers"]}
    )
    assert historical_recipe["request_intelligence"]["primary_intent"] == "historical_comparison"


def test_missing_development_data_generates_question_and_blocker():
    recipe = build_recipe("Show current permits near Kannapolis.", sample_catalog(), persist_data_gaps=False)
    questions = [item["question"] for item in recipe["request_intelligence"]["clarifying_questions"]]

    assert "permits" in recipe["missing_data_needed"]
    assert "development" not in recipe["missing_data_needed"]
    assert "How should AutoMap handle missing current development activity data?" in questions
    assert any("Missing verified catalog layer for permits" in blocker for blocker in recipe["analysis_plan"]["blockers"])
    assert recipe["request_intelligence"]["understood"] is False


def test_no_invented_layers_or_disallowed_references_in_recipe_output():
    catalog = sample_catalog()
    catalog_keys = {record["layer_key"] for record in catalog}
    recipe = build_recipe("Map commercial growth opportunities near major roads.", catalog, persist_data_gaps=False)
    serialized = json.dumps(recipe).lower()

    assert {layer["layer_key"] for layer in recipe["selected_layers"]}.issubset(catalog_keys)
    assert "cfs_dev" not in serialized
    assert "confirm-publish" not in serialized
    assert "publish-draft-webmap" not in serialized
    assert "arcgis_password" not in serialized


def test_automap_preset_fixture_is_distinct_safe_and_cabarrus_scoped():
    presets = json.loads(PRESET_FIXTURE_PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(presets).lower()

    assert len(presets) >= 7
    assert len({item["id"] for item in presets}) == len(presets)
    assert len({item["prompt"] for item in presets}) == len(presets)
    assert {item["expected_request_type"] for item in presets}.issuperset(
        {"proximity", "map", "table_request", "scenario", "historical_comparison"}
    )
    assert all("Cabarrus County, NC only" in item["expected_safety_notes"] for item in presets)
    assert "mecklenburg" not in serialized
    assert "wake county" not in serialized
    assert "database_url" not in serialized
    assert "service" + "_role" not in serialized
    assert "cfs_dev" not in serialized


def test_automap_presets_classify_to_expected_workflow_types():
    presets = json.loads(PRESET_FIXTURE_PATH.read_text(encoding="utf-8"))
    catalog = sample_catalog()

    for item in presets:
        prompt = item["prompt"]
        expected_type = item["expected_request_type"]
        expected_intent = item["expected_intent"]

        if expected_type == "proximity":
            proximity = classify_proximity_request(prompt)
            assert proximity["target_type"] == "nearest_fire_station"
            assert proximity["route_mode"] == "road_network"
            assert proximity["straight_line_supported"] is True
            continue

        if expected_type == "table_request":
            table = classify_table_request(prompt)
            assert table["table_requested"] is True
            assert expected_intent in table["intents"] or table["primary_intent"] == expected_intent
            assert table["primary_intent"] == "parcel_table"
            continue

        parsed = parse_prompt(prompt)
        intelligence = build_request_intelligence(prompt, parsed)["request_intelligence"]
        detected = set(intelligence["detected_intents"])
        recipe = build_recipe(prompt, catalog, persist_data_gaps=False)
        selected_categories = {layer["category"] for layer in recipe["selected_layers"]}

        assert expected_intent in detected, prompt

        if expected_type == "historical_comparison":
            assert parsed["historical_year"] == 2014
            assert recipe["request_intelligence"]["primary_intent"] == "historical_comparison"
            selected_keys = {layer["layer_key"] for layer in recipe["selected_layers"]}
            assert "legacy_parcels_2014" in selected_keys
            assert selected_categories.issuperset({"parcel", "zoning"})
        elif expected_type == "scenario":
            assert "growth_suitability" in detected
            assert {"transportation", "flood", "zoning"}.issubset(selected_categories)
        elif expected_intent == "development_activity":
            assert "permits" in recipe["missing_data_needed"]
            assert "planning cases" in recipe["missing_data_needed"]
            assert "jurisdiction" in selected_categories
        else:
            for domain in item["expected_layers_or_domains"]:
                if domain in {"address", "fire", "roads", "historical", "permits", "planning cases"}:
                    continue
                assert domain in selected_categories, prompt
