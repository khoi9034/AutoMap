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
  request_history_count?: number;
  approval_history_count?: number;
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
