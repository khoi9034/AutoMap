from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def read(path: str) -> str:
    return (FRONTEND / path).read_text(encoding="utf-8")


def test_workflow_store_has_persistent_state_and_step_logic():
    source = read("lib/workflow-store.ts")

    assert "WORKFLOW_STORAGE_KEY" in source
    assert "loadWorkflowState" in source
    assert "saveWorkflowState" in source
    assert "mergeWorkflowState" in source
    assert "getWorkflowStepStates" in source
    assert "review_packet" in source
    assert "publish" in source
    assert "PROTECTED_MARKERS" in source
    assert "database_url" in source


def test_stepper_and_context_panel_are_present():
    stepper = read("components/workflow-stepper.tsx")
    context = read("components/workflow-context-panel.tsx")
    layout = read("app/layout.tsx")

    assert "getWorkflowStepStates" in stepper
    assert "workflow-step-" in stepper
    assert "WorkflowContextPanel" in context
    assert "clearWorkflowState" in context
    assert "WorkflowContextPanel" in layout


def test_packet_picker_supports_resume_workflows():
    source = read("components/packet-picker.tsx")

    assert "packetType" in source
    assert "review_packets" in source
    assert "adjusted_packets" in source
    assert "approved_packets" in source
    assert "listPackets" in source


def test_map_request_and_recipe_review_store_workflow_state():
    map_request = read("components/map-request-client.tsx")
    recipe_review = read("components/recipe-review-client.tsx")

    assert "makeRecipe" in map_request
    assert "mergeWorkflowState" in map_request
    assert "workflowMissingDataFromRecipe" in map_request
    assert "Continue to Recipe Review" in map_request
    assert "makeReviewPacket" in recipe_review
    assert "selectedPacketId" in recipe_review
    assert "Create Adjustment Template" in recipe_review


def test_publish_center_is_dry_run_only():
    source = read("components/publish-center-client.tsx")

    assert "dryRunPublish" in source
    assert "portalSmokeTestDryRun" in source
    assert "Real publish remains CLI-only" in source
    assert "confirm-publish" not in source.lower()
    assert "publish-draft-webmap" not in source.lower()


def test_v16_dashboard_has_operations_and_safety_cards():
    source = read("app/dashboard/page.tsx")

    assert "dashboard-hero" in source
    assert "Demo scenarios" in source
    assert "Latest workflow activity" in source
    assert "Latest packets" in source
    assert "Safety status" in source
    assert "Frontend 3010" in source
    assert "Backend/API 8010" in source
    assert "CFS ports 3000 and 8000 are reserved" in source


def test_map_preview_uses_safe_frontend_preview_components():
    preview = read("components/map-preview-client.tsx")
    shell = read("components/arcgis-map-preview.tsx")

    assert "ArcGISMapPreview" in preview
    assert "No ArcGIS login" in preview
    assert "getPreviewConfig" in shell
    assert "LayerPanel" in shell
    assert "WarningPanel" in shell
    assert "No ArcGIS login" in shell
    assert "No publish" in shell
    assert "iframe" in shell
    assert "confirm-publish" not in shell.lower()
    assert "publish-draft-webmap" not in shell.lower()


def test_layer_panel_renders_review_metadata_without_assuming_layer_zero():
    source = read("components/layer-panel.tsx")

    assert "visibility" in source
    assert "opacity" in source
    assert "definition_expression" in source
    assert "confidence_score" in source
    assert "review_warnings" in source
    assert "service_url" in source
    assert "layer_id" in source
    assert '"/0"' not in source


def test_warning_panel_groups_human_review_warnings():
    source = read("components/warning-panel.tsx")

    assert "missing_data" in source
    assert "filter_review" in source
    assert "layer_selection" in source
    assert "publishing_blockers" in source
    assert "historical_data" in source
    assert "safety_warnings" in source


def test_data_gaps_page_explains_missing_sources_not_failures():
    source = read("app/data-gaps/page.tsx")

    assert "These are not AutoMap failures" in source
    assert "current_permits" in source
    assert "current_planning_cases" in source
    assert "current_development_pipeline" in source


def test_api_client_has_timeout_and_sanitized_fallback_version():
    source = read("lib/api.ts")

    assert "Backend API request timed out" in source
    assert "http://127.0.0.1:8010" in source
    assert 'version: "1.6.0"' in source
    assert "redactProtected" in source
