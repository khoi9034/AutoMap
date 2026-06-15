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
  match_reasons?: string[];
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

export type PacketSummary = {
  packet_id?: string;
  packet_type?: string;
  packet_path?: string;
  webmap_path?: string;
  recipe_path?: string | null;
  map_title?: string;
  updated_at?: string;
  preview_url?: string;
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

export type PreviewLayer = {
  id?: string;
  title?: string;
  layer_key?: string;
  role?: string;
  source_status?: string;
  source_priority?: number;
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
