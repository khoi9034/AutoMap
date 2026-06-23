from app.map_title_generator import generate_map_title, generate_proximity_title, map_layout_subtitle
from app.recipe_engine import build_recipe
from tests.test_request_intelligence import sample_catalog


def test_proximity_title_is_concise_and_request_specific():
    title = generate_proximity_title(
        {
            "status": "ok",
            "origin_input": "793 bartram ave",
            "target_type": "nearest_fire_station",
        }
    )

    assert title == "Nearest Fire Station from 793 Bartram Ave"
    assert len(title) < 72


def test_generic_address_layer_title_is_not_used_for_proximity():
    title = generate_map_title(
        "make a map of my address 793 bartram ave and include nearest line to the nearest fire station",
        recipe={"map_title": "Addresses"},
        proximity_result={"status": "ok", "origin_input": "793 bartram ave", "target_type": "nearest_fire_station"},
    )

    assert title == "Nearest Fire Station from 793 Bartram Ave"


def test_prompt_titles_for_common_composer_maps():
    assert generate_map_title("Show parcels in Concord that are in the 100-year floodplain.") == "Parcels in Concord Floodplain"
    assert generate_map_title("Show commercial zoning around Concord.") == "Commercial Zoning Around Concord"
    assert generate_map_title("Show school districts for parcels in Harrisburg.") == "School Districts for Harrisburg Parcels"


def test_commercial_zoning_title_uses_normalized_typo_prompt():
    prompt = "show commercial zonign aorund concord with bearny major roads"
    recipe = build_recipe(prompt, sample_catalog(), persist_data_gaps=False)

    assert generate_map_title(prompt, recipe=recipe) == "Commercial Zoning Around Concord"


def test_layout_subtitle_stays_short():
    assert map_layout_subtitle({"route_mode": "road_network"}) == "Road-following draft route. Not official navigation."
    assert map_layout_subtitle({"route_mode": "straight_line_fallback"}) == "Straight-line fallback. Road route unavailable."
