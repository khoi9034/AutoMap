import { presetPrompts } from "@/lib/automap-presets";

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
  { href: "/methodology", label: "Methodology", group: "Support" },
  { href: "/system-status", label: "System Status", group: "Support" },
];

export const samplePrompts = presetPrompts();

export const workflowSteps = [
  { href: "/map-composer", label: "Map Composer", description: "Request, preview, adjust, and print/export." },
  { href: "/parcel-workspace", label: "Parcel Workspace", description: "Parcel IDs, PINs, addresses, and context maps." },
  { href: "/proximity", label: "Proximity", description: "Nearest facilities and road-following route drafts." },
  { href: "/tables", label: "Tables", description: "Bounded table previews and CSV/JSON exports." },
  { href: "/scenarios", label: "Scenarios", description: "Reviewable suitability frameworks." },
  { href: "/analysis", label: "Analysis", description: "Safe bounded local GeoJSON execution." },
  { href: "/reports", label: "Reports", description: "Local draft reports and exports." },
];
