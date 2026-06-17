"use client";

import type { DerivedOverlay } from "@/types/automap";
import { legendItems, svgDataUrl } from "@/lib/map-symbols";

export function MapSymbolLegend({ overlays }: { overlays: DerivedOverlay[] }) {
  const items = legendItems(overlays);
  if (!items.length) return null;
  return (
    <div className="map-symbol-legend" aria-label="Map symbol legend">
      {items.map((item) => (
        <span className="map-symbol-legend-item" key={item.key}>
          <span className="map-symbol-legend-icon" style={{ backgroundImage: `url("${svgDataUrl(item)}")` }} aria-hidden="true" />
          {item.label}
        </span>
      ))}
    </div>
  );
}
