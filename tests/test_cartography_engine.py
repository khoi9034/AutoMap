from app.automap_brain.cartography_engine import (
    cartography_for_role,
    context_draw_rank,
    plain_legend_label,
    style_context_layer,
    universal_layer_role,
)


def test_zoning_cartography_uses_visible_commercial_highlight():
    recipe = {
        "user_intent": "show commercial zoning around Concord with nearby major roads",
        "request_plan": {"request_type": "zoning_context", "zoning_category": "commercial"},
        "parsed_request": {"topic_details": {"zoning_modifiers": ["commercial"]}},
    }
    layer = {
        "layer_key": "zoning",
        "title": "Cabarrus County Zoning",
        "category": "zoning",
        "definition_expression": "ZONING IN ('GC')",
    }

    styled = style_context_layer(layer, recipe)

    assert styled["title"] == "Commercial zoning"
    assert styled["legend_label"] == "Commercial zoning"
    assert styled["cartography_role"] == "commercial_zoning"
    assert styled["map_role"] == "primary_polygon_highlight"
    assert styled["layer_role"] == "primary_result"
    assert 0.35 <= styled["opacity"] <= 0.55
    assert styled["drawing_info"]["renderer"]["symbol"]["outline"]["width"] >= 1.2


def test_layer_order_keeps_roads_above_polygons():
    zoning = {"cartography_role": "commercial_zoning", "map_role": "primary_polygon_highlight"}
    roads = {"cartography_role": "major_roads", "map_role": "major_road"}
    boundary = {"cartography_role": "boundary", "map_role": "boundary_outline"}

    assert context_draw_rank(boundary) < context_draw_rank(zoning) < context_draw_rank(roads)


def test_plain_legend_labels_are_user_facing():
    assert plain_legend_label({"map_role": "road_context"}) == "Road context"
    assert plain_legend_label({"map_role": "floodplain_overlay"}) == "100-year floodplain"
    assert plain_legend_label({"map_role": "primary_polygon_highlight"}) == "Commercial zoning"
    assert plain_legend_label({"map_role": "affected_parcels"}) == "Parcels in 100-year floodplain"


def test_route_and_fallback_symbols_are_distinct_roles():
    route = cartography_for_role("roads", major_requested=True)
    muted = cartography_for_role("zoning")

    assert route["cartography_role"] == "major_roads"
    assert route["map_role"] == "major_road"
    assert route["drawing_info"]["renderer"]["symbol"]["width"] > 2
    assert muted["opacity"] < 0.3


def test_floodplain_screening_cartography_highlights_affected_parcels():
    affected = cartography_for_role("affected_parcels")
    flood = cartography_for_role("flood")
    boundary = cartography_for_role("boundary")

    assert affected["cartography_role"] == "affected_parcels"
    assert affected["map_role"] == "affected_parcels"
    assert affected["legend_label"] == "Parcels in 100-year floodplain"
    assert affected["opacity"] > flood["opacity"]
    assert flood["drawing_info"]["renderer"]["symbol"]["color"] == [14, 165, 233, 112]
    assert flood["drawing_info"]["renderer"]["symbol"]["outline"]["width"] >= 1.5
    assert boundary["drawing_info"]["renderer"]["symbol"]["color"][3] == 0
    assert boundary["drawing_info"]["renderer"]["symbol"]["outline"]["width"] >= 2.4
    assert boundary["min_stroke_width"] >= 2.4
    assert affected["drawing_info"]["renderer"]["symbol"]["outline"]["width"] > flood["drawing_info"]["renderer"]["symbol"]["outline"]["width"]
    assert context_draw_rank({"map_role": "floodplain_overlay"}) < context_draw_rank({"map_role": "affected_parcels"})


def test_universal_roles_group_primary_context_and_diagnostics():
    assert universal_layer_role({"map_role": "affected_parcels"}) == "primary_result"
    assert universal_layer_role({"map_role": "floodplain_overlay"}) == "supporting_context"
    assert universal_layer_role({"map_role": "boundary_outline"}) == "boundary_context"
    assert universal_layer_role({"map_role": "diagnostics_only"}) == "diagnostic_hidden"
