"use client";

import type { CSSProperties } from "react";
import type { DerivedOverlay, PreviewLayer } from "@/types/automap";
import { isRoadRouteMode, symbolDefinition, svgDataUrl } from "@/lib/map-symbols";

function isVisible(value: { visible?: boolean; visibility?: boolean; default_visible?: boolean }): boolean {
  return value.default_visible ?? value.visible ?? value.visibility ?? true;
}

function overlayLabel(overlay: DerivedOverlay): string {
  const role = `${overlay.role || ""} ${overlay.geometry_role || ""}`.toLowerCase();
  if (overlay.legend_label) return overlay.legend_label;
  if (role.includes("affected") && role.includes("parcel")) return "Parcels in 100-year floodplain";
  if (role.includes("origin")) return "Origin Address";
  if (role.includes("target")) {
    if ((overlay.facility_type || "").includes("fire") || overlay.symbol_key === "target_fire_station") {
      return "Nearest Fire Station";
    }
    return overlay.facility_display_name ? `Nearest Facility: ${overlay.facility_display_name}` : "Nearest Facility";
  }
  if (role.includes("distance") || role.includes("route")) return overlay.route_label || "Route Draft";
  if (role.includes("parcel") || overlay.symbol_key === "selected_parcel") return "Selected Parcel";
  return overlay.title || overlay.id || "Derived output";
}

function contextLabel(layer: PreviewLayer): string {
  if (layer.legend_label) return layer.legend_label;
  const role = layer.cartography_role || "";
  if (role === "affected_parcels" || layer.map_role === "affected_parcels") return "Parcels in 100-year floodplain";
  if (role === "commercial_zoning") return "Commercial zoning";
  if (role === "zoning") return "Zoning context";
  if (role === "boundary") return "Concord boundary";
  if (role === "major_roads") return "Major roads";
  if (role === "roads") return "Road context";
  if (role === "flood") return "100-year floodplain";
  if (role === "parcel_context") return "Parcels";
  return layer.title || layer.layer_key || "Context layer";
}

function contextKind(layer: PreviewLayer): string {
  const blob = `${layer.cartography_role || ""} ${layer.role || ""} ${layer.layer_key || ""} ${layer.title || ""}`.toLowerCase();
  if (blob.includes("affected") && blob.includes("parcel")) return "affected-parcels";
  if (blob.includes("road") || blob.includes("street") || blob.includes("centerline")) return "line";
  if (blob.includes("flood")) return "flood";
  if (blob.includes("zoning")) return "zoning";
  return "context";
}

type EsriSymbol = {
  type?: string;
  style?: string;
  color?: unknown;
  width?: unknown;
  outline?: { color?: unknown; width?: unknown } | null;
};

type SymbolSource = { drawing_info?: Record<string, unknown> | null };

function rgba(value: unknown): string | undefined {
  if (!Array.isArray(value) || value.length < 3) return undefined;
  const [r, g, b] = value;
  if (typeof r !== "number" || typeof g !== "number" || typeof b !== "number") return undefined;
  const alphaValue = typeof value[3] === "number" ? value[3] : 255;
  const alpha = Math.max(0, Math.min(1, alphaValue > 1 ? alphaValue / 255 : alphaValue));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function rendererSymbol(layer: SymbolSource): EsriSymbol | null {
  const drawingInfo = layer.drawing_info as { renderer?: { symbol?: EsriSymbol } } | null | undefined;
  return drawingInfo?.renderer?.symbol || null;
}

function contextSwatchStyle(layer: SymbolSource): CSSProperties | undefined {
  const symbol = rendererSymbol(layer);
  if (!symbol) return undefined;
  const color = rgba(symbol.color);
  const outline = symbol.outline && typeof symbol.outline === "object" ? symbol.outline : null;
  if (symbol.type === "esriSLS") {
    return {
      borderTopColor: color,
      borderTopWidth: typeof symbol.width === "number" ? `${Math.max(2, symbol.width)}px` : undefined,
      borderTopStyle: symbol.style?.toLowerCase().includes("dash") ? "dashed" : "solid",
    };
  }
  return {
    background: color,
    borderColor: rgba(outline?.color),
    borderWidth: typeof outline?.width === "number" ? `${Math.max(1, outline.width)}px` : undefined,
  };
}

export function MapLegend({
  overlays = [],
  contextLayers = [],
}: {
  overlays?: DerivedOverlay[];
  contextLayers?: PreviewLayer[];
}) {
  const visibleOverlays = overlays.filter(isVisible);
  const visibleContextLayers = contextLayers.filter(isVisible);
  if (!visibleOverlays.length && !visibleContextLayers.length) return null;

  const seen = new Set<string>();
  const overlayItems = visibleOverlays
    .map((overlay) => ({ overlay, label: overlayLabel(overlay), definition: symbolDefinition(overlay.symbol_key) }))
    .filter((item) => {
      const key = `${item.definition.key}:${item.label}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });

  return (
    <aside className="map-legend" aria-label="Map legend">
      <strong>Legend</strong>
      <div className="map-legend-list">
        {overlayItems.map(({ overlay, label, definition }) => {
          const isRoute = definition.key.startsWith("route_") || (overlay.role || "").includes("line");
          const isParcel = definition.key === "selected_parcel" || definition.key === "affected_floodplain_parcel";
          const isAffectedParcel = definition.key === "affected_floodplain_parcel" || (overlay.role || "").includes("affected");
          const overlayStyle = contextSwatchStyle(overlay);
          return (
            <span className="map-legend-item" key={`${definition.key}-${label}`}>
              {isRoute ? (
                <i className={`map-legend-line ${isRoadRouteMode(overlay.route_mode) ? "map-legend-line-solid" : "map-legend-line-dashed"}`} aria-hidden="true" />
              ) : isParcel ? (
                <i className={isAffectedParcel ? "map-legend-parcel map-legend-affected-parcel" : "map-legend-parcel"} style={overlayStyle} aria-hidden="true" />
              ) : (
                <i className="map-legend-icon" style={{ backgroundImage: `url("${svgDataUrl(definition)}")` }} aria-hidden="true" />
              )}
              {label}
            </span>
          );
        })}
        {visibleContextLayers.map((layer) => (
          <span className="map-legend-item" key={`context-${layer.id || layer.layer_key || layer.title}`}>
            <i className={`map-legend-context map-legend-context-${contextKind(layer)}`} style={contextSwatchStyle(layer)} aria-hidden="true" />
            {contextLabel(layer)}
          </span>
        ))}
      </div>
    </aside>
  );
}
