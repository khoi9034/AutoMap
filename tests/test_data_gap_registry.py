from app.data_gap_registry import data_gap_records_from_recipe


def test_data_gap_registry_maps_missing_permits_and_planning_cases():
    recipe = {
        "user_intent": "Map recent permits and planning cases near Kannapolis.",
        "missing_data_needed": ["permits", "planning cases"],
    }

    gaps = data_gap_records_from_recipe(recipe)
    gap_keys = {gap["gap_key"] for gap in gaps}

    assert "current_permits" in gap_keys
    assert "current_planning_cases" in gap_keys
