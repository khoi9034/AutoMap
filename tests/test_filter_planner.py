from app.filter_planner import build_filter_plan


def test_filter_planner_flags_uncertain_commercial_zoning_values():
    recipe = {
        "parsed_request": {
            "geography_terms": [{"name": "Concord", "type": "municipality"}],
            "time_references": ["current"],
            "topic_details": {"zoning_modifiers": ["commercial"]},
        },
        "selected_layers": [
            {
                "layer_key": "concord_zoning",
                "layer_name": "Concord Zoning",
                "category": "zoning",
                "role": "constraint_overlay",
            }
        ],
    }
    catalog = [
        {
            "layer_key": "concord_zoning",
            "layer_url": "https://example.com/MapServer/0",
            "fields": [
                {"name": "ZONE_CODE", "type": "esriFieldTypeString", "alias": "Zoning Code"}
            ],
        }
    ]

    plan = build_filter_plan(recipe, catalog_records=catalog)

    assert plan["concord_zoning"]["selected_field"] == "ZONE_CODE"
    assert plan["concord_zoning"]["needs_review"] is True
    assert "commercial" in plan["concord_zoning"]["review_reason"].lower()


def test_filter_planner_does_not_fake_floodplain_attribute_filter():
    recipe = {
        "parsed_request": {
            "geography_terms": [],
            "time_references": ["current"],
            "topic_details": {"flood_frequency": "100_year"},
        },
        "selected_layers": [
            {
                "layer_key": "flood100",
                "layer_name": "FloodPlain100year",
                "category": "flood",
                "role": "constraint_overlay",
            }
        ],
    }

    plan = build_filter_plan(recipe, catalog_records=[])

    assert plan["flood100"]["selected_field"] is None
    assert plan["flood100"]["draft_where_clause"] is None
    assert plan["flood100"]["needs_review"] is False
