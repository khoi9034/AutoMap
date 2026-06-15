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
    intelligence_panel = read("components/request-intelligence-panel.tsx")

    assert "makeRecipe" in map_request
    assert "mergeWorkflowState" in map_request
    assert "workflowMissingDataFromRecipe" in map_request
    assert "Continue to Recipe Review" in map_request
    assert "RequestIntelligencePanel" in map_request
    assert "makeReviewPacket" in recipe_review
    assert "selectedPacketId" in recipe_review
    assert "Create Adjustment Template" in recipe_review
    assert "RequestIntelligencePanel" in recipe_review
    assert "detected_intents" in intelligence_panel
    assert "clarifying_questions" in intelligence_panel
    assert "Analysis plan" in intelligence_panel
    assert "Answer Clarifying Questions" in map_request
    assert "clarificationQuestionCount" in map_request
    assert "Clarifications applied" in recipe_review
    assert "RefinementSummary" in recipe_review


def test_clarification_page_components_and_workflow_state_exist():
    navigation = read("components/navigation.ts")
    page = read("app/clarify/page.tsx")
    panel = read("components/clarification-panel.tsx")
    question_card = read("components/clarification-question-card.tsx")
    summary = read("components/refinement-summary.tsx")
    store = read("lib/workflow-store.ts")
    api = read("lib/api.ts")

    assert 'href: "/clarify"' in navigation
    assert "Clarify Request" in page
    assert "Start Clarification" in panel
    assert "Submit Answers" in panel
    assert "Refine Recipe" in panel
    assert "Continue with Refined Recipe" in panel
    assert "single_choice" in question_card
    assert "multi_choice" in question_card
    assert "distance" in question_card
    assert "Layers added" in summary
    assert "warnings_remaining" in summary
    assert 'id: "clarify"' in store
    assert "clarificationSessionId" in store
    assert "refinedRecipe" in store
    assert "startClarification" in api
    assert "answerClarificationSession" in api
    assert "refineClarificationSession" in api
    assert "confirm-publish" not in panel.lower()
    assert "publish-draft-webmap" not in panel.lower()


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
    assert 'version: "2.0.0"' in source
    assert "redactProtected" in source


def test_analysis_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/analysis/page.tsx")
    client = read("components/analysis-client.tsx")
    api = read("lib/api.ts")
    store = read("lib/workflow-store.ts")
    types = read("types/automap.ts")
    preview = read("components/arcgis-map-preview.tsx")
    layer_panel = read("components/layer-panel.tsx")

    assert 'href: "/analysis"' in navigation
    assert "Safe bounded spatial execution" in page
    assert "Plan Analysis" in client
    assert "Execute Analysis" in client
    assert "Add result to map preview" in client
    assert "planAnalysis" in api
    assert "executeAnalysis" in api
    assert '"/api/analysis/plan"' in api
    assert '"/api/analysis/execute"' in api
    assert 'id: "analysis"' in store
    assert "analysisPlan" in store
    assert "analysisRun" in store
    assert "AnalysisExecutionPlan" in types
    assert "AnalysisRun" in types
    assert "Derived Local Analysis Result" in preview
    assert "derived_local_analysis" in layer_panel
    assert "confirm-publish" not in client.lower()
    assert "publish-draft-webmap" not in client.lower()


def test_learning_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/learning/page.tsx")
    center = read("components/learning-center-client.tsx")
    pattern_card = read("components/pattern-card.tsx")
    default_card = read("components/clarification-default-card.tsx")
    suggestions = read("components/learning-suggestions-panel.tsx")
    api = read("lib/api.ts")
    map_request = read("components/map-request-client.tsx")
    clarify_card = read("components/clarification-question-card.tsx")

    assert 'href: "/learning"' in navigation
    assert "Feedback Learning and Approved Pattern Library" in page
    assert "Learn From Approved Packet" in center
    assert "PatternCard" in pattern_card
    assert "ClarificationDefaultCard" in default_card
    assert "Suggested from approved patterns" in suggestions
    assert "getPatterns" in api
    assert "learnFromApprovedPacket" in api
    assert "recordRecipeFeedback" in api
    assert "getClarificationDefaults" in api
    assert "LearningSuggestionsPanel" in map_request
    assert "Use suggestion" in clarify_card
    assert "confirm-publish" not in center.lower()
    assert "publish-draft-webmap" not in center.lower()


def test_reports_navigation_page_and_components_exist():
    navigation = read("components/navigation.ts")
    page = read("app/reports/page.tsx")
    center = read("components/report-center-client.tsx")
    card = read("components/report-card.tsx")
    preview = read("components/report-preview.tsx")

    assert 'href: "/reports"' in navigation
    assert "Report and Export Center" in page
    assert "generateReport" in center
    assert "getReports" in center
    assert "getReport" in center
    assert "Generate Report" in center
    assert "report_summary.html" not in center.lower()
    assert "ReportCard" in card
    assert "ReportPreview" in preview
    assert "Dry-run" in preview
    assert "No report selected" in preview
    assert "confirm-publish" not in center.lower()
    assert "publish-draft-webmap" not in center.lower()


def test_report_api_client_functions_are_typed_and_safe():
    source = read("lib/api.ts")
    types = read("types/automap.ts")

    assert "generateReport" in source
    assert '"/api/generate-report"' in source
    assert "getReports" in source
    assert "getReport" in source
    assert "ReportSummary" in types
    assert "ReportDetail" in types
    assert "GenerateReportResponse" in types


def test_frontend_types_include_request_intelligence_recipe_fields():
    types = read("types/automap.ts")

    assert "RequestIntelligence" in types
    assert "AnalysisPlan" in types
    assert "LearnedContext" in types
    assert "request_intelligence" in types
    assert "analysis_plan" in types
    assert "learned_context" in types
    assert "why_selected" in types
    assert "why_not_legacy" in types
