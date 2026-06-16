from app.layer_matcher import match_layers
from app.prompt_parser import parse_prompt


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
    }


def test_match_layers_prefers_current_new_layer_over_legacy():
    catalog = [
        catalog_record("legacy_parcels", "Tax Parcels", "parcel", source_priority=2, source_status="legacy"),
        catalog_record("new_parcels", "Tax Parcels", "parcel"),
    ]

    result = match_layers(parse_prompt("Show parcels."), catalog)

    assert result["selected_layers"][0]["layer_key"] == "new_parcels"


def test_match_layers_uses_historical_layers_when_year_requested():
    catalog = [
        catalog_record("new_parcels", "Tax Parcels", "parcel"),
        catalog_record(
            "legacy_parcels_2014",
            "Tax Parcels 2014",
            "parcel",
            source_priority=2,
            source_status="legacy_historical",
            is_historical=True,
            historical_year=2014,
        ),
    ]

    result = match_layers(parse_prompt("Show 2014 parcels."), catalog)

    assert result["selected_layers"][0]["layer_key"] == "legacy_parcels_2014"


def test_match_layers_selects_100_year_floodplain_when_requested():
    catalog = [
        catalog_record("floodway", "FloodWay", "flood", service_name="Flood_Hazard_Areas"),
        catalog_record("flood100", "FloodPlain100year", "flood", service_name="Flood_Hazard_Areas"),
        catalog_record("flood500", "FloodPlain500year", "flood", service_name="Flood_Hazard_Areas"),
    ]

    result = match_layers(parse_prompt("Show parcels in the 100-year floodplain."), catalog)

    assert result["selected_layers"][0]["layer_key"] == "flood100"


def test_match_layers_selects_school_district_sublayers():
    catalog = [
        catalog_record("elem", "Elementary School District", "schools"),
        catalog_record("middle", "Middle School District", "schools"),
        catalog_record("high", "High School District", "schools"),
    ]

    result = match_layers(parse_prompt("Show school districts."), catalog)
    selected_keys = {layer["layer_key"] for layer in result["selected_layers"]}

    assert selected_keys == {"elem", "middle", "high"}


def test_match_layers_reports_missing_requested_data():
    result = match_layers(parse_prompt("Map recent permits and planning cases near Kannapolis."), [])

    assert "planning cases" in result["missing_data_needed"]
    assert "permits" in result["missing_data_needed"]
    assert "development" not in result["missing_data_needed"]
