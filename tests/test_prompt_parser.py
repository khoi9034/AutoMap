from app.prompt_parser import parse_prompt


def test_parse_prompt_returns_raw_prompt_and_terms():
    result = parse_prompt("Show parcels with zoning.")

    assert result["raw_prompt"] == "Show parcels with zoning."
    assert result["terms"] == ["show", "parcels", "with", "zoning"]

