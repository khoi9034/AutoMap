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
