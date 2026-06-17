"use client";

import type { DerivedOverlay, PreviewLayer } from "@/types/automap";
import { symbolDefinition, svgDataUrl } from "@/lib/map-symbols";

function isVisible(value: { visible?: boolean; visibility?: boolean; default_visible?: boolean }): boolean {
  return value.default_visible ?? value.visible ?? value.visibility ?? true;
}

function overlayLabel(overlay: DerivedOverlay): string {
  const role = `${overlay.role || ""} ${overlay.geometry_role || ""}`.toLowerCase();
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
  return layer.title || layer.layer_key || "Context layer";
}

function contextKind(layer: PreviewLayer): string {
  const blob = `${layer.role || ""} ${layer.layer_key || ""} ${layer.title || ""}`.toLowerCase();
  if (blob.includes("road") || blob.includes("street") || blob.includes("centerline")) return "line";
  if (blob.includes("flood")) return "flood";
  if (blob.includes("zoning")) return "zoning";
  return "context";
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
          const isParcel = definition.key === "selected_parcel";
          return (
            <span className="map-legend-item" key={`${definition.key}-${label}`}>
              {isRoute ? (
                <i className={`map-legend-line ${overlay.route_mode === "road_following_draft" ? "map-legend-line-solid" : "map-legend-line-dashed"}`} aria-hidden="true" />
              ) : isParcel ? (
                <i className="map-legend-parcel" aria-hidden="true" />
              ) : (
                <i className="map-legend-icon" style={{ backgroundImage: `url("${svgDataUrl(definition)}")` }} aria-hidden="true" />
              )}
              {label}
            </span>
          );
        })}
        {visibleContextLayers.map((layer) => (
          <span className="map-legend-item" key={`context-${layer.id || layer.layer_key || layer.title}`}>
            <i className={`map-legend-context map-legend-context-${contextKind(layer)}`} aria-hidden="true" />
            {contextLabel(layer)}
          </span>
        ))}
      </div>
    </aside>
  );
}
