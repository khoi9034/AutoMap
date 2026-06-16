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
  user_intent?: string;
  parsed_request?: {
    raw_prompt?: string;
    geography_terms?: Array<{ name?: string; type?: string } | string>;
    topics?: string[];
    time_references?: string[];
    historical_year?: number | null;
  };
  request_intelligence?: RequestIntelligence;
  analysis_plan?: AnalysisPlan;
  learned_context?: LearnedContext;
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
  opacity?: number;
  definition_expression?: string | null;
  review_warnings?: string[];
  derived_local_analysis?: boolean;
  analysis_run_id?: string | null;
};

export type PreviewConfig = {
  map_title?: string;
  original_prompt?: string;
  operational_layers?: PreviewLayer[];
  warnings?: Record<string, JsonValue>;
  missing_data?: string[];
  data_gaps?: JsonValue[];
  packet_id?: string;
  packet_path?: string;
  webmap_path?: string;
  draft_status?: string;
  preview_only?: boolean;
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
