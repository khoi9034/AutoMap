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
    assert "SourceCoveragePanel" in map_request
    assert "DevelopmentContextPanel" in map_request
    assert "TransportationContextPanel" in map_request
    assert "makeReviewPacket" in recipe_review
    assert "selectedPacketId" in recipe_review
    assert "Create Adjustment Template" in recipe_review
    assert "RequestIntelligencePanel" in recipe_review
    assert "SourceCoveragePanel" in recipe_review
    assert "detected_intents" in intelligence_panel
    assert "clarifying_questions" in intelligence_panel
    assert "Analysis plan" in intelligence_panel
    assert "Scenario workflow recommended" in intelligence_panel
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
    resolver = read("components/data-gap-resolver-client.tsx")

    assert "These are not AutoMap failures" in source
    assert "DataGapResolverClient" in source
    assert "current_permits" in resolver
    assert "current_planning_cases" in resolver
    assert "current_development_pipeline" in resolver
    assert "Proxy sources are not official approvals" in resolver
    assert "ProxySourceBadge" in resolver
    assert "getGapCandidates" in resolver
    assert "resolveDataGap" in resolver
    assert "partially_supported" in resolver
    assert "verified" in resolver


def test_external_sources_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/external-sources/page.tsx")
    client = read("components/external-sources-client.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/external-sources"' in navigation
    assert "Candidate REST source connector registry" in page
    assert "Load Seed Sources" in client
    assert "Inspect Metadata" in client
    assert "Discover Sources" in client
    assert "Verify All Sources" in client
    assert "Verify Selected Source" in client
    assert "Discovery results" in client
    assert "Proxy" in client
    assert "ProxySourceBadge" in client
    assert "context layers" in client
    assert "No ArcGIS login is required" in client
    assert "getExternalSources" in api
    assert "loadExternalSources" in api
    assert "inspectExternalSources" in api
    assert "discoverExternalSources" in api
    assert "verifyExternalSource" in api
    assert "verifyAllExternalSources" in api
    assert '"/api/external-sources"' in api
    assert '"/api/external-sources/discover"' in api
    assert '"/api/external-sources/verify-all"' in api
    assert "/api/data-gaps/${" in api
    assert "ExternalSource" in types
    assert "SourceDiscoveryResult" in types
    assert "DataGapCandidate" in types
    assert "confirm-publish" not in client.lower()
    assert "publish-draft-webmap" not in client.lower()


def test_api_client_has_timeout_and_sanitized_fallback_version():
    source = read("lib/api.ts")

    assert "Backend API request timed out" in source
    assert "http://127.0.0.1:8010" in source
    assert 'version: "3.0.0"' in source
    assert "redactProtected" in source


def test_parcel_workspace_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/parcel-workspace/page.tsx")
    input_panel = read("components/parcel-input-panel.tsx")
    match_table = read("components/parcel-match-table.tsx")
    layer_picker = read("components/parcel-context-layer-picker.tsx")
    summary = read("components/parcel-context-summary.tsx")
    report_card = read("components/parcel-report-card.tsx")
    field_status = read("components/parcel-field-status.tsx")
    candidate_table = read("components/parcel-candidate-table.tsx")
    selected_card = read("components/selected-parcel-layer-card.tsx")
    nearby_controls = read("components/parcel-nearby-controls.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/parcel-workspace"' in navigation
    assert "Parcel Workspace" in page
    assert "ParcelInputPanel" in page
    assert "ParcelMatchTable" in page
    assert "ParcelContextLayerPicker" in page
    assert "ParcelContextSummary" in page
    assert "ParcelReportCard" in page
    assert "ParcelFieldStatus" in page
    assert "ParcelCandidateTable" in page
    assert "SelectedParcelLayerCard" in page
    assert "ParcelNearbyControls" in page
    assert "Parse Identifiers" in input_panel
    assert "Match Parcels" in input_panel
    assert "returnGeometry=false" in match_table
    assert "planning/development proxy" in layer_picker
    assert "SourceCoveragePanel" in summary
    assert "Verified field profile" in field_status
    assert "Ambiguous candidates" in candidate_table
    assert "Fetch Selected Parcel Geometry" in selected_card
    assert "Nearby context" in nearby_controls
    assert "outputs/parcel_reports" in page
    assert "parseParcels" in api
    assert "profileParcelFields" in api
    assert "matchParcels" in api
    assert "createParcelSet" in api
    assert "fetchSelectedParcelGeometry" in api
    assert "createParcelContext" in api
    assert "generateParcelReport" in api
    assert '"/api/parcels/parse"' in api
    assert '"/api/parcels/profile-fields"' in api
    assert '"/api/parcels/match"' in api
    assert "/fetch-geometry" in api
    assert '"/api/parcels/context"' in api
    assert "ParcelSet" in types
    assert "ParcelContext" in types
    assert "ParcelFieldProfileResponse" in types
    assert "SelectedParcelGeometryResult" in types
    assert "ParcelReport" in types
    assert "confirm-publish" not in page.lower()
    assert "publish-draft-webmap" not in page.lower()


def test_analysis_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/analysis/page.tsx")
    client = read("components/analysis-client.tsx")
    refinement_panel = read("components/analysis-refinement-panel.tsx")
    option_card = read("components/refinement-option-card.tsx")
    result_panel = read("components/refinement-result-panel.tsx")
    api = read("lib/api.ts")
    store = read("lib/workflow-store.ts")
    types = read("types/automap.ts")
    preview = read("components/arcgis-map-preview.tsx")
    layer_panel = read("components/layer-panel.tsx")

    assert 'href: "/analysis"' in navigation
    assert "Safe bounded spatial execution" in page
    assert "Plan Analysis" in client
    assert "Execute Analysis" in client
    assert "Strategy" in client
    assert "Optimized count" in client
    assert "Narrowing suggestions" in client
    assert "AnalysisRefinementPanel" in client
    assert "Add result to map preview" in client
    assert "Refine Analysis" in refinement_panel
    assert "Create Refinement Options" in refinement_panel
    assert "Parameters JSON" in refinement_panel
    assert "Execute Refinement" in refinement_panel
    assert "Generate Analysis Report" in refinement_panel
    assert "Tradeoffs" in option_card
    assert "No geometry download" in result_panel
    assert "planAnalysis" in api
    assert "executeAnalysis" in api
    assert "createAnalysisRefinement" in api
    assert "selectAnalysisRefinement" in api
    assert "executeAnalysisRefinement" in api
    assert "generateAnalysisReportFromRefinement" in api
    assert '"/api/analysis/plan"' in api
    assert '"/api/analysis/execute"' in api
    assert '"/api/analysis/refinements"' in api
    assert 'id: "analysis"' in store
    assert "analysisPlan" in store
    assert "analysisRun" in store
    assert "AnalysisExecutionPlan" in types
    assert "optimized_query_plan" in types
    assert "AnalysisRun" in types
    assert "AnalysisRefinementSession" in types
    assert "AnalysisRefinementOption" in types
    assert "Derived Local Analysis Result" in preview
    assert "derived_local_analysis" in layer_panel
    assert "confirm-publish" not in client.lower()
    assert "publish-draft-webmap" not in client.lower()
    assert "confirm-publish" not in refinement_panel.lower()
    assert "publish-draft-webmap" not in refinement_panel.lower()


def test_analysis_reports_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/analysis-reports/page.tsx")
    center = read("components/analysis-reports-client.tsx")
    card = read("components/analysis-report-card.tsx")
    preview = read("components/analysis-report-preview.tsx")
    table = read("components/analysis-summary-table.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/analysis-reports"' in navigation
    assert "Summary analytics and report exports" in page
    assert "listAnalysisRuns" in center
    assert "listAnalysisRefinements" in center
    assert "listAnalysisReports" in center
    assert "generateAnalysisReport" in center
    assert "generateAnalysisReportFromRefinement" in center
    assert "AnalysisReportCard" in card
    assert "AnalysisReportPreview" in preview
    assert "AnalysisSummaryTable" in table
    assert "returnGeometry=false" in center
    assert '"/api/analysis/reports"' in api
    assert '"/api/analysis/reports/from-refinement"' in api
    assert "AnalysisReportSummary" in types
    assert "AnalysisReportData" in types
    assert "confirm-publish" not in center.lower()
    assert "publish-draft-webmap" not in center.lower()


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
    assert "data_gap_resolution_context" in types
    assert "why_selected" in types
    assert "why_not_legacy" in types


def test_v26_source_coverage_components_are_wired_and_safe():
    source_panel = read("components/source-coverage-panel.tsx")
    proxy_badge = read("components/proxy-source-badge.tsx")
    development_panel = read("components/development-context-panel.tsx")
    transportation_panel = read("components/transportation-context-panel.tsx")
    catalog = read("components/catalog-search-client.tsx")
    types = read("types/automap.ts")

    assert "official_sources" in source_panel
    assert "proxy_sources" in source_panel
    assert "limited_coverage_sources" in source_panel
    assert "reference_sources" in source_panel
    assert "missing_official_sources" in source_panel
    assert "Proxy and reference layers are review context" in source_panel
    assert "Official" in proxy_badge
    assert "Proxy" in proxy_badge
    assert "Limited coverage" in proxy_badge
    assert "Reference" in proxy_badge
    assert "not be treated as official approvals" in development_panel
    assert "AADT and STIP are context layers" in transportation_panel
    assert "ProxySourceBadge" in catalog
    assert "known_limitations" in catalog
    assert "source_coverage" in types
    assert "SourceCoverageEntry" in types
    assert "confirm-publish" not in source_panel.lower()
    assert "publish-draft-webmap" not in source_panel.lower()


def test_v27_scenarios_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/scenarios/page.tsx")
    builder = read("components/scenario-builder.tsx")
    factors = read("components/scenario-factor-table.tsx")
    scorecard = read("components/scenario-scorecard.tsx")
    questions = read("components/scenario-review-questions.tsx")
    coverage = read("components/scenario-source-coverage.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/scenarios"' in navigation
    assert "Planning scenario and suitability intelligence" in page
    assert "Generate Scenario" in builder
    assert "Generate Scenario Report" in builder
    assert "Create Map Recipe" in builder
    assert "Map commercial growth opportunities near high traffic roads but avoid floodplain." in builder
    assert "ScenarioFactorTable" in factors
    assert "Scoring framework" in factors
    assert "Scenario scorecard" in scorecard
    assert "Review questions" in questions
    assert "SourceCoveragePanel" in coverage
    assert "makeScenario" in api
    assert "listScenarios" in api
    assert "generateScenarioReport" in api
    assert '"/api/scenarios"' in api
    assert "PlanningScenario" in types
    assert "ScenarioFactor" in types
    assert "ScenarioReport" in types
    assert "confirm-publish" not in builder.lower()
    assert "publish-draft-webmap" not in builder.lower()


def test_v28_scenario_workbench_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/scenario-workbench/page.tsx")
    client = read("components/scenario-workbench-client.tsx")
    editor = read("components/scenario-weight-editor.tsx")
    card = read("components/scenario-variant-card.tsx")
    comparison = read("components/scenario-comparison-table.tsx")
    panel = read("components/scenario-to-recipe-panel.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/scenario-workbench"' in navigation
    assert "ScenarioWorkbenchClient" in page
    assert "Tune weights" in page
    assert "ScenarioWeightEditor" in client
    assert "ScenarioComparisonTable" in client
    assert "ScenarioToRecipePanel" in client
    assert "Save Variant" in editor
    assert "Proxy sources remain context only" in editor
    assert "Scenario variant" in card
    assert "Scenario comparison" in comparison
    assert "Convert to Recipe" in panel
    assert "createScenarioVariant" in api
    assert "listScenarioVariants" in api
    assert "compareScenarios" in api
    assert "scenarioToRecipe" in api
    assert "scenarioVariantToRecipe" in api
    assert "ScenarioVariant" in types
    assert "ScenarioComparison" in types
    assert "ScenarioToRecipeResult" in types
    assert "confirm-publish" not in client.lower()
    assert "publish-draft-webmap" not in client.lower()
