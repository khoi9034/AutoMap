from app import arcgis_service_search as search
from app import source_discovery


def test_discover_arcgis_services_parses_root_and_folder(monkeypatch):
    payloads = {
        "https://example.test/arcgis/rest/services": {
            "folders": ["Transportation"],
            "services": [{"name": "Permits", "type": "MapServer"}],
        },
        "https://example.test/arcgis/rest/services/Transportation": {
            "folders": [],
            "services": [{"name": "Transportation/AADT", "type": "FeatureServer"}],
        },
    }
    monkeypatch.setattr(search, "fetch_json", lambda url: payloads[url.rstrip("/")])

    services = search.discover_arcgis_services("https://example.test/arcgis/rest/services")

    urls = {item["service_url"] for item in services}
    assert "https://example.test/arcgis/rest/services/Permits/MapServer" in urls
    assert "https://example.test/arcgis/rest/services/Transportation/AADT/FeatureServer" in urls


def test_keyword_search_finds_mocked_services(monkeypatch):
    monkeypatch.setattr(
        search,
        "discover_arcgis_services",
        lambda root_url: [
            {"service_name": "OpenData/Addresses", "service_url": f"{root_url}/OpenData/Addresses/MapServer"},
            {"service_name": "Traffic/AADT", "service_url": f"{root_url}/Traffic/AADT/FeatureServer"},
        ],
    )

    matches = search.search_services_by_keyword("https://example.test/rest/services", ["aadt", "permits"])

    assert len(matches) == 1
    assert matches[0]["service_name"] == "Traffic/AADT"
    assert matches[0]["matched_keywords"] == ["aadt"]


def test_score_discovered_layer_for_aadt_and_stip():
    aadt = {
        "is_verified": True,
        "layer_url": "https://example.test/AADT/FeatureServer/0",
        "layer_metadata": {"layer_name": "AADT Traffic Counts", "fields": [{"name": "AADT"}]},
    }
    stip = {
        "is_verified": True,
        "layer_url": "https://example.test/STIP/FeatureServer/0",
        "layer_metadata": {"layer_name": "STIP Projects", "fields": [{"name": "TIP_ID"}]},
    }

    assert search.score_discovered_layer_for_gap(aadt, "traffic_counts")["score"] >= 60
    assert search.score_discovered_layer_for_gap(stip, "stip_projects")["score"] >= 60


def test_discovered_layer_to_source_record_labels_proxy_and_transportation():
    plan_layer = {
        "layer_url": "https://example.test/PlanReviews/FeatureServer/0",
        "layer_name": "Accela Plan Reviews",
        "layer_metadata": {"layer_name": "Accela Plan Reviews"},
    }
    aadt_layer = {
        "layer_url": "https://example.test/AADT/FeatureServer/0",
        "layer_name": "AADT Traffic Counts",
        "layer_metadata": {"layer_name": "AADT Traffic Counts"},
    }

    plan_record = source_discovery.discovered_layer_to_source_record(
        plan_layer,
        {"gap_key": "current_development_pipeline", "score": 80, "matched_terms": ["accela", "plan review"]},
    )
    aadt_record = source_discovery.discovered_layer_to_source_record(
        aadt_layer,
        {"gap_key": "traffic_counts", "score": 95, "matched_terms": ["aadt"]},
    )

    assert plan_record["source_status"] == "proxy"
    assert "development_pipeline_proxy" in plan_record["categories"]
    assert aadt_record["source_status"] == "reference"
    assert "aadt" in aadt_record["categories"]


def test_verify_external_source_upserts_registry_and_catalog(monkeypatch):
    source = {
        "source_key": "verified_aadt",
        "source_name": "AADT Traffic Counts",
        "source_type": "arcgis_layer",
        "layer_url": "https://example.test/AADT/FeatureServer/0",
        "base_url": "https://example.test/AADT/FeatureServer",
        "approval_status": "candidate",
        "source_status": "reference",
        "categories": ["aadt", "traffic"],
        "intended_gaps": ["traffic_counts"],
        "inspected_metadata": {},
    }
    inspected = {**source, "inspected_metadata": {"inspection_status": "inspected", "is_verified": True}}
    calls = []

    monkeypatch.setattr(source_discovery, "get_external_source", lambda source_key, schema_name="automap": source)
    monkeypatch.setattr(source_discovery, "inspect_external_source", lambda record: inspected)
    monkeypatch.setattr(
        source_discovery,
        "update_external_source_metadata",
        lambda source_key, metadata, schema_name="automap": {**source, "inspected_metadata": metadata},
    )
    monkeypatch.setattr(
        source_discovery,
        "upsert_external_source_to_catalog",
        lambda source_key, schema_name="automap": calls.append(source_key) or 1,
    )

    result = source_discovery.verify_external_source("verified_aadt")

    assert result["catalog_upserts"] == 1
    assert calls == ["verified_aadt"]
    assert result["downloaded_geometry"] is False


def test_proxy_partial_support_does_not_resolve_official_permit(monkeypatch):
    source = {
        "source_key": "plan_review_proxy",
        "source_name": "Accela Plan Review",
        "source_type": "arcgis_layer",
        "approval_status": "candidate",
        "source_status": "proxy",
        "categories": ["plan_review", "development_activity_proxy"],
        "intended_gaps": ["current_development_pipeline", "current_permits"],
        "inspected_metadata": {"inspection_status": "inspected", "is_verified": True},
        "is_active": True,
    }

    from app import data_gap_resolver

    monkeypatch.setattr(data_gap_resolver, "list_external_sources", lambda schema_name="automap": [source])

    permits = data_gap_resolver.evaluate_gap_resolution("current_permits")
    pipeline = data_gap_resolver.evaluate_gap_resolution("current_development_pipeline")

    assert permits["status"] == "needs_review"
    assert permits["authoritative_sources"] == []
    assert pipeline["status"] == "partially_supported"
    assert pipeline["partial_sources"][0]["source_key"] == "plan_review_proxy"
