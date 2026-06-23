export const navigationItems = [
  { href: "/map-composer", label: "Map Composer", group: "Main" },
  { href: "/parcel-workspace", label: "Parcel Workspace", group: "Main" },
  { href: "/proximity", label: "Proximity", group: "Main" },
  { href: "/tables", label: "Tables", group: "Main" },
  { href: "/scenarios", label: "Scenarios", group: "Main" },
  { href: "/analysis", label: "Analysis", group: "Main" },
  { href: "/reports", label: "Reports", group: "Main" },
  { href: "/layer-catalog", label: "Layer Catalog", group: "Support" },
  { href: "/data-gaps", label: "Data Gaps", group: "Support" },
  { href: "/external-sources", label: "External Sources", group: "Support" },
  { href: "/history", label: "History", group: "Support" },
  { href: "/system-status", label: "System Status", group: "Support" },
];

export const samplePrompts = [
  "make a map of my address 793 bartram ave and include nearest line to the nearest fire station",
  "show parcels in Concord that are in the 100-year floodplain",
  "show commercial zoning around Concord",
  "map recent permits and planning cases near Kannapolis",
  "give me a table of parcels in Cabarrus County",
];

export const workflowSteps = [
  { href: "/map-composer", label: "Map Composer", description: "Request, preview, adjust, and print/export." },
  { href: "/parcel-workspace", label: "Parcel Workspace", description: "Parcel IDs, PINs, addresses, and context maps." },
  { href: "/proximity", label: "Proximity", description: "Nearest facilities and straight-line route drafts." },
  { href: "/tables", label: "Tables", description: "Bounded table previews and CSV/JSON exports." },
  { href: "/scenarios", label: "Scenarios", description: "Reviewable suitability frameworks." },
  { href: "/analysis", label: "Analysis", description: "Safe bounded local GeoJSON execution." },
  { href: "/reports", label: "Reports", description: "Local draft reports and exports." },
];
