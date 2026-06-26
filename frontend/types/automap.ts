export type JsonValue =
  | string
  | number
  | boolean
  | null
  | JsonValue[]
  | { [key: string]: JsonValue };

export type SystemStatus = {
  version?: string;
  database_connected?: boolean;
  database_name?: string | null;
  database_host_kind?: "supabase_direct" | "supabase_pooler" | "local_dev" | "unknown" | string;
  automap_schema?: string;
  postgis_version?: string | null;
  catalog?: {
    layer_count?: number;
    verified_layer_count?: number;
    new_opendata_layer_count?: number;
    legacy_layer_count?: number;
    historical_layer_count?: number;
  };
  profiles?: {
    field_profile_count?: number;
    value_profile_count?: number;
  };
  data_gap_count?: number;
  external_source_count?: number;
  request_history_count?: number;
  approval_history_count?: number;
  analysis_run_count?: number;
  analysis_refinement_count?: number;
  analysis_report_count?: number;
  planning_scenario_count?: number;
  scenario_variant_count?: number;
  scenario_comparison_count?: number;
  parcel_set_count?: number;
  parcel_context_session_count?: number;
  parcel_field_map_count?: number;
  proximity_request_count?: number;
  proximity_result_count?: number;
  table_request_count?: number;
  table_export_count?: number;
  packets?: {
    review_packet_count?: number;
    adjusted_packet_count?: number;
    approved_packet_count?: number;
  };
  ports?: {
    frontend?: number;
    backend_api?: number;
    reserved?: number[];
  };
  arcgis_publisher_mode?: string;
  arcgis_publish_profile?: string;
  real_publish_enabled?: boolean;
  counts_partial?: boolean;
  status_mode?: "quick" | "full" | string;
  errors?: string[];
};

export type LayerRecord = {
  layer_key?: string;
  layer_name?: string;
  category?: string;
  source_status?: string;
  source_priority?: number;
  is_verified?: boolean;
  is_historical?: boolean;
  layer_url?: string;
  service_name?: string;
  aliases?: string[];
  approval_status?: string;
  known_limitations?: string;
  canonical_topic?: string;
};

export type SelectedLayer = {
  layer_key?: string;
  layer_name?: string;
  category?: string;
  role?: string;
  layer_url?: string;
  service_url?: string;
  source_status?: string;
  source_priority?: number;
  approval_status?: string;
  source_role?: string;
  coverage_geography?: string;
  source_limitation?: string;
  gap_support?: Record<string, JsonValue>;
  coverage_warnings?: string[];
  display_title?: string;
  geometry_type?: string;
  confidence_score?: number;
  match_score?: number;
  match_reasons?: string[];
  intent_reasons?: string[];
  why_selected?: string | null;
  why_not_legacy?: string | null;
  review_notes?: string[];
};

export type ClarifyingQuestion = {
  question?: string;
  reason?: string;
  examples?: string[];
  trigger?: string;
};

export type RequestIntelligence = {
  detected_intents?: string[];
  confidence_by_intent?: Record<string, number>;
  primary_intent?: string;
  secondary_intents?: string[];
  extracted_constraints?: string[];
  extracted_opportunities?: string[];
  spatial_relationships?: Array<Record<string, JsonValue>>;
  ambiguity_flags?: string[];
  clarifying_questions?: ClarifyingQuestion[];
  reasoning_summary?: string;
  unsupported_parts?: string[];
  matched_phrases_by_intent?: Record<string, string[]>;
  quality_score?: number;
  understood?: boolean;
  scenario_context?: {
    scenario_detected?: boolean;
    scenario_type?: string;
    recommended_scenario_workflow?: string | null;
    suitability_factors?: string[];
    constraint_factors?: string[];
    proxy_context?: string;
    confidence_score?: number;
    classification_reasons?: string[];
  };
  parcel_context?: {
    parcel_context_detected?: boolean;
    input_type?: string;
    parsed_identifier_count?: number;
    address_candidate_count?: number;
    owner_lookup_requested?: boolean;
    privacy_sensitive?: boolean;
    warnings?: string[];
    recommended_workflow?: string | null;
  };
  proximity_context?: {
    proximity_detected?: boolean;
    target_type?: string;
    target_layer?: string | null;
    distance_mode?: string;
    route_mode?: string;
    straight_line_supported?: boolean;
    road_route_supported?: boolean;
    clarifying_questions?: ClarifyingQuestion[];
    warnings?: string[];
  };
};

export type LearnedContext = {
  similar_patterns?: Array<Record<string, JsonValue>>;
  suggested_defaults?: Array<Record<string, JsonValue>>;
  preferred_layers?: Array<Record<string, JsonValue>>;
  avoided_layers?: Array<Record<string, JsonValue>>;
  learned_assumptions?: string[];
  missing_data_decisions?: JsonValue[];
  confidence_score?: number;
  review_note?: string;
  analysis_goal?: string;
};

export type AnalysisExecutionPlan = {
  executable?: boolean;
  operation_type?: string;
  supported_operations?: string[];
  blocked_reasons?: string[];
  warnings?: string[];
  estimated_query_counts?: Record<string, JsonValue>;
  recommended_execution_plan?: string[];
  optimized_query_plan?: Record<string, JsonValue>;
  query_strategy?: string;
  strategy_explanation?: string;
  narrowing_suggestions?: string[];
  analysis_run_id?: string | null;
  derived_outputs?: JsonValue[];
  target_layer?: Record<string, JsonValue> | null;
  geography_layer?: Record<string, JsonValue> | null;
  constraint_layer?: Record<string, JsonValue> | null;
  attribute_layer?: Record<string, JsonValue> | null;
};

export type AnalysisRun = {
  analysis_run_id?: string;
  raw_prompt?: string;
  operation_type?: string;
  status?: string;
  selected_layer_keys?: string[];
  input_counts?: Record<string, JsonValue>;
  output_count?: number;
  output_geojson_path?: string | null;
  output_folder?: string | null;
  analysis_receipt?: Record<string, JsonValue>;
  warnings?: string[];
  blocked_reasons?: string[];
  derived_layer?: PreviewLayer | Record<string, JsonValue> | null;
  created_at?: string;
};

export type AnalysisRefinementOption = {
  option_id?: string;
  option_type?: string;
  label?: string;
  description?: string;
  estimated_count?: number | null;
  expected_output?: string;
  safety_level?: "safe" | "review_needed" | "blocked" | string;
  required_user_input?: string[];
  suggested_parameters?: Record<string, JsonValue>;
  tradeoffs?: string[];
  recommended?: boolean;
};

export type AnalysisRefinementSession = {
  session_id?: string;
  source_analysis_run_id?: string;
  raw_prompt?: string;
  blocked_reason?: string;
  broad_count?: number | null;
  optimized_count?: number | null;
  safety_limit?: number;
  options?: AnalysisRefinementOption[];
  selected_option?: AnalysisRefinementOption | Record<string, JsonValue> | null;
  selected_parameters?: Record<string, JsonValue>;
  refined_plan?: Record<string, JsonValue>;
  refined_result?: Record<string, JsonValue>;
  status?: string;
  created_at?: string;
  updated_at?: string;
};

export type AnalysisReportFileLink = {
  name?: string;
  path?: string;
  url?: string;
};

export type AnalysisGroupedSummary = {
  summary_type?: string;
  status?: string;
  layer_key?: string;
  layer_name?: string;
  field_name?: string;
  field_alias?: string;
  reason?: string;
  return_geometry?: boolean;
  request_method?: string;
  rows?: Array<Record<string, JsonValue>>;
};

export type AnalysisReportData = {
  report_id?: string;
  report_title?: string;
  source_type?: string;
  source_analysis_run_id?: string | null;
  source_refinement_session_id?: string | null;
  raw_prompt?: string;
  analysis_status?: string;
  operation_type?: string;
  strategy_used?: string | null;
  broad_count?: number | null;
  optimized_count?: number | null;
  safety_limit?: number | null;
  geometry_downloaded?: boolean;
  geojson_created?: boolean;
  selected_refinement_option?: string | null;
  selected_layers?: Array<Record<string, JsonValue>>;
  definition_expressions?: Array<Record<string, JsonValue>>;
  warnings?: Record<string, string[]>;
  missing_data?: string[];
  narrowing_suggestions?: string[];
  grouped_summaries?: AnalysisGroupedSummary[];
  sections?: Array<Record<string, JsonValue>>;
  supported_export_formats?: string[];
  draft_only_disclaimer?: string;
  cfs_untouched_statement?: string;
};

export type AnalysisReportSummary = {
  report_id?: string;
  report_folder?: string;
  report_title?: string;
  report_status?: string;
  source_type?: string;
  source_analysis_run_id?: string | null;
  source_refinement_session_id?: string | null;
  summary_json?: AnalysisReportData;
  files?: AnalysisReportFileLink[];
  validation?: {
    is_valid?: boolean;
    errors?: string[];
  };
  created_at?: string;
};

export type AnalysisPlan = {
  goal?: string;
  required_layers?: string[];
  optional_layers?: string[];
  spatial_steps?: Array<Record<string, JsonValue>>;
  attribute_steps?: Array<Record<string, JsonValue>>;
  assumptions?: string[];
  blockers?: string[];
  review_questions?: ClarifyingQuestion[];
};

export type ClarificationQuestionOption = {
  value?: JsonValue;
  label?: string;
  distance?: {
    value?: number;
    unit?: string;
  };
};

export type ClarificationQuestionModel = {
  question_id?: string;
  question_text?: string;
  question_type?: "single_choice" | "multi_choice" | "text" | "number" | "distance" | "year" | "date_range";
  options?: ClarificationQuestionOption[];
  default_answer?: JsonValue;
  required?: boolean;
  related_intent?: string | null;
  related_layer_key?: string | null;
  related_filter?: string | null;
  blocking_level?: "optional" | "review_needed" | "blocks_recipe" | "blocks_publish";
  help_text?: string | null;
  suggested_default?: JsonValue;
  answer_label?: string | null;
  default_source?: string | null;
  default_confidence?: number | null;
  explanation?: string | null;
};

export type ClarificationAnswerModel = {
  question_id?: string;
  answer_value?: JsonValue;
  answer_label?: string | null;
  answered_by?: string;
  answered_at?: string;
};

export type ClarificationSession = {
  session_id?: string;
  raw_prompt?: string;
  initial_recipe?: MapRecipe;
  questions?: ClarificationQuestionModel[];
  answers?: ClarificationAnswerModel[];
  refined_prompt?: string | null;
  refined_request_context?: Record<string, JsonValue>;
  refined_recipe?: MapRecipe | null;
  changes_summary?: Record<string, JsonValue>;
  status?: string;
  created_at?: string;
  updated_at?: string;
};

export type MapRecipe = {
  map_title?: string;
  request_type?: string;
  user_intent?: string;
  parsed_request?: {
    raw_prompt?: string;
    normalized_prompt?: string;
    normalization?: Record<string, JsonValue>;
    geography_terms?: Array<{ name?: string; type?: string } | string>;
    topics?: string[];
    time_references?: string[];
    historical_year?: number | null;
  };
  request_plan?: Record<string, JsonValue>;
  request_intelligence?: RequestIntelligence;
  analysis_plan?: AnalysisPlan;
  learned_context?: LearnedContext;
  source_coverage?: SourceCoverage;
  analysis_execution?: AnalysisExecutionPlan;
  clarification?: {
    session_id?: string;
    questions?: ClarificationQuestionModel[];
    answers?: ClarificationAnswerModel[];
    applied_refinements?: Record<string, JsonValue>;
    changes_from_initial_recipe?: Record<string, JsonValue>;
    remaining_questions?: ClarificationQuestionModel[];
    unresolved_blockers?: string[];
  };
  parcel_context?: ParcelContext;
  origin_context?: OriginContext;
  proximity_context?: Record<string, JsonValue>;
  proximity_result?: ProximityResult;
  selected_layers?: SelectedLayer[];
  rejected_layers?: JsonValue[];
  filter_plan?: Record<string, JsonValue>;
  filters?: JsonValue[];
  spatial_operations?: JsonValue[];
  symbology_recommendations?: JsonValue[];
  suggested_extent?: JsonValue;
  confidence_score?: number;
  needs_review?: boolean;
  review_reasons?: string[];
  missing_data_needed?: string[];
  data_gap_notes?: JsonValue[];
  data_gap_resolution_context?: Record<string, JsonValue>;
  recipe_timing?: Record<string, number>;
};

export type ParcelIdentifier = {
  identifier_type?: string;
  value?: string;
  normalized_value?: string;
  source_text?: string | null;
  confidence?: number;
  needs_review?: boolean;
  notes?: string[];
};

export type ParcelParseResult = {
  raw_input?: string;
  input_type?: string;
  parsed_identifiers?: ParcelIdentifier[];
  address_candidates?: ParcelIdentifier[];
  parcel_intent?: boolean;
  owner_lookup_requested?: boolean;
  privacy_sensitive?: boolean;
  needs_review?: boolean;
  warnings?: string[];
};

export type ParcelMatchSummary = {
  pin14?: string | number | null;
  pin?: string | number | null;
  parcel_id?: string | number | null;
  address?: string | null;
  object_id?: string | number | null;
  source_layer_key?: string | null;
  attributes?: Record<string, JsonValue>;
  input_identifier?: ParcelIdentifier;
  needs_review?: boolean;
  count?: number;
};

export type ParcelFieldRole = {
  layer_key?: string | null;
  field_role?: string;
  field_name?: string;
  field_alias?: string | null;
  confidence_score?: number;
  notes?: string;
};

export type ParcelFieldMap = {
  layer_key?: string | null;
  layer_name?: string | null;
  layer_url?: string | null;
  object_id_field?: string | null;
  fields_by_role?: Record<string, string[]>;
  role_rows?: ParcelFieldRole[];
  geometry_supported?: boolean;
  warnings?: string[];
  stored_rows?: number;
};

export type ParcelFieldProfileResponse = {
  parcel_field_map?: ParcelFieldMap;
  address_field_map?: ParcelFieldMap;
  downloaded_geometry?: boolean;
};

export type ParcelSet = {
  parcel_set_id?: string;
  raw_input?: string;
  input_type?: string;
  parsed_identifiers?: ParcelIdentifier[];
  matched_parcels?: ParcelMatchSummary[];
  unmatched_identifiers?: ParcelIdentifier[];
  candidate_matches?: ParcelMatchSummary[];
  match_status?: "matched" | "partial" | "unmatched" | "needs_review" | string;
  source_layer_key?: string | null;
  matched_count?: number;
  warnings?: string[];
  downloaded_geometry?: boolean;
  geometry_output_path?: string | null;
  geometry_receipt?: Record<string, JsonValue>;
  geometry_fetched_at?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type ParcelContext = {
  parcel_set_id?: string | null;
  input_type?: string;
  origin_type?: string;
  request_type?: string;
  raw_input?: string;
  parsed_identifiers?: ParcelIdentifier[];
  address_candidates?: ParcelIdentifier[];
  match_status?: "matched" | "partial" | "unmatched" | "needs_review" | string;
  origin_match_status?: string;
  matched_count?: number | null;
  unmatched_identifiers?: ParcelIdentifier[];
  candidate_matches?: ParcelMatchSummary[];
  matched_parcels_summary?: ParcelMatchSummary[];
  parcel_extent?: Record<string, JsonValue>;
  parcel_buffer_extent?: Record<string, JsonValue> | null;
  can_focus_map?: boolean;
  can_fetch_geometry?: boolean;
  reason_if_not_focusable?: string | null;
  preview_status?: string;
  analysis_status?: string;
  focus_mode?: string;
  selected_parcel_geojson_path?: string | null;
  context_layers?: SelectedLayer[];
  nearby_distance?: string | null;
  geometry_output_path?: string | null;
  geometry_receipt?: Record<string, JsonValue>;
  parcel_warnings?: string[];
};

export type OriginContext = {
  origin_type?: string;
  origin_input?: string | null;
  origin_match_status?: string;
  match_status?: string;
  candidate_matches?: Array<Record<string, JsonValue>> | JsonValue[];
  related_parcel?: Record<string, JsonValue> | null;
  can_preview?: boolean;
  reason_if_not_focusable?: string | null;
  warnings?: string[];
};

export type SelectedParcelGeometryResult = {
  parcel_set_id?: string;
  match_status?: string;
  matched_count?: number;
  unmatched_identifiers?: ParcelIdentifier[];
  candidate_matches?: ParcelMatchSummary[];
  geometry_output_path?: string | null;
  receipt_path?: string | null;
  summary_path?: string | null;
  feature_count?: number | null;
  warnings?: string[];
  downloaded_geometry?: boolean;
  status?: string;
};

export type ProximityResult = {
  proximity_result_id?: string;
  proximity_request_id?: string;
  raw_prompt?: string;
  origin_input?: string;
  destination_input?: string | null;
  origin_type?: string;
  target_type?: string;
  target_layer_key?: string;
  target_layer?: Record<string, JsonValue>;
  target_name?: string | null;
  requested_target_type?: string | null;
  target_classification?: string | null;
  status?: string;
  route_status?: string;
  route_mode?: string;
  nearest_facility_method?: string | null;
  route_label?: string | null;
  route_warning?: string | null;
  route_distance_miles?: number | null;
  route_travel_time_minutes?: number | null;
  route_geometry?: string | null;
  route_confidence?: string | null;
  straight_line_distance_miles?: number | null;
  route_refinement_available?: boolean;
  route_refinement_status?: string | null;
  road_feature_count?: number | null;
  line_type?: string;
  distance_value?: number | null;
  distance_unit?: string;
  property_match_status?: string | null;
  origin_point_geojson_path?: string | null;
  origin_point_geojson_url?: string | null;
  origin_point_geojson_file_id?: string | null;
  target_feature_geojson_path?: string | null;
  target_feature_geojson_url?: string | null;
  target_feature_geojson_file_id?: string | null;
  line_geojson_path?: string | null;
  line_geojson_url?: string | null;
  line_geojson_file_id?: string | null;
  route_line_geojson_path?: string | null;
  route_line_geojson_url?: string | null;
  route_line_geojson_file_id?: string | null;
  straight_line_geojson_path?: string | null;
  straight_line_geojson_url?: string | null;
  straight_line_geojson_file_id?: string | null;
  proximity_result_geojson_path?: string | null;
  proximity_result_geojson_url?: string | null;
  proximity_result_geojson_file_id?: string | null;
  selected_parcel_geojson_path?: string | null;
  selected_parcel_geojson_url?: string | null;
  selected_parcel_geojson_file_id?: string | null;
  output_folder?: string | null;
  report_files?: Record<string, string>;
  candidate_matches?: JsonValue[];
  warnings?: string[];
  bounded_search?: Record<string, JsonValue>;
  derived_layer?: Record<string, JsonValue>;
  derived_overlays?: DerivedOverlay[];
  proximity_timing?: Record<string, JsonValue>;
  cache_hit?: boolean;
  published?: boolean;
};

export type ParcelContextSession = {
  session_id?: string;
  parcel_set_id?: string;
  raw_prompt?: string;
  context_layers?: SelectedLayer[];
  context_recipe?: MapRecipe;
  context_report?: Record<string, JsonValue>;
  warnings?: string[];
  created_at?: string;
};

export type ParcelReport = {
  report_id?: string;
  parcel_set_id?: string;
  report_folder?: string;
  report_title?: string;
  files?: ReportFileLink[];
  validation?: {
    is_valid?: boolean;
    errors?: string[];
  };
  published?: boolean;
};

export type SourceCoverageEntry = {
  layer_key?: string;
  layer_name?: string;
  display_title?: string;
  category?: string;
  source_key?: string;
  source_status?: string;
  approval_status?: string;
  source_role?: string;
  coverage_geography?: string;
  limitation?: string;
  gap_key?: string;
  status?: string;
  reason?: string;
  gap_support?: Record<string, JsonValue>;
  warnings?: string[];
  partial_sources?: SourceCoverageEntry[];
  candidate_sources?: Array<Record<string, JsonValue>>;
};

export type SourceCoverage = {
  official_sources?: SourceCoverageEntry[];
  proxy_sources?: SourceCoverageEntry[];
  limited_coverage_sources?: SourceCoverageEntry[];
  reference_sources?: SourceCoverageEntry[];
  historical_fallback_sources?: SourceCoverageEntry[];
  missing_official_sources?: SourceCoverageEntry[];
  selected_source_roles?: Record<string, SourceCoverageEntry>;
  warnings?: string[];
};

export type ScenarioFactor = {
  factor_key?: string;
  factor_label?: string;
  factor_type?: "opportunity" | "constraint" | "context" | "proxy" | string;
  layer_keys?: string[];
  suggested_weight?: number;
  reviewer_weight?: number;
  normalized_weight?: number;
  normalized_percent?: number;
  enabled?: boolean;
  direction?:
    | "higher_is_better"
    | "lower_is_better"
    | "presence_is_good"
    | "presence_is_bad"
    | "reference_only"
    | string;
  scoring_method?:
    | "attribute_score"
    | "proximity_score"
    | "intersection_penalty"
    | "reference_context"
    | "not_executable_yet"
    | string;
  needs_review?: boolean;
  notes?: string;
  reviewer_note?: string;
};

export type PlanningScenario = {
  scenario_id?: string;
  raw_prompt?: string;
  scenario_type?: string;
  scenario_title?: string;
  planning_goal?: string;
  positive_factors?: ScenarioFactor[];
  negative_factors?: ScenarioFactor[];
  required_layers?: string[];
  optional_layers?: string[];
  excluded_layers?: string[];
  selected_layers?: SelectedLayer[];
  scoring_framework?: ScenarioFactor[];
  assumptions?: string[];
  review_questions?: string[];
  source_coverage?: SourceCoverage;
  missing_data?: string[];
  proxy_warnings?: string[];
  confidence_score?: number;
  execution_status?: "scoring_plan_only" | "executable_if_refined" | "blocked_by_count" | "executed_small_sample" | string;
  official_use_disclaimer?: string;
  status?: string;
  created_at?: string;
  map_recipe?: MapRecipe;
  scenario_json?: PlanningScenario;
};

export type ScenarioReport = {
  scenario_id?: string;
  report_folder?: string;
  report_title?: string;
  files?: AnalysisReportFileLink[];
  validation?: {
    is_valid?: boolean;
    errors?: string[];
  };
};

export type ScenarioVariant = {
  variant_id?: string;
  source_scenario_id?: string;
  scenario_type?: string;
  scenario_title?: string;
  variant_name?: string;
  variant_description?: string;
  factor_weights?: ScenarioFactor[];
  enabled_factors?: string[];
  disabled_factors?: string[];
  normalized_weights?: Array<Record<string, JsonValue>>;
  weight_overrides?: Record<string, number>;
  direction_overrides?: Record<string, string>;
  reviewer_assumptions?: string[];
  selected_layer_keys?: string[];
  required_layers?: string[];
  optional_layers?: string[];
  source_coverage?: SourceCoverage;
  missing_data?: string[];
  changes_from_base?: Record<string, JsonValue>;
  safety_warnings?: string[];
  proxy_warnings?: string[];
  missing_data_warnings?: string[];
  blocked_reasons?: string[];
  safety_level?: string;
  is_safe?: boolean;
  official_use_disclaimer?: string;
  created_at?: string;
  updated_at?: string;
  variant_json?: ScenarioVariant;
};

export type ScenarioComparison = {
  comparison_id?: string;
  scenario_ids?: string[];
  variant_ids?: string[];
  items?: Array<Record<string, JsonValue>>;
  factor_differences?: Array<Record<string, JsonValue>>;
  layer_differences?: Record<string, JsonValue>;
  source_coverage_differences?: Record<string, JsonValue>;
  missing_data_differences?: Record<string, string[]>;
  review_question_differences?: Record<string, string[]>;
  recommended_review_focus?: string[];
  created_at?: string;
};

export type ScenarioToRecipeResult = {
  scenario_id?: string;
  variant_id?: string | null;
  recipe?: MapRecipe;
  scenario_context?: Record<string, JsonValue>;
  warnings?: string[];
  published?: boolean;
};

export type ApprovedPattern = {
  pattern_key?: string;
  source_approved_packet?: string;
  raw_prompt?: string;
  normalized_prompt?: string;
  primary_intent?: string;
  secondary_intents?: string[];
  geographies?: JsonValue[];
  topics?: string[];
  selected_layer_keys?: string[];
  rejected_layer_keys?: string[];
  preferred_layer_keys?: string[];
  avoided_layer_keys?: string[];
  spatial_operations?: JsonValue[];
  filter_plan?: Record<string, JsonValue>;
  clarification_answers?: JsonValue[];
  reviewer_notes?: JsonValue[];
  accepted_assumptions?: string[];
  warning_resolutions?: Record<string, JsonValue>;
  missing_data_decisions?: JsonValue[];
  confidence_score?: number;
  approval_decision?: string;
  final_publish_ready?: boolean;
  usage_count?: number;
  is_active?: boolean;
  similarity_score?: number;
  created_at?: string;
  updated_at?: string;
};

export type ClarificationDefault = {
  default_key?: string;
  intent?: string;
  topic?: string;
  question_type?: string;
  question_text?: string;
  default_answer?: JsonValue;
  answer_label?: string;
  source_pattern_key?: string;
  confidence_score?: number;
  usage_count?: number;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type FeedbackLogRow = {
  id?: number;
  raw_prompt?: string;
  feedback_type?: string;
  feedback_json?: JsonValue;
  source_packet_path?: string | null;
  created_at?: string;
};

export type PacketSummary = {
  packet_id?: string;
  packet_type?: string;
  packet_path?: string;
  webmap_path?: string;
  recipe_path?: string | null;
  map_title?: string;
  updated_at?: string;
  preview_url?: string;
  final_publish_ready?: boolean | null;
  approval_block_reasons?: string[];
  latest_publish_receipt?: {
    exists?: boolean;
    status?: string | null;
    published?: boolean | null;
    created_item?: boolean | null;
    real_publish_attempted?: boolean | null;
  };
  latest_smoke_test_receipt?: {
    exists?: boolean;
    dry_run?: boolean | null;
    item_created?: boolean | null;
    blocked?: boolean | null;
  };
};

export type PacketsResponse = {
  latest?: PacketSummary | null;
  review_packets?: PacketSummary[];
  adjusted_packets?: PacketSummary[];
  approved_packets?: PacketSummary[];
  counts?: {
    review_packets?: number;
    adjusted_packets?: number;
    approved_packets?: number;
  };
};

export type ReportFileLink = {
  name?: string;
  path?: string;
  url?: string;
};

export type ReportSummary = {
  report_id?: string;
  report_path?: string;
  report_title?: string;
  generated_map_title?: string;
  workflow_status?: string;
  packet_type?: string;
  packet_path?: string;
  source_packet_path?: string;
  updated_at?: string;
  files?: Record<string, string> | ReportFileLink[];
  validation?: {
    is_valid?: boolean;
    errors?: string[];
    warnings?: string[];
  };
};

export type ReportData = {
  report_title?: string;
  original_prompt?: string;
  generated_map_title?: string;
  workflow_status?: string;
  packet_type?: string;
  packet_path?: string;
  selected_layers?: Array<Record<string, JsonValue>>;
  warnings?: Record<string, string[]>;
  missing_data?: string[];
  data_gaps?: JsonValue[];
  approval?: Record<string, JsonValue>;
  final_publish_ready?: boolean | null;
  dry_run_publish_receipt?: Record<string, JsonValue>;
  portal_smoke_test_receipt?: Record<string, JsonValue>;
  draft_only_disclaimer?: string;
};

export type ReportDetail = {
  report_id?: string;
  report_path?: string;
  report_data?: ReportData;
  manifest?: Record<string, JsonValue>;
  files?: Record<string, string> | ReportFileLink[];
  validation?: {
    is_valid?: boolean;
    errors?: string[];
    warnings?: string[];
  };
};

export type GenerateReportResponse = ReportSummary & {
  files?: ReportFileLink[];
};

export type PreviewLayer = {
  id?: string;
  title?: string;
  layer_key?: string;
  category?: string;
  role?: string;
  source_status?: string;
  source_priority?: number;
  confidence_score?: number;
  url?: string;
  layer_url?: string;
  service_url?: string;
  layer_id?: number | null;
  preview_type?: string;
  visibility?: boolean;
  default_visible?: boolean;
  is_context_layer?: boolean;
  opacity?: number;
  definition_expression?: string | null;
  drawing_info?: Record<string, JsonValue> | null;
  legend_label?: string;
  cartography_role?: string;
  map_role?: string;
  layer_role?: string;
  clipped_to_aoi?: boolean;
  aoi_filter_applied?: boolean;
  aoi_summary?: string;
  max_feature_count?: number | null;
  simplification_applied?: boolean;
  diagnostics_only?: boolean;
  fallback_used?: boolean;
  review_warnings?: string[];
  derived_local_analysis?: boolean;
  local_output?: boolean;
  analysis_run_id?: string | null;
  display_role?: string;
  draw_order?: number;
};

export type DerivedOverlay = {
  id?: string;
  title?: string;
  kind?: "source_layer" | "generated_graphic" | "derived_overlay" | string;
  layer_type?: "arcgis_feature_layer" | "arcgis_map_image_layer" | "graphics_overlay" | "route_overlay" | "point_marker" | string;
  type?: "geojson" | string;
  url?: string;
  path?: string;
  file_id?: string | null;
  geojson?: Record<string, JsonValue> | null;
  feature_collection?: Record<string, JsonValue> | null;
  feature?: Record<string, JsonValue> | null;
  geometry?: Record<string, JsonValue> | null;
  role?: string;
  map_role?: string;
  cartography_role?: string;
  opacity?: number;
  drawing_info?: Record<string, JsonValue> | null;
  geometry_type?: "point" | "line" | "polygon" | string;
  visible?: boolean;
  local_output?: boolean;
  source_status?: string;
  symbol?: Record<string, JsonValue>;
  symbol_key?: string;
  geometry_role?: string;
  route_mode?: string | null;
  route_label?: string | null;
  route_warning?: string | null;
  facility_type?: string | null;
  facility_display_name?: string | null;
  default_visible?: boolean;
  is_context_layer?: boolean;
  feature_count?: number;
  output_count?: number;
  extent?: Record<string, JsonValue> | null;
  legend_label?: string;
  analysis_type?: string;
  floodplain_type?: string;
};

export type PreviewConfig = {
  map_title?: string;
  original_prompt?: string;
  basemap?: string;
  initial_extent?: Record<string, JsonValue>;
  operational_layers?: PreviewLayer[];
  context_layers?: PreviewLayer[];
  warnings?: Record<string, JsonValue> | string[];
  missing_data?: string[];
  data_gaps?: JsonValue[];
  packet_id?: string;
  packet_path?: string;
  webmap_path?: string;
  draft_status?: string;
  parcel_context?: ParcelContext;
  preview_status?: string;
  focus_mode?: string;
  can_focus_map?: boolean | null;
  parcel_preview_blocked?: boolean;
  derived_overlays?: DerivedOverlay[];
  proximity_result?: ProximityResult | Record<string, JsonValue>;
  focus_extent?: Record<string, JsonValue>;
  aoi?: Record<string, JsonValue>;
  display_complexity?: Record<string, JsonValue>;
  origin_summary?: Record<string, JsonValue>;
  target_summary?: Record<string, JsonValue>;
  distance_summary?: Record<string, JsonValue>;
  parcel_resolution_summary?: Record<string, JsonValue>;
  floodplain_screening?: Record<string, JsonValue>;
  map_layout?: MapLayout;
  visible_feature_summary?: Array<Record<string, JsonValue>>;
  visible_feature_total?: number | null;
  visible_map_qa?: Record<string, JsonValue>;
  preview_only?: boolean;
};

export type MapLayout = {
  title?: string;
  subtitle?: string;
  legend_items?: Array<Record<string, JsonValue>>;
  scale_bar_enabled?: boolean;
  scale_bar_position?: string;
  scale_bar_width_percent?: number;
  scale_bar_style?: string;
  north_arrow_enabled?: boolean;
  disclaimer?: string;
  route_mode_label?: string;
  print_ready?: boolean;
};

export type WorkflowRunResponse = {
  workflow_id?: string;
  recipe_id?: string;
  prompt?: string;
  recipe?: MapRecipe;
  parcel_context?: ParcelContext;
  selected_layers?: SelectedLayer[];
  warnings?: string[];
  missing_data_needed?: string[];
  packet_id?: string | null;
  preview_url?: string | null;
  can_preview?: boolean;
  can_analyze?: boolean;
  can_report?: boolean;
  next_recommended_action?: string;
  analysis_not_needed?: boolean;
  draft_only?: boolean;
  published?: boolean;
};

export type TableField = {
  layer_key?: string;
  name?: string;
  alias?: string;
  source?: string;
};

export type TableRecipe = {
  table_request_id?: string;
  table_title?: string;
  raw_prompt?: string;
  table_intent?: string;
  source_layers?: Array<Record<string, JsonValue>>;
  selected_fields?: TableField[];
  filters?: Array<Record<string, JsonValue>>;
  where_clauses?: Array<Record<string, JsonValue>>;
  geography_filter?: string | null;
  time_filter?: string | null;
  historical_year?: number | null;
  output_formats?: string[];
  estimated_count?: number | null;
  safety_status?: string;
  missing_data_needed?: string[];
  warnings?: string[];
  preview_rows?: Array<Record<string, JsonValue>>;
  export_ready?: boolean;
  blocked_reasons?: string[];
  refinement_suggestions?: string[];
  query_options?: Record<string, JsonValue>;
  classification?: Record<string, JsonValue>;
};

export type TablePlanResponse = {
  table_recipe?: TableRecipe;
  table_context?: Record<string, JsonValue>;
};

export type TablePreviewResponse = {
  table_request_id?: string;
  table_recipe?: TableRecipe;
  preview_rows?: Array<Record<string, JsonValue>>;
  rows?: Array<Record<string, JsonValue>>;
  row_count?: number;
  returnGeometry?: boolean;
  query_options?: Record<string, JsonValue>;
};

export type TableExportResponse = TablePreviewResponse & {
  export_id?: string;
  export_ready?: boolean;
  safety_status?: string;
  blocked_reasons?: string[];
  output_folder?: string;
  files?: ReportFileLink[];
  output_formats?: string[];
  draft_only?: boolean;
  published?: boolean;
};

export type ComposerLayerAdjustment = {
  layer_key?: string;
  title?: string;
  visibility?: boolean;
  opacity?: number;
  role?: string;
  showLegend?: boolean;
  remove_layer?: boolean;
  definition_expression?: string;
  is_derived?: boolean;
  line_thickness?: number;
  line_style?: "solid" | "dashed" | string;
};

export type ReportSectionConfig = {
  include_map_summary?: boolean;
  include_layer_table?: boolean;
  include_warnings?: boolean;
  include_source_notes?: boolean;
  include_proximity_summary?: boolean;
  include_parcel_summary?: boolean;
  include_statistics?: boolean;
  include_permit_summary?: boolean;
  include_planning_summary?: boolean;
  include_development_proxy_summary?: boolean;
  include_table_preview?: boolean;
  include_table_export_summary?: boolean;
};

export type ExportMode = "map_sheet" | "map_exhibit_only" | "map_plus_summary" | "map_summary" | "full_report" | string;

export type PrintExportOptions = {
  export_mode?: ExportMode;
  include_map_summary?: boolean;
  include_key_findings?: boolean;
  include_layer_table?: boolean;
  include_warnings?: boolean;
  include_source_notes?: boolean;
  include_statistics?: boolean;
  include_parcel_summary?: boolean;
  include_proximity_summary?: boolean;
  include_permit_summary?: boolean;
  include_planning_summary?: boolean;
  include_development_proxy_summary?: boolean;
  include_appendix?: boolean;
  include_draft_disclaimer?: boolean;
  sheet_size_preset?: string;
  sheet_width?: number;
  sheet_height?: number;
  sheet_units?: "inches" | string;
  sheet_orientation?: "portrait" | "landscape" | string;
  sheet_dpi?: 150 | 300 | number;
  sheet_margin?: "none" | "narrow" | "standard" | string;
  map_frame_fill?: "fit_width" | "fit_page" | "fixed_scale" | string;
  scale_mode?: "fit_extent" | "fixed_scale" | string;
  fixed_scale?: string;
  custom_scale?: number;
  include_title?: boolean;
  include_subtitle?: boolean;
  include_legend?: boolean;
  include_scale_bar?: boolean;
  include_north_arrow?: boolean;
  include_source_note?: boolean;
  include_draft_watermark?: boolean;
  include_scope_note?: boolean;
  include_real_publish_note?: boolean;
  preserve_extent?: boolean;
  preserve_layer_state?: boolean;
  wysiwyg?: boolean;
};

export type ReportStatistics = {
  selected_visible_layer_count?: number;
  hidden_layer_count?: number;
  derived_overlay_count?: number;
  warning_count?: number;
  missing_data_count?: number;
  source_coverage_counts?: Record<string, number>;
  proximity?: Record<string, JsonValue>;
  parcel?: Record<string, JsonValue>;
  table?: Record<string, JsonValue>;
  permit_summary?: Record<string, JsonValue>;
  planning_cases_summary?: Record<string, JsonValue>;
  development_proxy_summary?: Record<string, JsonValue>;
};

export type ComposerMapState = {
  composer_session_id?: string;
  map_title?: string;
  map_subtitle?: string;
  raw_prompt?: string;
  request_type?: string;
  preview_config?: PreviewConfig;
  map_extent?: Record<string, JsonValue> | null;
  basemap?: string;
  visible_layers?: Array<Record<string, JsonValue>>;
  hidden_layers?: Array<Record<string, JsonValue>>;
  layer_order?: string[];
  layer_opacity?: Record<string, number>;
  layer_titles?: Record<string, string>;
  layer_roles?: Record<string, string>;
  layer_symbology?: Record<string, Record<string, JsonValue>>;
  derived_overlays?: DerivedOverlay[];
  legend_items?: Array<Record<string, JsonValue>>;
  scale_bar_config?: Record<string, JsonValue>;
  north_arrow_config?: Record<string, JsonValue>;
  route_summary?: Record<string, JsonValue>;
  proximity_summary?: ProximityResult | Record<string, JsonValue>;
  parcel_context?: ParcelContext | Record<string, JsonValue>;
  table_context?: {
    table_requested?: boolean;
    table_recipe?: TableRecipe;
    preview_rows?: Array<Record<string, JsonValue>>;
    export_status?: string;
    export_links?: ReportFileLink[];
    warnings?: string[];
  } | null;
  warnings?: string[];
  missing_data?: string[];
  reviewer_notes?: string;
  adjusted_state_applied?: boolean;
  current_center?: Record<string, JsonValue> | null;
  current_zoom?: number | null;
  current_scale?: number | null;
  current_rotation?: number | null;
  export_mode?: ExportMode;
  export_options?: PrintExportOptions;
  print_export_options?: PrintExportOptions;
  report_section_config?: ReportSectionConfig;
  report_statistics?: ReportStatistics;
  report_sections?: Record<string, JsonValue>;
  updated_at?: string;
};

export type ComposerAdjustPayload = {
  composer_session_id: string;
  map_title?: string;
  map_description?: string;
  notes?: string;
  layer_order?: string[];
  layers?: ComposerLayerAdjustment[];
  active_map_extent?: Record<string, JsonValue>;
  report_config?: ReportSectionConfig;
  export_mode?: ExportMode;
  export_options?: PrintExportOptions;
  map_state?: ComposerMapState;
};

export type ComposerExportPayload = ComposerAdjustPayload;

export type ComposerExport = {
  report_id?: string;
  report_path?: string;
  report_title?: string;
  files?: ReportFileLink[];
  validation?: {
    is_valid?: boolean;
    errors?: string[];
    warnings?: string[];
  };
};

export type ExhibitSummary = {
  exhibit_id?: string;
  exhibit_title?: string;
  exhibit_type?: string;
  created_at?: string;
  source_prompt?: string;
  exhibit_folder?: string;
  files?: ReportFileLink[];
  draft_only?: boolean;
  published?: boolean;
};

export type ExhibitPackage = ExhibitSummary & {
  validation?: {
    is_valid?: boolean;
    errors?: string[];
    warnings?: string[];
  };
  summary?: Record<string, JsonValue>;
  exhibit_data?: Record<string, JsonValue>;
  manifest?: Record<string, JsonValue>;
};

export type ComposerResponse = {
  composer_session_id?: string;
  prompt?: string;
  raw_prompt?: string;
  map_title?: string;
  request_type?: string;
  origin_type?: string;
  origin_match_status?: string;
  origin_candidates?: Array<Record<string, JsonValue>> | JsonValue[];
  related_parcel?: Record<string, JsonValue> | null;
  proximity_result?: ProximityResult | null;
  analysis_type?: string | null;
  spatial_relationship?: string | null;
  result_layer_role?: string | null;
  affected_feature_count?: number | null;
  floodplain_type?: string | null;
  aoi_name?: string | null;
  aoi_type?: string | null;
  floodplain_screening?: Record<string, JsonValue> | null;
  route_refinement_available?: boolean;
  route_refinement_status?: string | null;
  recipe?: MapRecipe;
  webmap_json?: Record<string, JsonValue>;
  preview_config?: PreviewConfig | null;
  map_layout?: MapLayout | null;
  request_plan?: Record<string, JsonValue> | null;
  visible_feature_summary?: Array<Record<string, JsonValue>>;
  composer_map_state?: ComposerMapState | null;
  composer_map_state_persisted?: boolean;
  selected_layers?: SelectedLayer[];
  warnings?: string[];
  missing_data?: string[];
  parcel_context?: ParcelContext;
  can_preview?: boolean;
  can_analyze?: boolean;
  can_report?: boolean;
  preview_blockers?: string[];
  next_action?: string;
  simple_steps?: Array<{ step?: string; status?: string }>;
  composer_timing?: Record<string, JsonValue>;
  debug_details?: Record<string, JsonValue>;
  review_packet_id?: string | null;
  review_packet_path?: string | null;
  adjusted_packet_id?: string | null;
  adjusted_packet_path?: string | null;
  packet_id?: string | null;
  packet_path?: string | null;
  preview_url?: string | null;
  webmap_path?: string | null;
  composer_session_path?: string | null;
  applied_adjustments?: Record<string, JsonValue>;
  table_context?: {
    table_requested?: boolean;
    table_recipe?: TableRecipe;
    preview_rows?: Array<Record<string, JsonValue>>;
    export_status?: string;
    export_links?: ReportFileLink[];
    warnings?: string[];
  } | null;
  export?: ComposerExport | null;
  exhibit?: ExhibitPackage | null;
  report_sections?: Record<string, JsonValue> | null;
  report_statistics?: ReportStatistics | null;
  draft_only?: boolean;
  published?: boolean;
  created_at?: string;
};

export type AddressResolveResponse = {
  address?: string;
  normalized_address?: string;
  parsed_address_parts?: Record<string, JsonValue>;
  match_status?: string;
  candidates?: Array<Record<string, JsonValue>>;
  matched_address_candidates?: Array<Record<string, JsonValue>>;
  matched_parcel_candidates?: Array<Record<string, JsonValue>>;
  related_parcel?: {
    pin?: string | null;
    pin14?: string | null;
    parcel_number?: string | null;
  };
  warnings?: string[];
};

export type DataGap = {
  gap_key?: string;
  topic?: string;
  missing_layer_type?: string;
  reason?: string;
  suggested_source?: string | null;
  status?: string;
  created_at?: string;
  updated_at?: string;
};

export type ExternalSource = {
  source_key?: string;
  source_name?: string;
  source_type?: string;
  base_url?: string | null;
  layer_url?: string | null;
  priority?: number;
  approval_status?: "approved" | "candidate" | "needs_review" | string;
  source_status?: "active" | "proxy" | "reference" | "legacy" | string;
  categories?: string[];
  intended_gaps?: string[];
  inspected_metadata?: Record<string, JsonValue>;
  limitations?: string;
  is_active?: boolean;
  created_at?: string;
  updated_at?: string;
};

export type DiscoveredSourceRecord = {
  source_key?: string;
  source_name?: string;
  source_type?: string;
  base_url?: string | null;
  layer_url?: string | null;
  approval_status?: string;
  source_status?: string;
  categories?: string[];
  intended_gaps?: string[];
  notes?: string;
  limitations?: string;
};

export type SourceDiscoveryResult = {
  discovered_at?: string;
  roots?: string[];
  keywords?: string[];
  services_discovered?: number;
  services_inspected?: number;
  candidate_layers?: JsonValue[];
  candidate_records?: DiscoveredSourceRecord[];
  candidate_count?: number;
  failures?: JsonValue[];
  report_path?: string;
  downloaded_geometry?: boolean;
};

export type DataGapCandidate = ExternalSource & {
  gap_key?: string;
  source_score?: number;
  metadata_summary?: Record<string, JsonValue>;
  classified_limitations?: string[];
  resolution_recommendation?: string;
};

export type HistoryRow = {
  id?: number;
  raw_prompt?: string;
  workflow_step?: string;
  map_title?: string;
  status?: string;
  packet_path?: string | null;
  adjusted_packet_path?: string | null;
  created_at?: string;
  notes?: JsonValue;
};

export type ApiError = {
  error: string;
};
