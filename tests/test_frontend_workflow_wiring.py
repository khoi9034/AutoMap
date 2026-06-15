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
