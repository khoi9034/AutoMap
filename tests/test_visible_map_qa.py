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


def test_brain_visible_map_qa_counts_affected_parcel_overlay():
    recipe = {"request_plan": {"request_type": "floodplain_screening", "parameters": {"geography": "Concord"}}}
    preview = {
        "aoi": {
            "type": "municipality",
            "summary": "Concord boundary",
            "extent": {"xmin": -80.7, "ymin": 35.3, "xmax": -80.5, "ymax": 35.5, "spatialReference": {"wkid": 4326}},
        },
        "context_layers": [],
        "derived_overlays": [
            {
                "id": "affected",
                "title": "Parcels in 100-year floodplain",
                "role": "affected_parcels",
                "geometry_role": "affected_parcels",
                "feature_count": 12,
                "visible": True,
                "extent": {"xmin": -80.61, "ymin": 35.36, "xmax": -80.55, "ymax": 35.42, "spatialReference": {"wkid": 4326}},
                "local_output": True,
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe)

    assert qa["qa_status"] == "visible"
    assert qa["visible_feature_total"] == 12
    row = qa["visible_feature_summary"][0]
    assert row["expected_role"] == "affected_parcels"
    assert row["feature_count"] == 12
    assert row["clipped_to_aoi"] is True


def test_brain_visible_map_qa_flags_dense_affected_parcels_without_display_mode():
    recipe = {"request_plan": {"request_type": "floodplain_screening", "parameters": {"geography": "Concord"}}}
    preview = {
        "derived_overlays": [
            {
                "id": "affected",
                "title": "Parcels in 100-year floodplain",
                "role": "affected_parcels",
                "geometry_role": "affected_parcels",
                "feature_count": 150,
                "visible": True,
                "extent": {"xmin": -80.61, "ymin": 35.36, "xmax": -80.55, "ymax": 35.42, "spatialReference": {"wkid": 4326}},
                "local_output": True,
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe)

    assert any("generalized display mode" in warning for warning in qa["warnings"])
    assert qa["visible_feature_summary"][0]["display_mode"] is None


def test_brain_visible_map_qa_uses_truthful_floodplain_fallback_warning():
    class FakeClient:
        def query_count(self, *_args, **_kwargs):
            return {"count": 0}

        def query_extent(self, *_args, **_kwargs):
            return {"extent": None}

    recipe = {"request_plan": {"request_type": "floodplain_screening", "parameters": {"geography": "Concord"}}}
    preview = {
        "context_layers": [
            {
                "layer_key": "flood_100",
                "title": "100-year floodplain",
                "category": "flood",
                "url": "https://example.test/flood/0",
                "visibility": True,
                "drawing_info": {"renderer": {"symbol": {"type": "esriSFS", "color": [14, 165, 233, 112], "outline": {"color": [2, 132, 199, 235], "width": 1.8}}}},
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe, query_client=FakeClient())

    assert qa["qa_status"] == "no_visible_features"
    assert any("affected parcel extraction unavailable" in warning for warning in qa["warnings"])
    assert qa["visible_feature_summary"][0]["legend_label"] == "100-year floodplain"
    assert qa["visible_feature_summary"][0]["drawing_info"]["renderer"]["symbol"]["color"] == [14, 165, 233, 112]


def test_brain_visible_map_qa_flags_filled_boundary_renderer():
    class FakeClient:
        def query_count(self, *_args, **_kwargs):
            return {"count": 1}

        def query_extent(self, *_args, **_kwargs):
            return {"extent": {"xmin": -80.6, "ymin": 35.3, "xmax": -80.5, "ymax": 35.4, "spatialReference": {"wkid": 4326}}}

    recipe = {"request_plan": {"request_type": "floodplain_screening", "parameters": {"geography": "Concord"}}}
    preview = {
        "context_layers": [
            {
                "layer_key": "municipal",
                "title": "Concord boundary",
                "category": "jurisdiction",
                "url": "https://example.test/municipal/0",
                "visibility": True,
                "drawing_info": {"renderer": {"symbol": {"type": "esriSFS", "color": [237, 212, 252, 255]}}},
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe, query_client=FakeClient())

    assert any("Boundary layer fill is too opaque" in warning for warning in qa["warnings"])


def test_brain_visible_map_qa_flags_boundary_below_primary_polygons():
    class FakeClient:
        def query_count(self, *_args, **_kwargs):
            return {"count": 1}

        def query_extent(self, *_args, **_kwargs):
            return {"extent": {"xmin": -80.6, "ymin": 35.3, "xmax": -80.5, "ymax": 35.4, "spatialReference": {"wkid": 4326}}}

    recipe = {"request_plan": {"request_type": "floodplain_screening", "parameters": {"geography": "Concord"}}}
    preview = {
        "context_layers": [
            {
                "layer_key": "municipal",
                "title": "Concord boundary",
                "category": "jurisdiction",
                "url": "https://example.test/municipal/0",
                "visibility": True,
                "draw_order": 10,
                "drawing_info": {"renderer": {"symbol": {"type": "esriSFS", "color": [255, 255, 255, 0], "outline": {"width": 3.2}}}},
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe, query_client=FakeClient())

    assert any("Boundary draw order is below primary polygon results" in warning for warning in qa["warnings"])
    assert qa["visual_quality"]["boundary_visible"] is False


def test_brain_visible_map_qa_flags_weak_floodplain_symbol():
    class FakeClient:
        def query_count(self, *_args, **_kwargs):
            return {"count": 1}

        def query_extent(self, *_args, **_kwargs):
            return {"extent": {"xmin": -80.6, "ymin": 35.3, "xmax": -80.5, "ymax": 35.4, "spatialReference": {"wkid": 4326}}}

    recipe = {"request_plan": {"request_type": "floodplain_screening", "parameters": {"geography": "Concord"}}}
    preview = {
        "context_layers": [
            {
                "layer_key": "flood_100",
                "title": "100-year floodplain",
                "category": "flood",
                "url": "https://example.test/flood/0",
                "visibility": True,
                "drawing_info": {"renderer": {"symbol": {"type": "esriSFS", "color": [56, 189, 248, 40], "outline": {"width": 0.5}}}},
            }
        ],
    }

    qa = run_visible_map_qa(preview, recipe, query_client=FakeClient())

    assert any("Floodplain symbol is too weak" in warning for warning in qa["warnings"])
