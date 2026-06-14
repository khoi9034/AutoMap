from app.prompt_parser import parse_prompt


def test_parse_prompt_extracts_geography_topics_and_intent():
    result = parse_prompt("Show parcels in Concord that are in the 100-year floodplain.")

    assert result["raw_prompt"] == "Show parcels in Concord that are in the 100-year floodplain."
    assert {"name": "Concord", "type": "municipality"} in result["geography_terms"]
    assert "parcel" in result["topics"]
    assert "flood" in result["topics"]
    assert result["topic_details"]["flood_frequency"] == "100_year"
    assert result["analysis_intent"] == "overlay_intersection"


def test_parse_prompt_extracts_historical_year():
    result = parse_prompt("Show 2014 parcels and zoning.")

    assert result["historical_year"] == 2014
    assert "historical" in result["time_references"]
    assert "parcel" in result["topics"]
    assert "zoning" in result["topics"]


def test_parse_prompt_extracts_recent_development_terms():
    result = parse_prompt("Map recent permits and planning cases near Kannapolis.")

    assert {"name": "Kannapolis", "type": "municipality"} in result["geography_terms"]
    assert "recent" in result["time_references"]
    assert "development" in result["topics"]
    assert result["topic_details"]["development_terms"] == ["permits", "planning_cases"]
    assert result["analysis_intent"] == "proximity"

