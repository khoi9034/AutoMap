from app.recipe_engine import build_recipe
from app.recipe_models import recipe_has_required_keys


def record(layer_key, layer_name, category, *, aliases=None, priority=1, status="active", service_name=None, layer_id=0, historical_year=None):
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
        "is_historical": historical_year is not None,
        "historical_year": historical_year,
        "record_count": 1,
    }


def sample_catalog():
    return [
        record("parcels", "Tax Parcels", "parcel", aliases=["parcel", "parcels", "tax parcel"], service_name="Tax_Parcels", layer_id=1),
        record("municipal", "MunicipalDistrict", "jurisdiction", aliases=["municipal", "municipality", "jurisdiction"], service_name="MunicipalDistrict"),
        record("flood100", "FloodPlain100year", "flood", aliases=["flood", "floodplain", "100 year flood"], service_name="Flood_Hazard_Areas", layer_id=2),
        record("elem", "Elementary School District", "schools", service_name="School_Districts"),
        record("middle", "Middle School District", "schools", service_name="School_Districts", layer_id=2),
        record("high", "High School District", "schools", service_name="School_Districts", layer_id=1),
        record("concord_zoning", "Concord Zoning", "zoning", service_name="Zoning_By_Municipalities"),
        record("county_zoning", "Cabarrus County Zoning", "zoning", service_name="Cabarrus_County_Zoning"),
        record("legacy_parcels_2014", "Tax Parcels 2014", "parcel", priority=2, status="legacy_historical", historical_year=2014),
        record("legacy_zoning_2014", "Zoning 2014", "zoning", priority=2, status="legacy_historical", historical_year=2014),
    ]


def test_build_recipe_returns_required_json_shape():
    recipe = build_recipe("Show parcels in Concord that are in the 100-year floodplain.", sample_catalog())

    assert recipe_has_required_keys(recipe)
    assert recipe["parsed_request"]["topic_details"]["flood_frequency"] == "100_year"
    assert {layer["layer_key"] for layer in recipe["selected_layers"]} >= {"parcels", "municipal", "flood100"}
    assert any(operation["operation"] == "intersect" for operation in recipe["spatial_operations"])


def test_build_recipe_school_request_selects_three_school_layers():
    recipe = build_recipe("Show school districts for parcels in Harrisburg.", sample_catalog())
    selected_keys = {layer["layer_key"] for layer in recipe["selected_layers"]}

    assert {"elem", "middle", "high", "parcels", "municipal"}.issubset(selected_keys)


def test_build_recipe_reports_missing_development_data():
    recipe = build_recipe("Map recent permits and planning cases near Kannapolis.", sample_catalog())

    assert recipe["needs_review"] is True
    assert "planning cases" in recipe["missing_data_needed"]
    assert "permits" in recipe["missing_data_needed"]


def test_build_recipe_historical_year_prefers_historical_layers():
    recipe = build_recipe("Show 2014 parcels and zoning.", sample_catalog())
    selected_keys = {layer["layer_key"] for layer in recipe["selected_layers"]}

    assert "legacy_parcels_2014" in selected_keys
    assert "legacy_zoning_2014" in selected_keys
    assert "parcels" not in selected_keys

