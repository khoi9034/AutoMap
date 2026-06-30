import json
from pathlib import Path

from app.automap_brain.domain_ontology import DOMAIN_ONTOLOGY
from app.automap_brain.aoi_planner import apply_aoi_to_preview_config, build_aoi_plan, request_wants_major_roads, visual_complexity_score
from app.automap_brain.layer_ranker import rank_candidate_layers
from app.automap_brain.normalizer import normalize_prompt
from app.automap_brain.request_parser import build_brain_plan
from app.prompt_parser import parse_prompt
from app.recipe_engine import build_recipe


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "automap_brain_benchmark.json"


def catalog_record(layer_key, layer_name, category, *, geometry_type="esriGeometryPolygon", is_historical=False, historical_year=None):
    return {
        "layer_key": layer_key,
        "layer_name": layer_name,
        "category": category,
        "aliases": [category, layer_name],
        "description": layer_name,
        "planning_use_cases": [category],
        "canonical_topic": category,
        "source_priority": 1,
        "source_status": "active",
        "source_key": "cabarrus_new_opendata",
        "service_name": layer_name,
        "service_url": f"https://example.test/{layer_key}/MapServer",
        "layer_url": f"https://example.test/{layer_key}/MapServer/0",
        "geometry_type": geometry_type,
        "layer_id": 0,
        "is_verified": True,
        "is_group_layer": False,
        "is_feature_layer": True,
        "is_historical": is_historical,
        "historical_year": historical_year,
        "record_count": 10,
        "fields": [{"name": "PIN14", "alias": "PIN14"}],
    }


def sample_catalog():
    return [
        catalog_record("tax_parcels", "Tax Parcels", "parcel"),
        catalog_record("zoning", "Cabarrus County Zoning", "zoning"),
        catalog_record("concord_zoning", "Concord Zoning", "zoning"),
        catalog_record("flood_100", "FloodPlain100year", "flood"),
        catalog_record("roads", "Cabarrus County Centerlines", "transportation", geometry_type="esriGeometryPolyline"),
        catalog_record("municipal", "Municipal District", "jurisdiction"),
        catalog_record("planning_cases", "Planning Cases", "planning_cases", geometry_type="esriGeometryPoint"),
        catalog_record("legacy_parcels_2014", "Tax Parcels 2014", "parcel", is_historical=True, historical_year=2014),
        catalog_record("legacy_zoning_2014", "Zoning 2014", "zoning", is_historical=True, historical_year=2014),
    ]


def test_brain_ontology_covers_core_county_gis_domains():
    assert {"zoning", "floodplain", "transportation", "table_requests", "address_proximity"}.issubset(DOMAIN_ONTOLOGY)
    assert "commercial zoning" in DOMAIN_ONTOLOGY["zoning"]["synonyms"]
    assert "major roads" in DOMAIN_ONTOLOGY["transportation"]["synonyms"]


def test_brain_normalizer_handles_safe_typos():
    normalized = normalize_prompt("show commercial zonign aorund concord with bearny major roads")

    assert normalized["normalized_text"] == "show commercial zoning around concord with nearby major roads"
    assert normalized["corrected"] is True


def test_brain_benchmark_has_required_prompt_coverage():
    prompts = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    assert len(prompts) >= 80
    assert sum(1 for item in prompts if item["expected_request_type"] == "zoning_context") >= 5
    assert sum(1 for item in prompts if item["expected_request_type"] == "table_request") >= 5
    assert sum(1 for item in prompts if item["expected_request_type"] == "unsupported") >= 3


def test_brain_benchmark_parses_expected_request_types():
    prompts = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    strict_prompts = [
        item
        for item in prompts
        if item["prompt"]
        in {
            "show commercial zoning around Concord with nearby major roads",
            "show commercial zonign aorund concord with bearny major roads",
            "map commercial zones near major roads in Concord",
            "show parcels in Concord that are in the 100-year floodplain",
            "give me a table of parcels in Cabarrus County with parcel ID, acreage, municipality, and zoning",
            "make a map of my address 793 bartram ave and include nearest line to the nearest fire station",
            "map parcels in Charlotte near flood zones",
        }
    ]

    for item in strict_prompts:
        parsed = parse_prompt(item["prompt"])
        plan = build_brain_plan(item["prompt"], parsed)
        domains = {plan.get("primary_domain"), *(plan.get("secondary_domains") or [])}

        assert plan["request_type"] == item["expected_request_type"], item["prompt"]
        assert item["expected_output_mode"] == plan["output_mode"], item["prompt"]
        for domain in item["expected_domains"]:
            assert domain in domains, item["prompt"]
        if item["expected_geography"]:
            assert plan["geography"] == item["expected_geography"], item["prompt"]
        assert "Real ArcGIS publishing is disabled." in plan["safety_notes"]


def test_semantic_layer_ranking_explains_selected_zoning_and_roads():
    plan = build_brain_plan("show commercial zoning around Concord with nearby major roads")
    ranked = rank_candidate_layers(plan, sample_catalog())
    categories = {item["category"] for item in ranked[:4]}

    assert {"zoning", "transportation"}.issubset(categories)
    assert all(item["brain_rank_reasons"] for item in ranked[:3])


def test_recipe_uses_brain_v2_metadata_and_visible_roles():
    recipe = build_recipe("show commercial zoning around Concord with nearby major roads", sample_catalog(), persist_data_gaps=False)

    assert recipe["request_plan"]["brain_version"] == "automap_brain_v2"
    assert recipe["request_plan"]["request_type"] == "zoning_context"
    assert recipe["automap_brain"]["version"] == "automap_brain_v2"
    assert recipe["automap_brain"]["layer_rankings"]
    assert recipe["automap_brain"]["field_value_resolution"]["filter_plan"]
    assert "commercial zoning" in recipe["request_plan"]["parameters"]["subtype_filter"]
    assert "transportation" in {layer["category"] for layer in recipe["selected_layers"]}


def test_aoi_planner_detects_concord_around_buffer():
    recipe = build_recipe("show commercial zoning around Concord with nearby major roads", sample_catalog(), persist_data_gaps=False)

    aoi = build_aoi_plan(recipe)

    assert aoi["type"] == "municipality"
    assert aoi["geography_name"] == "Concord"
    assert aoi["buffer_distance"]["value"] == 2.0
    assert aoi["summary"] == "Concord boundary + 2 mile buffer"
    assert aoi["extent"]["xmin"] < -80.72
    assert aoi["extent"]["xmax"] > -80.46


def test_major_roads_require_prompt_intent_not_advisory_filter():
    recipe = build_recipe("commercial zoning around Concord", sample_catalog(), persist_data_gaps=False)
    recipe["request_plan"].setdefault("filters", []).append({"domain": "transportation", "value": "major roads"})

    assert request_wants_major_roads(recipe) is False


def test_aoi_application_clips_local_zoning_layers_and_hides_extra_context():
    recipe = build_recipe("show commercial zoning around Concord with nearby major roads", sample_catalog(), persist_data_gaps=False)
    preview = {
        "operational_layers": [
            {"layer_key": "zoning", "title": "Cabarrus County Zoning", "category": "zoning", "definition_expression": "ZONE = 'GC'", "visibility": True},
            {"layer_key": "municipal_zoning", "title": "Zoning context", "category": "zoning", "visibility": True},
            {"layer_key": "roads", "title": "Road Centerlines", "category": "transportation", "visibility": True},
            {"layer_key": "tax_parcels", "title": "Tax Parcels", "category": "parcel", "visibility": True},
        ]
    }

    bounded = apply_aoi_to_preview_config(preview, recipe)
    layers = bounded["operational_layers"]
    zoning = next(layer for layer in layers if layer["layer_key"] == "zoning")
    zoning_context = next(layer for layer in layers if layer["layer_key"] == "municipal_zoning")
    roads = next(layer for layer in layers if layer["layer_key"] == "roads")
    parcels = next(layer for layer in layers if layer["layer_key"] == "tax_parcels")

    assert bounded["focus_extent"] == bounded["aoi"]["extent"]
    assert zoning["clipped_to_aoi"] is True
    assert zoning_context["visibility"] is False
    assert zoning_context["diagnostics_only"] is True
    assert zoning_context["simplification_applied"] is True
    assert roads["clipped_to_aoi"] is True
    assert roads["legend_label"] == "Road context"
    assert "Major-road classification unavailable" in " ".join(roads["review_warnings"])
    assert parcels["visibility"] is False
    assert parcels["diagnostics_only"] is True


def test_aoi_application_filters_major_roads_when_route_fields_exist():
    recipe = build_recipe("show commercial zoning around Concord with nearby major roads", sample_catalog(), persist_data_gaps=False)
    recipe["filter_plan"]["roads"] = {"candidate_fields": ["NameID", "ROUTE_NAME", "FUNC_CLASS"], "selected_field": "ROUTE_NAME"}
    preview = {
        "operational_layers": [
            {"layer_key": "roads", "title": "Road Centerlines", "category": "transportation", "visibility": True}
        ]
    }

    bounded = apply_aoi_to_preview_config(preview, recipe)
    roads = bounded["operational_layers"][0]

    assert roads["major_road_filter_applied"] is True
    assert roads["legend_label"] == "Major roads"
    assert roads["cartography_role"] == "major_roads"
    assert "UPPER(ROUTE_NAME)" in roads["definition_expression"]
    assert "NameID" not in roads["definition_expression"]


def test_aoi_floodplain_context_fallback_is_truthful_without_affected_overlay():
    recipe = build_recipe("show parcels in Concord that are in the 100-year floodplain", sample_catalog(), persist_data_gaps=False)
    preview = {
        "operational_layers": [
            {"layer_key": "tax_parcels", "title": "Tax Parcels", "category": "parcel", "visibility": True},
            {"layer_key": "flood_100", "title": "FloodPlain100year", "category": "flood", "visibility": True},
            {"layer_key": "municipal", "title": "Municipal District", "category": "jurisdiction", "visibility": True},
        ]
    }

    bounded = apply_aoi_to_preview_config(preview, recipe)
    parcels = next(layer for layer in bounded["operational_layers"] if layer["layer_key"] == "tax_parcels")

    assert parcels["visibility"] is False
    assert parcels["diagnostics_only"] is True
    assert "extraction is unavailable" in parcels["warning"]
    assert "affected parcels are shown" not in parcels["warning"]


def test_visual_complexity_score_tracks_visible_layer_stack():
    aoi = {"type": "municipality", "summary": "Concord boundary + 2 mile buffer"}
    layers = [
        {"map_role": "primary_polygon_highlight", "visibility": True, "opacity": 0.48, "clipped_to_aoi": True},
        {"map_role": "road_context", "visibility": True, "clipped_to_aoi": True},
        {"map_role": "parcel_outline", "visibility": False, "clipped_to_aoi": True},
    ]

    score = visual_complexity_score(layers, aoi)

    assert score["visible_layer_count"] == 2
    assert score["polygon_layer_count"] == 1
    assert score["line_layer_count"] == 1
    assert score["status"] in {"simple", "moderate"}


def test_out_of_scope_place_returns_unsupported_area_without_geocoder():
    plan = build_brain_plan("map parcels in Charlotte near flood zones")

    assert plan["request_type"] == "unsupported"
    assert plan["status"] == "unsupported_area"
    assert plan["geography"] == "Charlotte"
    assert any("Cabarrus County" in note for note in plan["safety_notes"])
