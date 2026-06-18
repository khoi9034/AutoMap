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
  "Show parcels in Concord that are in the 100-year floodplain.",
  "Show commercial zoning around Concord.",
  "Show school districts for parcels in Harrisburg.",
  "Show 2014 parcels and zoning.",
  "Give me a table of parcels in Concord.",
  "Map recent permits and planning cases near Kannapolis.",
  "Map commercial growth opportunities near high traffic roads but avoid floodplain.",
  "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.",
  "How far is parcel 5528-12-3456 from the nearest school?",
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
