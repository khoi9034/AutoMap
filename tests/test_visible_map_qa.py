from app.automap_brain.visible_map_qa import run_visible_map_qa


def test_brain_visible_map_qa_adds_status_metadata():
    class FakeClient:
        def query_count(self, *_args, **_kwargs):
            return {"count": 3}

        def query_extent(self, *_args, **_kwargs):
            return {"extent": {"xmin": -80.6, "ymin": 35.4, "xmax": -80.58, "ymax": 35.42, "spatialReference": {"wkid": 4326}}}

    recipe = {"request_plan": {"request_type": "zoning_context", "parameters": {"geography": "Concord"}}}
    preview = {
        "initial_extent": {"xmin": -80.72, "ymin": 35.30, "xmax": -80.46, "ymax": 35.49, "spatialReference": {"wkid": 4326}},
        "context_layers": [
            {
                "layer_key": "zoning",
                "title": "Commercial zoning",
                "category": "zoning",
                "url": "https://example.test/zoning/0",
                "visibility": True,
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe, query_client=FakeClient())

    assert qa["brain_version"] == "automap_brain_v2"
    assert qa["qa_status"] == "visible"
    assert qa["visible_feature_total"] == 3


def test_brain_visible_map_qa_flags_empty_preview():
    class FakeClient:
        def query_count(self, *_args, **_kwargs):
            return {"count": 0}

        def query_extent(self, *_args, **_kwargs):
            return {"extent": None}

    recipe = {"request_plan": {"request_type": "zoning_context", "parameters": {"geography": "Concord"}}}
    preview = {
        "context_layers": [
            {
                "layer_key": "zoning",
                "title": "Commercial zoning",
                "category": "zoning",
                "url": "https://example.test/zoning/0",
                "visibility": True,
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe, query_client=FakeClient())

    assert qa["qa_status"] == "no_visible_features"
    assert qa["visible_feature_total"] == 0
    assert any("filter returned no visible features" in warning for warning in qa["warnings"])


def test_brain_visible_map_qa_preserves_aoi_clipping_metadata():
    class FakeClient:
        def query_count(self, *_args, **_kwargs):
            return {"count": 8}

        def query_extent(self, *_args, **_kwargs):
            return {"extent": {"xmin": -80.61, "ymin": 35.36, "xmax": -80.55, "ymax": 35.42, "spatialReference": {"wkid": 4326}}}

    recipe = {"user_intent": "show commercial zoning around Concord with nearby major roads", "request_plan": {"request_type": "zoning_context", "parameters": {"geography": "Concord"}}}
    preview = {
        "aoi": {
            "type": "municipality",
            "geography_name": "Concord",
            "summary": "Concord boundary + 2 mile buffer",
            "extent": {"xmin": -80.75, "ymin": 35.27, "xmax": -80.43, "ymax": 35.52, "spatialReference": {"wkid": 4326}},
        },
        "context_layers": [
            {
                "layer_key": "roads",
                "title": "Road context",
                "category": "transportation",
                "url": "https://example.test/roads/0",
                "visibility": True,
                "clipped_to_aoi": True,
                "aoi_filter_applied": True,
                "aoi_summary": "Concord boundary + 2 mile buffer",
                "map_role": "road_context",
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe, query_client=FakeClient())

    row = qa["visible_feature_summary"][0]
    assert row["clipped_to_aoi"] is True
    assert row["aoi_filter_applied"] is True
    assert row["aoi_summary"] == "Concord boundary + 2 mile buffer"
    assert row["map_role"] == "road_context"
