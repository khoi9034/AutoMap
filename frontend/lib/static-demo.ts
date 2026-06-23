import type { ComposerResponse } from "@/types/automap";

export const STATIC_DEMO_PROMPT =
  "make a map of my address 793 bartram ave and include nearest line to the nearest fire station";

export const STATIC_DEMO_TITLE = "Nearest Fire Station from 793 Bartram Ave";
export const STATIC_DEMO_SCOPE = "Cabarrus County, NC";

export const staticDemoComposerResponse: ComposerResponse = {
  composer_session_id: "static-demo-793-bartram-fire-station",
  prompt: STATIC_DEMO_PROMPT,
  raw_prompt: STATIC_DEMO_PROMPT,
  map_title: STATIC_DEMO_TITLE,
  request_type: "proximity",
  origin_type: "address",
  origin_match_status: "matched",
  can_preview: true,
  can_report: true,
  draft_only: true,
  published: false,
  route_refinement_available: true,
  warnings: [
    "Static demo fallback. Live backend unavailable or warming up.",
    "Scope: Cabarrus County, NC.",
    "Publishing is disabled for safety.",
    "Route and distance details are for portfolio demonstration only.",
  ],
  preview_blockers: [],
  next_action: "Retry the live backend request when Render finishes waking up.",
  map_layout: {
    title: STATIC_DEMO_TITLE,
    subtitle: "Static demo fallback. Live backend unavailable or warming up.",
    route_mode_label: "Nearest facility proximity draft",
    disclaimer: "Static demo fallback. No ArcGIS item was published.",
    print_ready: false,
  },
  preview_config: {
    map_title: STATIC_DEMO_TITLE,
    original_prompt: STATIC_DEMO_PROMPT,
    basemap: "streets-vector",
    preview_status: "static_demo_fallback",
    can_focus_map: true,
    preview_only: true,
    warnings: ["Static demo fallback. Live backend unavailable or warming up.", "Scope: Cabarrus County, NC."],
    derived_overlays: [],
  },
  composer_timing: {
    total_ms: 0,
    static_demo: true,
  },
};

export const staticDemoHighlights = [
  "Scope: Cabarrus County, NC.",
  "Address prompt is parsed as an address origin.",
  "Nearest fire station workflow is selected.",
  "Preview/export remain draft-only with real publishing disabled.",
  "Static fallback is shown only when the live backend is cold, slow, or unavailable.",
];
