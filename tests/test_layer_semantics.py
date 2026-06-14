from app.layer_semantics import (
    build_layer_key,
    detect_historical_year,
    infer_layer_semantics,
    service_slug,
    slugify,
    sort_layer_candidates,
)


def test_slug_generation_for_service_and_layer_names():
    assert slugify("Flood Hazard Areas") == "flood_hazard_areas"
    assert service_slug("OpenData/School_Districts") == "school_districts"


def test_new_and_legacy_layer_key_generation():
    assert (
        build_layer_key("cabarrus_new_opendata", "Flood_Hazard_Areas", 2, "FloodPlain100year")
        == "cabarrus_new_flood_hazard_areas_2_floodplain100year"
    )
    assert (
        build_layer_key("cabarrus_legacy_opendata", "opendata", 42, "Addresses")
        == "cabarrus_legacy_opendata_42_addresses"
    )


def test_detect_historical_year_only_for_supported_range():
    assert detect_historical_year("Parcels 2008") == 2008
    assert detect_historical_year("Contours2017_4ft") is None


def test_categorization_and_aliases_for_flood_layers():
    semantics = infer_layer_semantics("Flood_Hazard_Areas", "FloodPlain100year")

    assert semantics["category"] == "flood"
    assert "floodplain" in semantics["aliases"]
    assert "100 year flood" in semantics["aliases"]


def test_search_preference_for_new_verified_layers_over_legacy():
    records = [
        {
            "layer_name": "Floodplain",
            "source_priority": 2,
            "source_status": "legacy",
            "is_verified": True,
            "is_historical": False,
        },
        {
            "layer_name": "FloodPlain100year",
            "source_priority": 1,
            "source_status": "active",
            "is_verified": True,
            "is_historical": False,
        },
    ]

    sorted_records = sort_layer_candidates(records)

    assert sorted_records[0]["source_status"] == "active"
    assert sorted_records[0]["source_priority"] == 1

