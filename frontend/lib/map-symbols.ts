import type { DerivedOverlay } from "@/types/automap";

export type SymbolDefinition = {
  key: string;
  label: string;
  color: string;
  halo?: string;
  accent?: string;
  glyph: "home" | "fire" | "school" | "hospital" | "park" | "library" | "vote" | "facility" | "parcel" | "route";
};

const SYMBOLS: Record<string, SymbolDefinition> = {
  origin_home: { key: "origin_home", label: "Origin address", color: "#0f766e", glyph: "home" },
  origin_address: { key: "origin_address", label: "Origin address", color: "#0f766e", glyph: "home" },
  target_fire_station: { key: "target_fire_station", label: "Fire station", color: "#dc2626", glyph: "fire" },
  target_school: { key: "target_school", label: "School", color: "#4f46e5", glyph: "school" },
  target_hospital: { key: "target_hospital", label: "Hospital", color: "#b91c1c", glyph: "hospital" },
  target_park: { key: "target_park", label: "Park", color: "#15803d", glyph: "park" },
  target_library: { key: "target_library", label: "Library", color: "#2563eb", glyph: "library" },
  target_polling_place: { key: "target_polling_place", label: "Polling place", color: "#7c3aed", glyph: "vote" },
  target_facility: { key: "target_facility", label: "Facility", color: "#334155", glyph: "facility" },
  route_road_following: { key: "route_road_following", label: "Road-following draft", color: "#1d4ed8", glyph: "route" },
  route_straight_line: { key: "route_straight_line", label: "Straight-line fallback", color: "#2563eb", glyph: "route" },
  selected_parcel: { key: "selected_parcel", label: "Selected parcel", color: "#f59e0b", glyph: "parcel" },
};

export function symbolDefinition(symbolKey?: string | null): SymbolDefinition {
  return SYMBOLS[symbolKey || ""] || SYMBOLS.target_facility;
}

function markerPath(glyph: SymbolDefinition["glyph"]): string {
  switch (glyph) {
    case "home":
      return '<path d="M8 17V10.5L16 4l8 6.5V17"/><path d="M11 17v-5h10v5"/>';
    case "fire":
      return '<path d="M16 27c5 0 8-3 8-7 0-5-4-7-5-11-3 2-4 5-3 8-2-1-3-3-2-6-4 3-6 6-6 9 0 4 3 7 8 7z"/><path d="M16 24c2 0 4-1.5 4-3.6 0-2-1.7-3.2-2.2-5.1-1.5 1.1-2.1 2.5-1.7 4.2-1-.4-1.5-1.4-1.2-2.8-1.8 1.4-2.9 2.8-2.9 4 0 2 1.8 3.3 4 3.3z" fill="white" stroke="none"/>';
    case "school":
      return '<path d="M6 13l10-5 10 5-10 5-10-5z"/><path d="M10 16v5c2 2 10 2 12 0v-5"/><path d="M26 13v7"/>';
    case "hospital":
      return '<path d="M8 8h16v16H8z"/><path d="M16 11v10"/><path d="M11 16h10"/>';
    case "park":
      return '<path d="M16 5l6 9h-4l5 7H9l5-7h-4l6-9z"/><path d="M16 21v5"/>';
    case "library":
      return '<path d="M8 8h5a4 4 0 014 4v13H8z"/><path d="M24 8h-5a4 4 0 00-4 4v13h9z"/>';
    case "vote":
      return '<path d="M7 15h18v10H7z"/><path d="M10 15l6-8 6 8"/><path d="M13 17l2 2 5-6"/>';
    case "parcel":
      return '<path d="M7 9l10-4 8 5-2 14-12 2-4-17z"/>';
    case "facility":
      return '<path d="M8 25V11l8-5 8 5v14"/><path d="M12 25v-7h8v7"/><path d="M12 13h2M18 13h2"/>';
    case "route":
      return '<path d="M7 22c4-10 14 0 18-10"/><circle cx="7" cy="22" r="2"/><circle cx="25" cy="12" r="2"/>';
    default:
      return "";
  }
}

export function svgDataUrl(definition: SymbolDefinition): string {
  const fill = definition.glyph === "fire" ? definition.color : "none";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 44"><defs><filter id="s" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="#0f172a" flood-opacity=".24"/></filter></defs><path d="M20 42c5.2-7.2 14-16.2 14-25A14 14 0 106 17c0 8.8 8.8 17.8 14 25z" fill="white" stroke="${definition.color}" stroke-width="2.7" filter="url(#s)"/><circle cx="20" cy="17" r="11.5" fill="${definition.glyph === "fire" ? "#fff5f5" : "#f8fafc"}" stroke="${definition.color}" stroke-width="1"/><g transform="translate(4 1)" fill="${fill}" stroke="${definition.color}" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round">${markerPath(definition.glyph)}</g></svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export function isRoadRouteMode(routeMode?: string | null): boolean {
  return ["road_network", "road_network_route", "road_following_draft"].includes((routeMode || "").toLowerCase());
}

export function arcgisSymbolForOverlay(
  overlay: DerivedOverlay,
  geometryType: string,
  options: { casing?: boolean } = {},
): Record<string, unknown> {
  const symbolKey = overlay.symbol_key || overlay.symbol?.symbol_key?.toString();
  const routeMode = overlay.route_mode || overlay.symbol?.route_mode?.toString();
  const role = (overlay.role || "").toLowerCase();
  const definition = symbolDefinition(symbolKey);
  if (geometryType === "point") {
    return {
      type: "picture-marker",
      url: svgDataUrl(definition),
      width: "34px",
      height: "38px",
      yoffset: "16px",
    };
  }
  if (geometryType === "line") {
    const roadRoute = isRoadRouteMode(routeMode);
    if (options.casing) {
      return {
        type: "simple-line",
        color: [255, 255, 255, 0.92],
        width: roadRoute ? 6 : 4.5,
        style: roadRoute ? "solid" : "dash",
        cap: "round",
        join: "round",
      };
    }
    return {
      type: "simple-line",
      color: definition.color,
      width: roadRoute ? 3.2 : 2.4,
      style: roadRoute ? "solid" : "dash",
      cap: "round",
      join: "round",
    };
  }
  const color = role.includes("parcel") ? "#f59e0b" : definition.color;
  return {
    type: "simple-fill",
    color: role.includes("parcel") ? [245, 158, 11, 0.12] : [37, 99, 235, 0.1],
    outline: { color, width: role.includes("parcel") ? 3 : 2 },
  };
}

export function legendItems(overlays: DerivedOverlay[]): SymbolDefinition[] {
  const seen = new Set<string>();
  return overlays
    .map((overlay) => symbolDefinition(overlay.symbol_key || (overlay.role === "target" ? "target_facility" : undefined)))
    .filter((definition) => {
      if (seen.has(definition.key)) return false;
      seen.add(definition.key);
      return true;
    });
}

export { SYMBOLS as MAP_SYMBOLS };
