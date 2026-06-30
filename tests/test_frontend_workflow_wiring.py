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


def test_composer_sessions_and_print_snapshots_are_durable():
    client = read("components/map-composer-client.tsx")
    store = read("lib/composer-session-store.ts")
    snapshot = read("lib/print-snapshot.ts")
    print_route = read("components/print/print-map-sheet-route.tsx")
    shared_renderer = read("components/map-renderer/shared-map-renderer.tsx")

    assert "saveComposerSession" in client
    assert "loadMostRecentComposerSession" in client
    assert "saveLockedMapState" in client
    assert "savePrintSnapshot" in client
    assert "loadPrintSnapshot" in client
    assert "validatePrintSnapshot" in client
    assert "response?.composer_map_state || (sessionId ? loadLockedMapState(sessionId) : null) || currentComposerPayload()?.map_state" in client
    assert "window.localStorage.setItem(storageKey" in client
    assert "Print snapshot could not be created yet" in client
    assert "SCHEMA_VERSION = 4" in store
    assert "hasRenderableMapPayload" in store
    assert "isUsableSession" in store
    assert "session.schema_version === SCHEMA_VERSION" in store
    assert "session.has_map_payload" in store
    assert "session.has_layers" in store
    assert "session.has_extent" in store
    assert "automap-composer-session:" in store
    assert "automap-locked-map-state:" in store
    assert "automap-print-snapshot:" in store
    assert "savePrintSnapshot" in store
    assert "loadPrintSnapshot" in store
    assert "TTL_MS = 24 * 60 * 60 * 1000" in store
    assert "database_url" in store
    assert "owner_name" in store
    assert "blank_or_white" in snapshot
    assert "ratio >= 0.025" in snapshot
    assert "window.localStorage.getItem(storageKey)" in print_route
    assert "disabled={!imageReady}" in print_route
    assert "Final map state expired" in print_route
    assert "preview_config: response?.preview_config || mapState.preview_config" in shared_renderer


def test_ai_planner_diagnostics_are_safe_frontend_fields():
    preview = read("components/map-composer/preview-step.tsx")
    types = read("types/automap.ts")
    api = read("lib/api.ts")

    assert "planner_used" in types
    assert "ai_status" in types
    assert "ai_confidence" in types
    assert "map_plan_summary" in types
    assert "Planner" in preview
    assert "interpreted_request" in preview
    assert "OPENAI_API_KEY" not in api
    assert ("NEXT_PUBLIC_" + "OPENAI") not in (api + types + preview)


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

    assert 'href: "/clarify"' not in navigation
    assert 'redirect("/map-composer")' in page
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
    assert "Frontend {productionLabels ? \"Vercel\" : \"3010\"}" in source
    assert "Backend/API {productionLabels ? \"Render\" : \"8010\"}" in source
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
    assert "Parcel not matched" in shell
    assert "parcel_preview_blocked" in shell
    assert "Try another parcel/PIN/address" in shell
    assert "confirm-publish" not in shell.lower()
    assert "publish-draft-webmap" not in shell.lower()


def test_simplified_workflow_page_guides_preview_and_blocks_fake_parcels():
    navigation = read("components/navigation.ts")
    page = read("app/workflow/page.tsx")
    client = read("components/workflow-client.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/workflow"' not in navigation
    assert 'redirect("/map-composer")' in page
    assert "Generate Recipe" in client
    assert "Create Preview" in client
    assert "Adjust Draft" in client
    assert "Run Analysis" in client
    assert "Generate Report / Print" in client
    assert "Parcel not matched" in client
    assert "Analysis is optional for context maps" in client
    assert "disabled={loading !== null || !canPreview}" in client
    assert "runWorkflow" in api
    assert '"/api/workflow/run"' in api
    assert "WorkflowRunResponse" in types
    assert "can_focus_map" in types
    assert "parcel_preview_blocked" in types
    assert "confirm-publish" not in client.lower()
    assert "publish-draft-webmap" not in client.lower()


def test_map_composer_is_primary_simple_workflow():
    navigation = read("components/navigation.ts")
    sidebar = read("components/sidebar.tsx")
    page = read("app/map-composer/page.tsx")
    client = read("components/map-composer-client.tsx")
    shell = read("components/map-composer/map-composer-shell.tsx")
    tabs = read("components/map-composer/composer-step-tabs.tsx")
    request_step = read("components/map-composer/request-step.tsx")
    preview_step = read("components/map-composer/preview-step.tsx")
    adjust_step = read("components/map-composer/adjust-step.tsx")
    export_step = read("components/map-composer/export-step.tsx")
    print_export_step = read("components/map-composer/print-export-step.tsx")
    composer_utils = read("components/map-composer/utils.ts")
    map_state_capture = read("components/map-composer/map-state-capture.tsx")
    step_types = read("components/map-composer/types.ts")
    composer_map_state_lib = read("lib/composer-map-state.ts")
    print_options = read("types/print-options.ts")
    automap_types = read("types/automap.ts")
    print_preview_panel = read("components/print-preview/print-preview-panel.tsx")
    map_sheet_document = read("components/print-preview/map-sheet-document.tsx")
    print_document_preview = read("components/print-preview/print-document-preview.tsx")
    print_map_page_preview = read("components/print-preview/print-map-page-preview.tsx")
    locked_map_sheet_page = read("components/print/LockedMapSheetPage.tsx")
    print_report_sections = read("components/print/PrintReportSections.tsx")
    print_map_sheet_route = read("components/print/print-map-sheet-route.tsx")
    print_map_sheet_page = read("app/print/map-sheet/page.tsx")
    print_job_types = read("types/print-job.ts")
    print_statistics = read("components/print-preview/print-statistics-section.tsx")
    print_layer_table = read("components/print-preview/print-layer-table-section.tsx")
    print_warning = read("components/print-preview/print-warning-section.tsx")
    print_sources = read("components/print-preview/print-source-notes-section.tsx")
    composer_preview = read("components/composer-map-preview.tsx")
    derived_layer = read("components/derived-geojson-layer.tsx")
    composer_layer_panel = read("components/composer-layer-panel.tsx")
    map_symbols = read("lib/map-symbols.ts")
    map_legend = read("components/map-legend.tsx")
    symbol_legend = read("components/map-symbol-legend.tsx")
    map_frame = read("components/map-renderer/map-frame.tsx")
    map_frame_title = read("components/map-frame-title.tsx")
    north_arrow = read("components/north-arrow.tsx")
    scale_bar = read("components/map-scale-bar.tsx")
    shared_renderer = read("components/map-renderer/shared-map-renderer.tsx")
    print_page = read("app/map-composer/[sessionId]/print/page.tsx")
    print_alias = read("app/print/[sessionId]/page.tsx")
    print_client = read("components/composer-print-client.tsx")
    exhibit_layout = read("components/exhibit-layout.tsx")
    exhibit_title = read("components/exhibit-title-block.tsx")
    exhibit_map_frame = read("components/exhibit-map-frame.tsx")
    exhibit_footer = read("components/exhibit-footer.tsx")
    exhibit_sources = read("components/exhibit-source-notes.tsx")
    exhibit_disclaimer = read("components/exhibit-disclaimer.tsx")
    exhibit_layer_table = read("components/exhibit-layer-table.tsx")
    exhibit_warnings = read("components/exhibit-warning-summary.tsx")
    exhibit_reports_page = read("app/reports/exhibits/page.tsx")
    exhibit_reports_client = read("components/exhibit-report-center-client.tsx")
    api = read("lib/api.ts")
    automap_proxy = read("app/api/automap/[...path]/route.ts")
    automap_presets = read("lib/automap-presets.ts")
    types = read("types/automap.ts")

    assert 'href: "/map-composer"' in navigation
    assert 'label: "Map Composer"' in navigation
    assert 'group: "Main"' in navigation
    assert 'group: "Support"' in navigation
    assert 'group: "Advanced"' not in navigation
    assert 'href: "/map-request"' not in navigation
    assert 'href: "/clarify"' not in navigation
    assert 'href: "/workflow"' not in navigation
    assert 'href: "/recipe-review"' not in navigation
    assert 'href: "/map-preview"' not in navigation
    assert 'href: "/adjustments"' not in navigation
    assert 'href: "/approval"' not in navigation
    assert 'href: "/publish-center"' not in navigation
    assert 'href: "/learning"' not in navigation
    assert 'href: "/scenario-workbench"' not in navigation
    assert 'href: "/analysis-reports"' not in navigation
    assert 'href: "/layer-catalog"' in navigation
    assert 'href: "/data-gaps"' in navigation
    assert 'href: "/external-sources"' in navigation
    assert 'href: "/history"' in navigation
    assert 'href: "/methodology"' in navigation
    assert 'href: "/system-status"' in navigation
    assert "nav-section-label" in sidebar
    assert '"Support"' in sidebar
    assert "MapComposerClient" in page
    assert "MapComposerShell" in client
    assert "RequestStep" in client
    assert "PreviewStep" in client
    assert "AdjustStep" in client
    assert "ExportStep" in client
    assert "PrintExportStep" in export_step
    assert "hasPreviewMapPayload" in composer_utils
    assert "canShowComposerMap" in composer_utils
    assert "composerResultState" in composer_utils
    assert "context_preview" in composer_utils
    assert 'composerResultState(response) === "no_matches" && hasContextMapPayload(response)' not in composer_utils
    assert "No matching features found" in preview_step
    assert "Map data could not be shown" in preview_step
    assert "Try broader request" in preview_step
    assert "result_state" in automap_types
    assert "requested_result" in automap_types
    assert "available_context" in automap_types
    assert "missing_operation" in automap_types
    assert "context_map_available" in automap_types
    assert "primary_result_available" in automap_types
    assert "requested_result_missing" in automap_types
    assert "legend_included?: boolean" in automap_types
    assert "query_status?: string | null" in automap_types
    assert "const previewReady = canShowComposerMap(response)" in client
    assert "const previewReady = canShowComposerMap(response)" in preview_step
    assert "if (!canShowComposerMap(response))" in adjust_step
    assert "if (!canShowComposerMap(response))" in print_export_step
    assert "exportComposerDraft" in client
    assert "saveComposerMapState" in client
    assert "exportComposerExhibit" in client
    assert "refineComposerRoute" in client
    assert "printJobStorageKey" in client
    assert "window.sessionStorage.setItem" in client
    assert 'window.open(`/print/map-sheet?job=${encodeURIComponent(printJobId)}&session=${encodeURIComponent(response.composer_session_id)}`, "_blank")' in client
    assert "/map-composer/${response.composer_session_id}/print" not in client
    assert "window.print()" not in client
    assert "buildComposerExportPayload" in client
    assert "printOptions" in client
    assert "lockedMapState" in client
    assert "Try Road-Following Route" in preview_step
    assert "Calculating road-following route" in request_step
    assert "currentComposerPayload" in client
    assert "report_config: mapState.report_section_config" in composer_map_state_lib
    assert "priorState = response.composer_map_state" in composer_map_state_lib
    assert "ComposerStepTabs" in shell
    assert "composer-workbench-shell" in shell
    assert "composer-step-body" in shell
    assert "ComposerStepId" in step_types
    assert "ComposerStepDisabled" in step_types
    assert "Request" in tabs
    assert "Preview" in tabs
    assert "Adjust" in tabs
    assert "Print / Export" in tabs
    assert "disabled={isDisabled}" in tabs
    assert "Clarify" not in tabs
    assert "Recipe" not in tabs
    assert "Dry-Run Publish" not in tabs
    assert "ArcGISMapPreview" not in client
    assert "MapView" in composer_preview
    assert "GraphicsLayer" in composer_preview
    assert "FeatureLayer" in composer_preview
    assert "MapImageLayer" in composer_preview
    assert "const layerUrl = layer.layer_url || layer.url" in composer_preview
    assert composer_preview.index("new modules.FeatureLayer") < composer_preview.index("new modules.MapImageLayer")
    assert "streets-vector" in composer_preview
    assert "Map preview failed to load." in composer_preview
    assert "composer-map-grid" not in composer_preview
    assert "arcgisSymbolForOverlay" in composer_preview
    assert "overlayIsGeneratedGraphic" in composer_preview
    assert "overlayIsClientRendered" in composer_preview
    assert "featureCollectionFromOverlay" in composer_preview
    assert "if (inline) return { overlay, collection: inline }" in composer_preview
    assert "if (overlayIsClientRendered(overlay)) return null" in composer_preview
    assert "MapLegend" in composer_preview
    assert "Commercial zoning" in map_legend
    assert "Zoning context" in map_legend
    assert "Major roads" in map_legend
    assert "Road context" in map_legend
    assert "contextSwatchStyle" in map_legend
    assert "layer.legend_included !== false" in map_legend
    assert "layer.feature_count !== 0" in map_legend
    assert "drawing_info as { renderer?: { symbol?: EsriSymbol } }" in map_legend
    assert "borderTopColor: color" in map_legend
    assert "background: color" in map_legend
    assert "NorthArrow" in composer_preview
    assert "MapScaleBar" in composer_preview
    assert "MapFrame" in composer_preview
    assert "frameModeForInteraction" in composer_preview
    assert "mode={frameMode}" in composer_preview
    assert "MapFrameTitle" in map_frame
    assert "data-map-frame-mode" in map_frame
    assert "map-interaction-blocker" in composer_preview
    assert "Locked preview" in composer_preview
    assert "Locked for print" in composer_preview
    assert "components: locked ? [\"attribution\"] : [\"attribution\", \"zoom\"]" in composer_preview
    assert "if ((!derivedOverlays.length && !contextLayers.length)" in composer_preview
    assert "if (!derivedOverlays.length && !contextLayers.length && packetId)" in composer_preview
    assert "mouseWheelZoomEnabled: false" in composer_preview
    assert "browserTouchPanEnabled: false" in composer_preview
    assert "onViewStateChange" in composer_preview
    assert "viewCommand" in composer_preview
    assert "map-frame-title" in map_frame_title
    assert "data-testid=\"map-frame-title\"" in map_frame_title
    assert "<MapScaleBar scale={viewScale} mapWidth={viewWidth}" in composer_preview
    assert "<MapLegend overlays={derivedOverlays} contextLayers={contextLayers} />" in composer_preview
    assert "contextDrawRank" in composer_preview
    assert 'typeof layer.draw_order === "number"' in composer_preview
    assert 'return layer.draw_order' in composer_preview
    assert "RESULT_OVERLAY_DRAW_RANK" in composer_preview
    assert "BOUNDARY_DRAW_RANK" in composer_preview
    assert "addContextLayers(map, contextLayers.filter((layer) => contextDrawRank(layer) < RESULT_OVERLAY_DRAW_RANK), modules)" in composer_preview
    assert 'addDerivedOverlayLayers(map, loaded, modules, ["parcel", "other"])' in composer_preview
    assert "contextDrawRank(layer) >= RESULT_OVERLAY_DRAW_RANK && contextDrawRank(layer) < BOUNDARY_DRAW_RANK" in composer_preview
    assert "addContextLayers(map, contextLayers.filter((layer) => contextDrawRank(layer) === BOUNDARY_DRAW_RANK), modules)" in composer_preview
    assert 'addDerivedOverlayLayers(map, loaded, modules, ["route", "origin", "target"])' in composer_preview
    frame_index = composer_preview.index("<MapFrame")
    legend_index = composer_preview.index("<MapLegend overlays={derivedOverlays} contextLayers={contextLayers} />")
    assert frame_index < legend_index
    assert "addDerivedOverlayLayers" in composer_preview
    assert "casing" in composer_preview
    assert "featureCollectionBounds" in derived_layer
    assert "Home marker" in composer_preview
    assert "nearest facility" in composer_layer_panel
    assert "Straight-line fallback" in composer_preview
    assert "Road-following draft route" in composer_preview
    assert "Hidden context" in composer_layer_panel
    assert "Local derived output" in composer_layer_panel
    assert "Open REST layer" not in composer_layer_panel
    assert "origin_home" in map_symbols
    assert "target_fire_station" in map_symbols
    assert "target_school" in map_symbols
    assert "target_hospital" in map_symbols
    assert "target_park" in map_symbols
    assert "target_library" in map_symbols
    assert "route_road_following" in map_symbols
    assert "route_straight_line" in map_symbols
    assert "svgDataUrl" in map_symbols
    assert "options: { casing?: boolean }" in map_symbols
    assert "kind?: \"source_layer\" | \"generated_graphic\"" in types
    assert "source_kind?: \"arcgis_source_layer\" | \"derived_feature_collection\"" in types
    assert "layer_type?: \"arcgis_feature_layer\"" in types
    assert "geojson?: Record<string, JsonValue>" in types
    assert "isRoadRouteMode" in map_symbols
    assert "width: roadRoute ? 3.2 : 2.4" in map_symbols
    assert "map-legend" in map_legend
    assert "Hidden context" not in map_legend
    assert "North arrow" in north_arrow
    assert "Map scale bar" in scale_bar
    assert "mapWidth?: number | null" in scale_bar
    assert "ENTERPRISE_WIDTH_PERCENT = 64" in scale_bar
    assert "map-scale-bar-centered" in scale_bar
    assert "centered enterprise" in scale_bar
    assert "0.25" in scale_bar
    assert "0.5 mi" in scale_bar
    assert "500" in scale_bar
    assert "approx." not in scale_bar
    assert "map-symbol-legend" in symbol_legend
    assert "Generate Draft Map" in request_step
    assert "automapPresets" in request_step
    assert "Try a preset" in request_step
    assert "Use preset" in request_step
    assert "Clicking a preset fills the request box" in request_step
    assert 'id="presets"' in request_step
    assert "samplePrompts" not in request_step
    assert "automapPresets" in automap_presets
    assert "presetPrompts" in navigation
    assert "presetForPrompt" in automap_presets
    assert automap_presets.count('id: "') >= 7
    assert "Nearest Fire Station Route" in automap_presets
    assert "Floodplain Parcel Screening" in automap_presets
    assert "Commercial Zoning Context" in automap_presets
    assert "Parcel Table Request" in automap_presets
    assert "Live working" in automap_presets
    assert "Partial / draft" in automap_presets
    assert "Data limited" in automap_presets
    assert "expected_output_type" in automap_presets
    assert "preset-status" in request_step
    assert "preset-output-type" in request_step
    assert "Recent Development Activity" in automap_presets
    assert "Commercial Growth Opportunity" in automap_presets
    assert "Historical Parcel/Zoning Lookup" in automap_presets
    assert "is_cabarrus_scoped: true" in automap_presets
    assert "Mecklenburg" not in automap_presets
    assert "Wake County" not in automap_presets
    preset_aside = request_step.lower().split("try a preset", maxsplit=1)[1].split("</aside>", maxsplit=1)[0]
    assert "static fallback" not in preset_aside
    assert "No map preview" not in request_step
    assert "Continue to Adjust" in preview_step
    assert "Regenerate Draft" in preview_step
    assert "Print / Export" in preview_step
    assert "SharedMapRenderer" in preview_step
    assert 'mode="preview_locked"' in preview_step
    assert "Parcel not matched" in preview_step
    assert "Address not found" in preview_step
    assert "Multiple possible address matches" in preview_step
    assert "Select Candidate" in preview_step
    assert "Correct address/PIN" in preview_step
    assert "Nearest facility draft" in preview_step
    assert "nearest fire/EMS station" in preview_step
    assert "Route mode" in preview_step
    assert "PreviewDetailsPanel" in preview_step
    assert "PREVIEW_DETAIL_TABS" in preview_step
    assert "Summary" in preview_step
    assert "Layers" in preview_step
    assert "Route / Analysis" in preview_step
    assert "Notes" in preview_step
    assert "Diagnostics" in preview_step
    assert "Why this map?" in preview_step
    assert "Interpreted request" in preview_step
    assert "How to read" in preview_step
    assert "AOI" in preview_step
    assert "100-year floodplain context" in preview_step
    assert "Affected parcel extraction unavailable; showing 100-year floodplain context" in preview_step
    assert "composerResultState" in preview_step
    assert "Partial" in preview_step
    assert "Parcel intersection unavailable" in preview_step
    assert "Partial context map" in preview_step
    assert "isPartialContextMap(response)" in preview_step
    assert "Adjust context map" in preview_step
    assert "Print partial context map" in preview_step
    assert "Requested result" in preview_step
    assert "Available context" in preview_step
    assert "Missing operation" in preview_step
    assert "Context map available" in preview_step
    assert "Display complexity" in preview_step
    assert "clipped to AOI" in preview_step
    assert "Visible map QA" in preview_step
    assert "visible_feature_summary" in preview_step
    assert "composer-preview-tab-list" in preview_step
    assert "composer-adjust-layout" in adjust_step
    assert "composer-adjust-controls-panel" in adjust_step
    assert "Lock Partial Context Map" in adjust_step
    assert "SharedMapRenderer" in adjust_step
    assert 'mode="adjust_interactive"' in adjust_step
    assert "Reset to Generated View" in adjust_step
    assert "Reset to Full Route / Feature Extent" in adjust_step
    assert "Center on Origin" in adjust_step
    assert "Center on Target" in adjust_step
    assert "Lock Final Map" in adjust_step
    assert "onMapViewStateChange" in adjust_step
    assert "Map controls" in adjust_step
    assert "Apply Adjustments" in adjust_step
    assert "Reset adjustments" in adjust_step
    assert "Route style" in adjust_step
    assert "Symbol overlays" in adjust_step
    assert "Line thickness" in adjust_step
    assert "Line style" in adjust_step
    assert "samplePrompts" not in adjust_step
    assert "Print Map" in print_export_step
    assert "Print Partial Context Map" in print_export_step
    assert "Open Browser Print" not in print_export_step
    assert "Generate Exhibit Package" in print_export_step
    assert "Map only" in print_export_step
    assert "Map Sheet" in print_export_step
    assert "Map Sheet Size" in print_export_step
    assert "Letter 8.5 x 11 in" in print_options
    assert "Tabloid 11 x 17 in" in print_options
    assert "ARCH D 24 x 36 in" in print_options
    assert "ARCH E 36 x 48 in" in print_options
    assert "Custom" in print_options
    assert "Fit locked extent to sheet" in print_export_step
    assert "Fixed map scale" in print_export_step
    assert "voting precinct maps" in print_export_step
    assert "Map + summary" in print_export_step
    assert "Full report" in print_export_step
    assert "MapStateCapture" in print_export_step
    assert "PrintPreviewPanel" in print_export_step
    assert "onPrintSnapshotReady" in print_export_step
    assert "printSnapshotReady" in print_export_step
    assert "Print snapshot ready" in print_export_step
    assert "Changing export mode adds pages after the locked map sheet" in print_export_step
    assert "Unlock and Edit Map" in print_export_step
    assert "PDF via Print Map" in print_export_step
    assert "PNG export draft" in print_export_step
    assert "Generate Review Report" in print_export_step
    assert "Advanced exports" in print_export_step
    assert "Export Layer Source CSV" in print_export_step
    assert "Export Warning Summary" in print_export_step
    assert "Export WebMap JSON" in print_export_step
    assert "Map furniture" in print_export_step
    assert "North arrow" in print_export_step
    assert "Scale bar" in print_export_step
    assert "Statistics" in print_export_step
    assert "Permit section" in print_export_step
    assert "reportConfig" not in print_export_step
    assert "Live Print Preview" in print_preview_panel
    assert "Final printout" in print_preview_panel
    assert "MapSheetDocument" in print_preview_panel
    assert "onSnapshotReady" in print_preview_panel
    assert 'id="automap-print-root"' in map_sheet_document
    assert "PrintDocumentPreview" in map_sheet_document
    assert "onSnapshotReady" in map_sheet_document
    assert "PrintMapPagePreview" in print_document_preview
    assert "PrintReportSections" in print_document_preview
    print_document_body = print_document_preview[print_document_preview.index("return (") :]
    assert print_document_body.index("<PrintMapPagePreview") < print_document_body.index("<PrintReportSections")
    assert "PrintStatisticsSection" in print_report_sections
    assert "PrintLayerTableSection" in print_report_sections
    assert "if (isMapSheet) return null" in print_report_sections
    assert "LockedMapSheetPage" in print_map_page_preview
    assert "snapshotDataUrl={snapshotUrl}" in print_map_page_preview
    assert "mapFallback={liveMapFallback}" in print_map_page_preview
    assert "LockedMapSheetPage" in locked_map_sheet_page
    assert "Route and distance" not in locked_map_sheet_page
    assert "Focused ArcGIS map" not in locked_map_sheet_page
    assert "inline-warning" not in locked_map_sheet_page
    assert "print-static-map-image" in locked_map_sheet_page
    assert "PrintMapSheetRoute" in print_map_sheet_page
    assert "Suspense" in print_map_sheet_page
    assert "useSearchParams" in print_map_sheet_route
    assert "sessionStorage.getItem" in print_map_sheet_route
    assert "printJobStorageKey(jobId)" in print_map_sheet_route
    assert "map_snapshot_data_url" in print_map_sheet_route
    assert "window.print()" in print_map_sheet_route
    assert "PrintReportSections" in print_map_sheet_route
    assert "LockedMapSheetPage" in print_map_sheet_route
    assert "printJobStorageKey" in print_job_types
    assert "DATABASE_URL" not in print_job_types
    assert "Statistics" in print_statistics
    assert "Layer Source Table" in print_layer_table
    assert "Warnings and Limitations" in print_warning
    assert "Source Notes" in print_sources
    assert "data-locked-map-state" in locked_map_sheet_page
    assert 'mode="print_locked"' in print_map_page_preview
    assert "mapOnly" in print_map_page_preview
    assert "Exact composer state" in map_state_capture
    assert "Standalone map sheet" in map_state_capture
    assert "Map exhibit first" in map_state_capture
    assert "buildComposerMapStateSnapshot" in composer_map_state_lib
    assert "map_sheet" in composer_map_state_lib
    assert "map_sheet" in print_options
    assert "map_plus_summary" in print_options
    assert "full_report" in print_options
    assert "include_layer_table: false" in composer_map_state_lib
    assert "DEFAULT_LIVE_PRINT_OPTIONS" in print_options
    assert "includeLayerTable: false" in print_options
    assert "sheetWidth" in print_options
    assert "includeLegend" in print_options
    assert "isMapSheet" in print_report_sections
    assert "print-sheet-mode-${printOptions.exportMode}" in locked_map_sheet_page
    assert "effectiveSheetDimensions" in locked_map_sheet_page
    assert "print-map-snapshot" in locked_map_sheet_page
    assert "data-print-snapshot" in locked_map_sheet_page
    assert "Sources: Cabarrus County / public GIS services. Draft output only." in locked_map_sheet_page
    assert "<NorthArrow />" in locked_map_sheet_page
    assert "<MapScaleBar scale={mapState?.current_scale}" in locked_map_sheet_page
    assert "<MapLegend overlays={overlays} contextLayers={contextLayers}" in locked_map_sheet_page
    assert "record.drawing_info" in locked_map_sheet_page
    assert "drawing_info: drawingInfo" in locked_map_sheet_page
    assert "locked-map-sheet-page" in locked_map_sheet_page
    assert "onSnapshotReady" in shared_renderer
    assert "mapOnly?: boolean" in shared_renderer
    assert "mapOnly={mapOnly}" in shared_renderer
    assert "composer-map-only" in composer_preview
    assert "Draft route based on public road centerlines. Not official navigation." in composer_preview
    assert "Straight-line fallback only. Road route unavailable." in composer_preview
    assert "Address matched. Related parcel was not resolved from verified fields, so the origin marker is shown as an address point." in composer_preview
    assert "normalizedWarningText" in print_warning
    assert "takeScreenshot" in composer_preview
    assert "Print snapshot could not be created yet" in print_client
    assert "Lock final map before printing" in print_client
    assert "disabled={!lockedMapState}" in print_client
    assert "System Snapshot" not in client
    assert "System Snapshot" not in request_step
    assert "Request to preview to print" not in client
    assert "composer-side" not in client
    assert "Address matched, but related parcel was not resolved" in preview_step
    normal_composer_sources = "\n".join([client, shell, tabs, request_step, preview_step, adjust_step, print_export_step])
    assert "Generate WebMap Draft" not in normal_composer_sources
    assert "Generate Review Packet" not in normal_composer_sources
    assert "confirm-publish" not in normal_composer_sources.lower()
    assert "publish-draft-webmap" not in normal_composer_sources.lower()
    assert "ComposerPrintClient" in print_page
    assert "ComposerPrintClient" in print_alias
    assert "MapSheetDocument" in print_client
    assert "SharedMapRenderer" in print_map_page_preview
    assert "ComposerMapPreview" in shared_renderer
    assert "mapState" in shared_renderer
    assert "preview_locked" in shared_renderer
    assert "adjust_interactive" in shared_renderer
    assert "print_locked" in shared_renderer
    assert "exhibit_locked" in shared_renderer
    assert "viewCommand" in shared_renderer
    assert "onViewStateChange" in shared_renderer
    assert "Print Map" in print_client
    assert "Open Browser Print" not in print_client
    assert "exhibit-layout" in exhibit_layout
    assert "ExhibitTitleBlock" in exhibit_layout
    assert "ExhibitMapFrame" in exhibit_layout
    assert "ExhibitLayerTable" in exhibit_layout
    assert "ExhibitWarningSummary" in exhibit_layout
    assert "exhibit-layout-${exportMode}" in exhibit_layout
    assert "showLayerTable" in exhibit_layout
    assert "exportMode === \"map_exhibit_only\"" in exhibit_layout
    assert "DRAFT - For GIS review only" in exhibit_title
    assert "GIS exhibit map frame" in exhibit_map_frame
    assert "No ArcGIS item was published" in exhibit_footer
    assert "local derived outputs" in exhibit_sources.lower()
    assert "official county map" in exhibit_disclaimer
    assert "Layer source table" in exhibit_layer_table
    assert "Warnings and limitations" in exhibit_warnings
    assert "ExhibitReportCenterClient" in exhibit_reports_page
    assert "getExhibits" in exhibit_reports_client
    assert "Open HTML" in exhibit_reports_client
    assert "generateComposerDraft" in api
    assert "presetForPrompt(prompt)" in api
    assert "preset_id" in api
    assert "preset_title" in api
    assert "expected_request_type" in api
    assert "exportComposerExhibit" in api
    assert "saveComposerMapState" in api
    assert '"/api/exhibits/generate"' in api
    assert '"/api/exhibits"' in api
    assert '"/api/composer/generate"' in api
    assert "`/api/composer/${encodeURIComponent(payload.composer_session_id)}/save-map-state`" in api
    assert "`/api/composer/${encodeURIComponent(payload.composer_session_id)}/export-exhibit`" in api
    assert "`/api/composer/${encodeURIComponent(composerSessionId)}/route-refine`" in api
    assert "timeoutMs: 240000" in api
    assert 'target.pathname === "/api/composer/generate" ? 240000 : 60000' in automap_proxy
    assert '"/api/composer/adjust"' in api
    assert '"/api/composer/export"' in api
    assert "ComposerResponse" in types
    assert "ComposerMapState" in types
    assert "ExportMode" in types
    assert "PrintExportOptions" in types
    assert "ReportSectionConfig" in types
    assert "ReportStatistics" in types
    assert "ExhibitPackage" in types
    assert "ExhibitSummary" in types
    assert "MapLayout" in types
    assert "map_layout" in types
    assert "ComposerAdjustPayload" in types
    assert "confirm-publish" not in client.lower()
    assert "publish-draft-webmap" not in client.lower()


def test_enterprise_scale_bar_css_is_centered_and_print_ready():
    css = read("app/globals.css")
    scale_index = css.index(".map-scale-bar {")
    scale_block = css[scale_index : css.index(".map-scale-bar-rule", scale_index)]

    assert "left: 50%" in scale_block
    assert "bottom: 18px" in scale_block
    assert "transform: translateX(-50%)" in scale_block
    assert "width: var(--scale-bar-width, 64%)" in scale_block
    assert "min-width: 360px" in scale_block
    assert "max-width: min(70%, 760px)" in scale_block
    assert "font-size: 13px" in css
    assert ".map-legend" in css
    assert "top: 72px" in css
    assert "bottom: auto" in css
    assert "@media print" in css
    assert "width: 64%" in css[css.index("@media print") :]
    assert "min-width: 420px" in css[css.index("@media print") :]


def test_map_composer_uses_enterprise_workbench_scroll_model():
    css = read("app/globals.css")
    preview_step = read("components/map-composer/preview-step.tsx")
    adjust_step = read("components/map-composer/adjust-step.tsx")
    print_export_step = read("components/map-composer/print-export-step.tsx")
    composer_preview = read("components/composer-map-preview.tsx")
    map_frame = read("components/map-renderer/map-frame.tsx")
    print_map_page_preview = read("components/print-preview/print-map-page-preview.tsx")
    locked_map_sheet_page = read("components/print/LockedMapSheetPage.tsx")

    assert ".content-grid:has(.map-composer-shell)" in css
    assert ".content-grid:has(.map-composer-shell) .right-rail" in css
    assert ".content-grid:has(.map-composer-shell) + .footer" in css
    assert ".map-composer-shell" in css
    shell_block = css[css.index(".map-composer-shell {") : css.index(".content-grid:has(.map-composer-shell)")]
    assert "height: calc(100vh - 116px)" in shell_block
    assert "overflow: hidden" in shell_block
    assert ".composer-step-body-adjust" in css
    assert ".composer-step-body-request,\n.composer-step-body-export" in css
    assert "overflow: hidden" in css[css.index(".composer-step-body-request,\n.composer-step-body-export") : css.index(".composer-request-layout")]
    assert ".composer-request-presets" in css
    request_presets_block = css[css.index(".composer-request-presets {") : css.index(".composer-preview-layout")]
    assert "repeat(2, minmax(0, 1fr))" in request_presets_block
    assert "overflow-y: auto" in request_presets_block
    assert ".preset-card" in css and "min-height: 172px" in css[css.index(".preset-card {") : css.index(".preset-card h4")]
    assert ".composer-preview-layout .shared-map-renderer-preview_locked" in css
    assert "min-height: clamp(560px, 68vh, 760px)" in css
    assert ".composer-preview-layout .map-frame-preview" in css
    assert "aspect-ratio: var(--map-frame-aspect-ratio, 16 / 10)" in css
    assert "data-map-frame-mode" in map_frame
    assert "map-frame-preview" in css
    assert ".composer-preview-layout" in css and "height: 100%" in css[css.index(".composer-preview-layout") : css.index(".composer-preview-main", css.index(".composer-preview-layout"))]
    assert ".composer-preview-sidebar" in css and "overflow: hidden" in css[
        css.index(".composer-preview-sidebar {") : css.index(".composer-compact-request")
    ]
    assert ".composer-preview-details-panel" in css
    details_block = css[css.index(".composer-preview-details-panel {") : css.index(".composer-preview-tab-list")]
    assert "grid-template-rows: auto minmax(0, 1fr)" in details_block
    assert "overflow: hidden" in details_block
    assert ".composer-preview-tab-panel" in css and "overflow-y: auto" in css[
        css.index(".composer-preview-tab-panel {") : css.index(".composer-preview-tab-panel > .panel")
    ]
    assert "PreviewDetailsPanel" in preview_step
    assert "role=\"tablist\"" in preview_step
    assert ".why-this-map-panel" in css
    assert ".composer-adjust-layout" in css and "height: 100%" in css[css.index(".composer-adjust-layout") : css.index(".composer-adjust-map-column", css.index(".composer-adjust-layout"))]
    assert ".composer-adjust-map-column" in css and "overflow: hidden" in css[
        css.index(".composer-adjust-map-column {") : css.index(".composer-adjust-controls-panel {")
    ]
    assert ".composer-adjust-controls-panel" in css and "overflow-y: auto" in css[
        css.index(".composer-adjust-controls-panel {") : css.index(".composer-adjust-controls-panel .composer-layer-row")
    ]
    assert ".composer-adjust-action-bar" in css and "position: sticky" in css[css.index(".composer-adjust-action-bar") : css.index(".workflow-prompt-panel")]
    assert ".composer-step-tab" in css and "min-height: 52px" in css[css.index(".composer-step-tab {") : css.index(".composer-step-tab span")]
    assert "showLayerPanel?: boolean" in composer_preview
    assert "showLayerPanel ? <ComposerLayerPanel" in composer_preview
    assert "showLayerPanel={false}" in preview_step
    assert "showLayerPanel={false}" in adjust_step
    assert "SharedMapRenderer" in print_map_page_preview
    assert 'mode="print_locked"' in print_map_page_preview
    assert ".composer-step-body-export" in css and "overflow: hidden" in css[css.index(".composer-step-body-export") : css.index(".composer-request-layout")]
    assert ".composer-export-panel" in css and "overflow-y: auto" in css[
        css.index(".composer-export-panel {") : css.index(".composer-export-buttons")
    ]
    assert ".print-preview-panel" in css
    assert ".print-preview-scroll" in css and "overflow-y: auto" in css[css.index(".print-preview-scroll") : css.index(".print-document-preview")]
    assert "#automap-print-root" in css
    assert "body * {\n    visibility: hidden;" in css
    assert "#automap-print-root,\n  #automap-print-root *" in css
    assert ".automap-print-document" in css
    assert ".locked-map-sheet-page" in css or "locked-map-sheet-page" in locked_map_sheet_page
    assert "flex-shrink: 0" in css[css.index(".print-preview-sheet") : css.index(".print-preview-title-block")]
    assert "page-break-inside: avoid" in css[css.index(".print-map-page-preview") : css.index(".print-preview-title-block")]
    assert ".print-preview-section" in css and "break-before: page" in css[css.index(".print-preview-section") : css.index(".print-preview-section h2")]
    assert ".composer-map-only" in css
    assert ".print-map-snapshot" in css
    assert ".print-preview-map-frame:has(.print-map-snapshot) .shared-map-renderer" in css
    assert "width: min(var(--print-width, 100vw), 100vw)" in css
    assert "height: min(var(--print-height, 100vh), 100vh)" in css
    assert "size: auto" in css[css.index("@page") :]
    assert "PrintPreviewPanel" in print_export_step
    assert "lockedMapState" in print_export_step
    assert "!canOpenPrint" in print_export_step
    assert "samplePrompts" not in adjust_step


def test_internal_workflow_pages_redirect_to_composer():
    internal_pages = [
        "app/recipe-review/page.tsx",
        "app/map-preview/page.tsx",
        "app/adjustments/page.tsx",
        "app/approval/page.tsx",
        "app/publish-center/page.tsx",
        "app/map-request/page.tsx",
        "app/clarify/page.tsx",
        "app/workflow/page.tsx",
    ]

    for path in internal_pages:
        page = read(path)
        assert 'redirect("/map-composer")' in page
        assert "WorkflowStepper" not in page
        assert "Internal recipe review tools" not in page
        assert "Generate WebMap Draft" not in page
        assert "Generate Review Packet" not in page


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
    map_request = read("components/map-request-client.tsx")
    proxy_route = read("app/api/automap/[...path]/route.ts")

    assert "Backend is offline. Start it with: python -m app.main --serve-ui --ui-port 8010" in source
    assert "Vercel proxy could not reach Render backend at" in source
    assert "Render API is online, but ${path} timed out" in source
    assert "Render API is online, but the Vercel proxy could not complete ${path}" in source
    assert "same-origin proxy network block" in source
    assert "This is often a CORS deployment-origin issue" in source
    assert "PRODUCTION_PROXY_API_BASE_PATH" in source
    assert '"/api/automap"' in source
    assert "getApiFetchBase" in source
    assert "getApiDisplayHost" in source
    assert "Current page origin:" in source
    assert "window.location.origin" in source
    assert "API host:" in source
    assert "Fetch base:" in source
    assert "Route:" in source
    assert "Failure:" in source
    assert "getDbHealth" in source
    assert '"/api/db-health"' in source
    assert '"/api/status?mode=quick"' in source
    assert "database status check timed out" in source
    assert "http://127.0.0.1:8010" in source
    assert "https://automap-api.onrender.com" in source
    assert "normalizeApiBaseUrl" in source
    assert "Invalid public API URLs are treated as unset" in source
    assert "getApiBaseUrl" in source
    assert "DEFAULT_PRODUCTION_API_BASE_URL" in source
    assert "Render backend route not found:" in source
    assert "Render backend returned HTTP ${response.status}" in source
    assert "apiUrl(path)" in source
    assert "timeoutMs: 60000" in source
    assert 'version: "4.9.0"' in source
    assert "redactProtected" in source
    assert "AutoMap is checking the catalog, parcel fields, and context layers" in map_request
    assert "AUTOMAP_API_SERVER_URL" in proxy_route
    assert "DEFAULT_AUTOMAP_API_SERVER_URL" in proxy_route
    assert "backend_unreachable" in proxy_route
    assert "Vercel proxy could not reach Render backend." in proxy_route
    assert "Invalid AutoMap API proxy path" in proxy_route
    assert "segment.includes(\":\")" in proxy_route
    assert "FORWARDED_REQUEST_HEADERS" in proxy_route
    assert '"content-type"' in proxy_route
    assert '"accept"' in proxy_route
    assert "request.text()" in proxy_route
    assert "error_category" in proxy_route


def test_vercel_proxy_route_maps_automap_paths_without_secret_forwarding():
    proxy_route = read("app/api/automap/[...path]/route.ts")

    assert "frontend/app/api/automap" not in proxy_route.lower()
    assert "new URL(`/api/${safePath}`, serverUrl)" in proxy_route
    assert "AUTOMAP_API_SERVER_URL" in proxy_route
    assert "https://automap-api.onrender.com" in proxy_route
    assert "Invalid AutoMap API proxy path" in proxy_route
    assert "segment === \"..\"" in proxy_route
    assert "segment.includes(\":\")" in proxy_route
    assert "FORWARDED_REQUEST_HEADERS" in proxy_route
    assert '"content-type"' in proxy_route
    assert '"accept"' in proxy_route
    assert '"host"' not in proxy_route
    assert '"connection"' not in proxy_route
    assert '"cookie"' not in proxy_route
    assert "backend_unreachable" in proxy_route
    assert "database_url" not in proxy_route.lower()
    assert "service_role" not in proxy_route.lower()


def test_production_status_badges_are_render_aware():
    top_header = read("components/top-header.tsx")
    status_panel = read("components/status-panel.tsx")

    assert "getApiRuntimeInfo" in top_header
    assert "FE {frontendLabel}" in top_header
    assert "API {apiLabel}" in top_header
    assert "Scope: Cabarrus County, NC" in top_header
    assert "Demo Mode" in top_header
    assert "Waking" in top_header
    assert "DB {dbLabel}" not in top_header
    assert "database_connected" not in top_header
    assert "FE 3010" not in top_header
    assert "API 8010" not in top_header
    assert "getApiRuntimeInfo" in status_panel
    assert "productionLabels ? \"Vercel\"" in status_panel
    assert "productionLabels ? \"Render\"" in status_panel


def test_frontend_does_not_expose_supabase_service_role_key():
    skipped = {"node_modules", ".next"}
    combined = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in FRONTEND.rglob("*")
        if path.is_file() and not any(part in skipped for part in path.parts)
    )

    assert "service_role" not in combined
    assert "supabase_service_role" not in combined


def test_table_center_page_components_and_api_are_present():
    navigation = read("components/navigation.ts")
    page = read("app/tables/page.tsx")
    client = read("components/table-center-client.tsx")
    request_panel = read("components/table-request-panel.tsx")
    recipe_card = read("components/table-recipe-card.tsx")
    preview_grid = read("components/table-preview-grid.tsx")
    export_card = read("components/table-export-card.tsx")
    safety_warning = read("components/table-safety-warning.tsx")
    composer_preview = read("components/map-composer/preview-step.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/tables"' in navigation
    assert "Tables" in navigation
    assert "Table and Data Export Center" in page
    assert "TableCenterClient" in page
    assert "TableRequestPanel" in client
    assert "TableRecipeCard" in client
    assert "TablePreviewGrid" in client
    assert "TableExportCard" in client
    assert "TableSafetyWarning" in client
    assert "Plan Table" in request_panel
    assert "returnGeometry=false" in preview_grid
    assert "Export Table" in export_card
    assert "Export needs review" in safety_warning
    assert "Table recipe" in recipe_card
    assert "Open Table Center" in composer_preview
    assert "Table preview live" in composer_preview
    assert "Table draft" in composer_preview
    assert "CSV export" in composer_preview
    assert "compact-table-preview" in composer_preview
    assert "planTableRequest" in api
    assert '"/api/tables/plan"' in api
    assert '"/api/tables/export"' in api
    assert "TableRecipe" in types


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
    proximity_page = read("app/proximity/page.tsx")
    proximity_form = read("components/proximity-form.tsx")
    proximity_result = read("components/proximity-result-card.tsx")
    proximity_map = read("components/proximity-map-panel.tsx")
    route_warning = read("components/route-warning-panel.tsx")
    api = read("lib/api.ts")
    types = read("types/automap.ts")

    assert 'href: "/parcel-workspace"' in navigation
    assert 'href: "/proximity"' in navigation
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
    assert "ProximityResultCard" in page
    assert "Nearest School" in page
    assert "Nearest Fire Station" in page
    assert "Containing Fire District" in page
    assert "Route Draft to Address" in page
    assert "Nearest facility and route drafts" in proximity_page
    assert "ProximityForm" in proximity_page
    assert "ProximityResultCard" in proximity_page
    assert "ProximityMapPanel" in proximity_page
    assert "RouteWarningPanel" in proximity_page
    assert "Run Proximity Prompt" in proximity_form
    assert "Find Nearest" in proximity_form
    assert "Create Route Draft" in proximity_form
    assert "Line type" in proximity_result
    assert "Straight-line fallback" in proximity_map
    assert "straight_line_fallback" in route_warning
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
    assert "runProximity" in api
    assert "runNearestFacility" in api
    assert "runRouteDraft" in api
    assert "listProximityResults" in api
    assert '"/api/parcels/parse"' in api
    assert '"/api/parcels/profile-fields"' in api
    assert '"/api/parcels/match"' in api
    assert "/fetch-geometry" in api
    assert '"/api/parcels/context"' in api
    assert '"/api/proximity"' in api
    assert '"/api/proximity/nearest"' in api
    assert '"/api/proximity/route-draft"' in api
    assert '"/api/proximity/results"' in api
    assert "ParcelSet" in types
    assert "ParcelContext" in types
    assert "ParcelFieldProfileResponse" in types
    assert "SelectedParcelGeometryResult" in types
    assert "ParcelReport" in types
    assert "ProximityResult" in types
    assert "confirm-publish" not in page.lower()
    assert "confirm-publish" not in proximity_page.lower()
    assert "publish-draft-webmap" not in page.lower()
    assert "publish-draft-webmap" not in proximity_page.lower()


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

    assert 'href: "/analysis-reports"' not in navigation
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

    assert 'href: "/learning"' not in navigation
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

    assert 'href: "/scenario-workbench"' not in navigation
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


def test_recruiter_safe_landing_and_health_fallback_are_present():
    landing = read("app/page.tsx")
    health_card = read("components/production-health-card.tsx")
    system_status = read("app/system-status/page.tsx")
    methodology = read("app/methodology/page.tsx")
    smoke_script = (ROOT / "scripts" / "production_smoke_check.py").read_text(encoding="utf-8")

    assert "County GIS Request Engine" in landing
    assert "Turn plain-language county GIS requests into draft maps, tables, and review-ready outputs." in landing
    assert "Open Live Demo" in landing
    assert "View Presets" in landing
    assert "View Methodology" in landing
    assert "View Static Demo" in landing
    assert "View System Status" in landing
    assert "What it does" in landing
    assert "Live demo scope" in landing
    assert "Example capabilities" in landing
    assert "Tech stack" in landing
    assert "Safety notes" in landing
    assert "ProductionHealthCard" not in landing
    assert "System architecture" in methodology
    assert "Vercel API proxy" in methodology
    assert "Render FastAPI" in methodology
    assert "Supabase PostGIS" in methodology
    assert "Real ArcGIS publishing is disabled" in methodology
    assert "backend waking up" in health_card.lower()
    assert "Last verified: live system check passed" in health_card
    assert "Real publish: disabled" in health_card
    assert "Technical diagnostics" in system_status
    assert "Technical status for project owner/reviewers" in system_status
    assert "Database unavailable" in system_status
    assert "production_smoke_check" not in smoke_script.lower()
    assert "https://auto-map-cyan.vercel.app" in smoke_script
    assert "DATABASE" + "_URL" not in smoke_script
    assert "service" + "_role" not in smoke_script.lower()
    assert "nearest fire station preset" in smoke_script
    assert "floodplain parcel preset" in smoke_script
    assert "parcel table preset" in smoke_script


def test_static_demo_fallback_is_available_for_slow_composer_requests():
    client = read("components/map-composer-client.tsx")
    request_step = read("components/map-composer/request-step.tsx")
    static_demo = read("lib/static-demo.ts")
    navigation = read("components/navigation.ts")
    automap_presets = read("lib/automap-presets.ts")

    assert "staticDemoComposerResponse" in client
    assert "setTimeout(resolve, 10000)" in client
    assert "setShowStaticDemoOffer(true)" in client
    assert "setStaticDemoPanelVisible(true" in client
    assert "elapsed >= FALLBACK_OFFER_DELAY_SECONDS" in client
    assert "PUBLIC_DEMO_TIMEOUT_MS = 240000" in client
    assert "pendingLiveResponse" in client
    assert "Switch to live result" in request_step
    assert "public_demo_timeout" in client
    assert "Retry live request" in request_step
    assert "View static demo" in request_step
    assert "Keep waiting" in request_step
    assert "Cancel request" in request_step
    assert "Open Project Summary" in request_step
    assert "Static demo fallback" in request_step
    assert "showStaticDemoOffer && !showStaticDemoPanel" in request_step
    assert "showStaticDemoPanel" in request_step
    assert "Live generation stays primary" in request_step
    assert "Live backend is warming up" in client
    assert "Nearest Fire Station from 793 Bartram Ave" in static_demo
    assert "Static demo fallback. Live backend unavailable or warming up." in static_demo
    assert "Demo uses a Cabarrus County address." in static_demo
    assert "This prototype is county-scoped, not a nationwide address search tool." in static_demo
    assert "presetPrompts" in navigation
    assert "make a map of my address 793 bartram ave" in automap_presets
    assert "give me a table of parcels in Cabarrus County" in automap_presets
    assert "published: false" in static_demo
    assert "owner" not in static_demo.lower()


def test_public_composer_explains_cabarrus_address_scope():
    landing = read("app/page.tsx")
    request_step = read("components/map-composer/request-step.tsx")
    preview_step = read("components/map-composer/preview-step.tsx")
    top_header = read("components/top-header.tsx")

    assert "Cabarrus County, NC" in landing
    assert "Live address and parcel workflows currently support {STATIC_DEMO_SCOPE} only" in request_step
    assert "Address not found in Cabarrus County records" in preview_step
    assert "Try a Cabarrus County address, parcel/PIN, or planning request" in preview_step
    assert "Scope: Cabarrus County, NC" in top_header
