export const navigationItems = [
  { href: "/map-composer", label: "Map Composer", group: "Main" },
  { href: "/parcel-workspace", label: "Parcel Workspace", group: "Main" },
  { href: "/proximity", label: "Proximity", group: "Main" },
  { href: "/scenarios", label: "Scenarios", group: "Main" },
  { href: "/analysis", label: "Analysis", group: "Main" },
  { href: "/reports", label: "Reports", group: "Main" },
  { href: "/recipe-review", label: "Recipe Review", group: "Advanced" },
  { href: "/map-preview", label: "Map Preview", group: "Advanced" },
  { href: "/adjustments", label: "Adjustments", group: "Advanced" },
  { href: "/approval", label: "Approval", group: "Advanced" },
  { href: "/publish-center", label: "Publish Center", group: "Advanced" },
  { href: "/learning", label: "Learning", group: "Advanced" },
  { href: "/layer-catalog", label: "Layer Catalog", group: "Advanced" },
  { href: "/data-gaps", label: "Data Gaps", group: "Advanced" },
  { href: "/external-sources", label: "External Sources", group: "Advanced" },
  { href: "/history", label: "History", group: "Advanced" },
  { href: "/system-status", label: "System Status", group: "Advanced" },
];

export const samplePrompts = [
  "Show parcels in Concord that are in the 100-year floodplain.",
  "Show commercial zoning around Concord.",
  "Show school districts for parcels in Harrisburg.",
  "Show 2014 parcels and zoning.",
  "Map recent permits and planning cases near Kannapolis.",
  "Map commercial growth opportunities near high traffic roads but avoid floodplain.",
  "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.",
  "How far is parcel 5528-12-3456 from the nearest school?",
];

export const workflowSteps = [
  { href: "/map-composer", label: "Map Composer", description: "Request, preview, adjust, and print/export." },
  { href: "/parcel-workspace", label: "Parcel Workspace", description: "Parcel IDs, PINs, addresses, and context maps." },
  { href: "/proximity", label: "Proximity", description: "Nearest facilities and straight-line route drafts." },
  { href: "/scenarios", label: "Scenarios", description: "Reviewable suitability frameworks." },
  { href: "/analysis", label: "Analysis", description: "Safe bounded local GeoJSON execution." },
  { href: "/reports", label: "Reports", description: "Local draft reports and exports." },
];
