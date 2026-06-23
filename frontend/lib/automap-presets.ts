export type AutoMapPreset = {
  id: string;
  title: string;
  short_description: string;
  prompt: string;
  category: string;
  capability_type: string;
  expected_request_type: string;
  expected_output: string;
  expected_output_type: string;
  status: "Live working" | "Partial / draft" | "Coming soon" | "Data limited";
  required_layers: string[];
  expected_behavior: string[];
  fallback_behavior: string;
  is_recruiter_safe: boolean;
  is_cabarrus_scoped: boolean;
};

export const automapPresets: AutoMapPreset[] = [
  {
    id: "nearest-fire-station-route",
    title: "Nearest Fire Station Route",
    short_description: "Address match, nearest fire station, and road-network route draft.",
    prompt: "make a map of my address 793 bartram ave and include nearest line to the nearest fire station",
    category: "Proximity",
    capability_type: "address matching + nearest facility + road-network route",
    expected_request_type: "proximity",
    expected_output: "Road-following draft map when centerlines are available.",
    expected_output_type: "Map + road route",
    status: "Live working",
    required_layers: ["Addresses", "Fire and EMS Stations", "Street Centerlines"],
    expected_behavior: [
      "origin_match_status=matched",
      "route_mode=road_network when available",
      "nearest_facility_method=road_distance",
      "solid road-following route",
    ],
    fallback_behavior: "Show straight-line fallback only when road routing is unavailable.",
    is_recruiter_safe: true,
    is_cabarrus_scoped: true,
  },
  {
    id: "floodplain-parcel-screening",
    title: "Floodplain Parcel Screening",
    short_description: "Screen Concord parcels against the 100-year floodplain.",
    prompt: "show parcels in Concord that are in the 100-year floodplain",
    category: "Parcel Screening",
    capability_type: "parcel + flood overlay + municipal filter",
    expected_request_type: "map",
    expected_output: "Parcel/flood map preview with summary count when available.",
    expected_output_type: "Map preview",
    status: "Live working",
    required_layers: ["Tax Parcels", "100-year Floodplain", "Municipal Districts"],
    expected_behavior: ["parcels layer", "100-year floodplain layer", "Concord geography/filter"],
    fallback_behavior: "Explain missing flood or parcel data without inventing counts.",
    is_recruiter_safe: true,
    is_cabarrus_scoped: true,
  },
  {
    id: "commercial-zoning-context",
    title: "Commercial Zoning Context",
    short_description: "Show commercial zoning with nearby major roads around Concord.",
    prompt: "show commercial zoning around Concord with nearby major roads",
    category: "Zoning",
    capability_type: "zoning + transportation context",
    expected_request_type: "map",
    expected_output: "Zoning context map with transportation reference layers.",
    expected_output_type: "Map preview",
    status: "Live working",
    required_layers: ["Zoning", "Major Roads", "Municipal Districts"],
    expected_behavior: ["zoning layer", "commercial zoning filter if possible", "roads context", "clear legend"],
    fallback_behavior: "Show zoning context and explain if commercial code filtering needs review.",
    is_recruiter_safe: true,
    is_cabarrus_scoped: true,
  },
  {
    id: "parcel-table-request",
    title: "Parcel Table Request",
    short_description: "Plan a bounded parcel attribute table and safe export.",
    prompt: "give me a table of parcels in Cabarrus County with parcel ID, acreage, municipality, and zoning",
    category: "Tables",
    capability_type: "natural-language table generation",
    expected_request_type: "table_request",
    expected_output: "Table preview with field selection and export safety limits.",
    expected_output_type: "Table preview",
    status: "Partial / draft",
    required_layers: ["Tax Parcels", "Zoning"],
    expected_behavior: ["table_request", "column selection", "safe row limits", "CSV/export option if available"],
    fallback_behavior: "Preview limited rows and ask for refinement if row count is too high.",
    is_recruiter_safe: true,
    is_cabarrus_scoped: true,
  },
  {
    id: "recent-development-activity",
    title: "Recent Development Activity",
    short_description: "Map permit and planning activity near Kannapolis with honest data gaps.",
    prompt: "map recent permits and planning cases near Kannapolis",
    category: "Planning Signals",
    capability_type: "development pipeline/proxy layer selection",
    expected_request_type: "map",
    expected_output: "Map preview or clear missing-data explanation.",
    expected_output_type: "Data-gap aware map",
    status: "Data limited",
    required_layers: ["Permits", "Planning Cases", "Municipal Districts"],
    expected_behavior: ["permits/planning cases if available", "proxy/data limitation note", "no invented data"],
    fallback_behavior: "Explain unresolved permit/planning sources instead of pretending data exists.",
    is_recruiter_safe: true,
    is_cabarrus_scoped: true,
  },
  {
    id: "commercial-growth-opportunity",
    title: "Commercial Growth Opportunity",
    short_description: "Draft a suitability view near high-traffic roads while avoiding floodplain.",
    prompt: "map commercial growth opportunities near high traffic roads but avoid floodplain",
    category: "Scenario",
    capability_type: "multi-constraint suitability / scenario logic",
    expected_request_type: "scenario",
    expected_output: "Draft suitability map or reviewable scenario recipe.",
    expected_output_type: "Scenario draft",
    status: "Partial / draft",
    required_layers: ["Roads or AADT", "Commercial Zoning", "Floodplain"],
    expected_behavior: ["transportation context", "commercial context", "floodplain avoidance", "draft suitability language"],
    fallback_behavior: "Show a draft suitability framework and name missing proxy layers honestly.",
    is_recruiter_safe: true,
    is_cabarrus_scoped: true,
  },
  {
    id: "historical-parcel-zoning-lookup",
    title: "Historical Parcel/Zoning Lookup",
    short_description: "Find 2014 parcel and zoning archive layers without using current data as history.",
    prompt: "show 2014 parcels and zoning in Cabarrus County",
    category: "Historical",
    capability_type: "historical layer discovery and time-specific mapping",
    expected_request_type: "historical_comparison",
    expected_output: "Historical layer map or honest unavailable-source explanation.",
    expected_output_type: "Historical lookup",
    status: "Data limited",
    required_layers: ["2014 Tax Parcels", "2014 Zoning"],
    expected_behavior: ["historical layers if available", "time period clearly shown", "no current layer pretending to be historical"],
    fallback_behavior: "Explain when historical parcel/zoning layers are unavailable.",
    is_recruiter_safe: true,
    is_cabarrus_scoped: true,
  },
];

export function presetPrompts(): string[] {
  return automapPresets.map((preset) => preset.prompt);
}

export function presetForPrompt(prompt: string): AutoMapPreset | undefined {
  const normalized = prompt.trim().toLowerCase();
  return automapPresets.find((preset) => preset.prompt.trim().toLowerCase() === normalized);
}
