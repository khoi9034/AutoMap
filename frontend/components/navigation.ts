export const navigationItems = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/map-request", label: "Map Request" },
  { href: "/recipe-review", label: "Recipe Review" },
  { href: "/map-preview", label: "Map Preview" },
  { href: "/adjustments", label: "Adjustments" },
  { href: "/approval", label: "Approval" },
  { href: "/publish-center", label: "Publish Center" },
  { href: "/layer-catalog", label: "Layer Catalog" },
  { href: "/data-gaps", label: "Data Gaps" },
  { href: "/history", label: "History" },
  { href: "/system-status", label: "System Status" },
];

export const samplePrompts = [
  "Show parcels in Concord that are in the 100-year floodplain.",
  "Show commercial zoning around Concord.",
  "Show school districts for parcels in Harrisburg.",
  "Show 2014 parcels and zoning.",
  "Map recent permits and planning cases near Kannapolis.",
];

export const workflowSteps = [
  { href: "/map-request", label: "Map Request", description: "Prompt to draft recipe." },
  { href: "/recipe-review", label: "Recipe Review", description: "Layers, filters, gaps, and operations." },
  { href: "/map-preview", label: "Map Preview", description: "Local WebMap JSON preview." },
  { href: "/adjustments", label: "Adjustments", description: "Human YAML adjustment loop." },
  { href: "/approval", label: "Approval", description: "Local readiness gate." },
  { href: "/publish-center", label: "Dry-Run Publish", description: "Dry-run receipts only." },
];
