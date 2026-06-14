from urllib.parse import parse_qs, urlparse

from app.field_profiler import build_sample_query_url, infer_field_roles


def test_infer_field_roles_detects_date_zoning_and_geography_fields():
    profiles = infer_field_roles(
        [
            {"name": "ISSUE_DATE", "type": "esriFieldTypeDate", "alias": "Issue Date"},
            {"name": "ZONE_CODE", "type": "esriFieldTypeString", "alias": "Zoning Code"},
            {"name": "MUNICIPALITY", "type": "esriFieldTypeString", "alias": "City"},
        ]
    )

    by_name = {profile["field_name"]: profile for profile in profiles}

    assert by_name["ISSUE_DATE"]["is_date_candidate"] is True
    assert by_name["ZONE_CODE"]["is_zoning_candidate"] is True
    assert by_name["MUNICIPALITY"]["is_geography_candidate"] is True


def test_sample_query_url_always_uses_return_geometry_false():
    url = build_sample_query_url("https://example.com/MapServer/0", "ZONE_CODE", max_values=25)
    query = parse_qs(urlparse(url).query)

    assert query["returnGeometry"] == ["false"]
    assert query["returnDistinctValues"] == ["true"]
    assert query["outFields"] == ["ZONE_CODE"]
    assert query["resultRecordCount"] == ["25"]
