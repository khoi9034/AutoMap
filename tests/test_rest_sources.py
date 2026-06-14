import pytest

from app.rest_sources import load_rest_sources, validate_rest_sources


def test_rest_sources_seed_file_is_valid():
    sources = load_rest_sources()

    assert [source["source_key"] for source in sources] == [
        "cabarrus_new_opendata",
        "cabarrus_legacy_opendata",
    ]
    assert sources[0]["source_type"] == "arcgis_folder"
    assert sources[1]["source_type"] == "arcgis_mapserver"


def test_rest_source_validation_rejects_duplicate_keys():
    sources = [
        {
            "source_key": "duplicate",
            "source_type": "arcgis_folder",
            "base_url": "https://example.com/arcgis/rest/services/OpenData",
            "priority": 1,
            "status": "active",
        },
        {
            "source_key": "duplicate",
            "source_type": "arcgis_mapserver",
            "base_url": "https://example.com/arcgis/rest/services/opendata/MapServer",
            "priority": 2,
            "status": "legacy",
        },
    ]

    with pytest.raises(ValueError, match="Duplicate REST source_key"):
        validate_rest_sources(sources)

