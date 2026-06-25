from app.automap_brain.benchmark import run_benchmark
from app.automap_brain.fallback_planner import plan_fallbacks
from app.automap_brain.intent_classifier import classify_intent
from app.automap_brain.ontology import LAYER_ROLES, REQUEST_TYPES, SPATIAL_RELATIONSHIPS, kernel_ontology
from app.automap_brain.parameter_extractor import extract_parameters
from app.automap_brain.spatial_operation_planner import plan_spatial_operation


def _operation(prompt: str):
    intent = classify_intent(prompt)
    params = extract_parameters(prompt, request_plan=intent["request_plan"])
    return intent, params, plan_spatial_operation(intent["request_plan"], params)


def test_kernel_ontology_defines_request_operations_and_roles():
    ontology = kernel_ontology()

    assert "floodplain_screening" in REQUEST_TYPES
    assert "unsupported_area" in REQUEST_TYPES
    assert "closest_by_road" in SPATIAL_RELATIONSHIPS
    assert "affected_parcels" in LAYER_ROLES
    assert ontology["scope"] == "Cabarrus County, NC"
    assert "parcels" in ontology["domains"]


def test_floodplain_prompt_plans_intersection_result_not_raw_layers():
    intent, params, operation = _operation("show parcels in Concord that are in the 100-year floodplain")

    assert intent["request_type"] == "floodplain_screening"
    assert params["geography"] == "Concord"
    assert operation["operation"] == "intersects"
    assert operation["result_layer_role"] == "affected_parcels"
    assert "affected_parcels" in operation["layer_roles"]
    assert "floodplain_overlay" in operation["layer_roles"]


def test_zoning_context_prompt_plans_aoi_clipped_context():
    intent, _params, operation = _operation("show commercial zoning around Concord with nearby major roads")

    assert intent["request_type"] == "zoning_context"
    assert operation["operation"] == "clipped_to_aoi"
    assert operation["result_layer_role"] == "primary_polygon_highlight"
    assert "major_road" in operation["layer_roles"]
    assert operation["clip_to_aoi"] is True


def test_proximity_prompt_prefers_closest_by_road():
    intent, _params, operation = _operation("closest fire station to 793 bartram ave")

    assert intent["request_type"] == "proximity"
    assert operation["operation"] == "closest_by_road"
    assert operation["method"] == "road_network"
    assert {"origin_marker", "target_marker", "route_line"}.issubset(set(operation["layer_roles"]))


def test_unsupported_area_is_explicit_and_safe():
    intent = classify_intent("show parcels near 123 Main St Charlotte NC")

    assert intent["request_type"] == "unsupported_area"
    assert intent["geography"] == "Charlotte"
    assert any("Cabarrus County" in note for note in intent["safety_notes"])


def test_fallback_planner_explains_context_only_floodplain_fallback():
    intent, _params, operation = _operation("show parcels in Concord that are in the 100-year floodplain")
    fallback = plan_fallbacks(intent["request_plan"], operation)

    assert any(item["action"] == "show_floodplain_context_only" for item in fallback["fallback_options"])
    assert fallback["refinement_guidance"]


def test_brain_benchmark_runner_reports_score_summary():
    report = run_benchmark()

    assert report["total"] >= 60
    assert report["passed"] > 0
    assert "failed_intent_classifications" in report
    assert "failed_spatial_operations" in report
    assert "failed_layer_roles" in report
