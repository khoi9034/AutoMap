"use client";

import { useEffect, useMemo, useState } from "react";

import { ArcGISMapPreview } from "@/components/arcgis-map-preview";
import { ComposerLayerPanel } from "@/components/composer-layer-panel";
import { DerivedGeoJsonLayer, featureCollectionBounds, type GeoJsonFeatureCollection } from "@/components/derived-geojson-layer";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL } from "@/lib/api";
import type { ComposerResponse, DerivedOverlay, PreviewLayer } from "@/types/automap";

type LoadedOverlay = {
  overlay: DerivedOverlay;
  collection: GeoJsonFeatureCollection;
};

const SVG_WIDTH = 1000;
const SVG_HEIGHT = 520;

function absoluteApiUrl(url?: string): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${API_BASE_URL}${url.startsWith("/") ? url : `/${url}`}`;
}

function numericExtent(value: unknown): [number, number, number, number] | null {
  if (!value || typeof value !== "object") return null;
  const extent = value as { xmin?: unknown; ymin?: unknown; xmax?: unknown; ymax?: unknown };
  const xmin = Number(extent.xmin);
  const ymin = Number(extent.ymin);
  const xmax = Number(extent.xmax);
  const ymax = Number(extent.ymax);
  return [xmin, ymin, xmax, ymax].every(Number.isFinite) ? [xmin, ymin, xmax, ymax] : null;
}

function bufferedBounds(bounds: [number, number, number, number] | null): [number, number, number, number] {
  const fallback: [number, number, number, number] = [-80.72, 35.25, -80.42, 35.55];
  if (!bounds) return fallback;
  const width = Math.max(Math.abs(bounds[2] - bounds[0]), 0.004);
  const height = Math.max(Math.abs(bounds[3] - bounds[1]), 0.004);
  const bufferX = Math.max(width * 0.28, 0.002);
  const bufferY = Math.max(height * 0.28, 0.002);
  return [bounds[0] - bufferX, bounds[1] - bufferY, bounds[2] + bufferX, bounds[3] + bufferY];
}

function panelTitle(response: ComposerResponse): string {
  const target = response.proximity_result?.target_name;
  if (target) return `Nearest fire station found: ${target}`;
  if (response.proximity_result?.target_type) return "Nearest facility result";
  return response.map_title || "Composer preview";
}

function distanceText(response: ComposerResponse): string | null {
  const result = response.proximity_result;
  if (typeof result?.distance_value !== "number") return null;
  return `${result.distance_value.toFixed(2)} ${result.distance_unit || "miles"}`;
}

export function ComposerMapPreview({ response, packetId }: { response: ComposerResponse; packetId?: string }) {
  const derivedOverlays = useMemo(
    () => response.preview_config?.derived_overlays || response.proximity_result?.derived_overlays || [],
    [response.preview_config?.derived_overlays, response.proximity_result?.derived_overlays],
  );
  const contextLayers = useMemo(
    () => (response.preview_config?.operational_layers || []).filter((layer: PreviewLayer) => !layer.derived_local_analysis && !layer.local_output),
    [response.preview_config?.operational_layers],
  );
  const [loaded, setLoaded] = useState<LoadedOverlay[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!derivedOverlays.length) {
      setLoaded([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all(
      derivedOverlays.map(async (overlay) => {
        const url = absoluteApiUrl(overlay.url);
        if (!url) throw new Error(`Missing local GeoJSON URL for ${overlay.title || overlay.id}.`);
        const response = await fetch(url, { cache: "no-store" });
        if (!response.ok) throw new Error(`${overlay.title || overlay.id} failed to load (${response.status}).`);
        return { overlay, collection: (await response.json()) as GeoJsonFeatureCollection };
      }),
    )
      .then((items) => {
        if (!cancelled) setLoaded(items);
      })
      .catch((exc) => {
        if (!cancelled) setError(exc instanceof Error ? exc.message : "Derived GeoJSON failed to load.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [derivedOverlays]);

  if (!derivedOverlays.length && packetId) {
    return <ArcGISMapPreview packetId={packetId} />;
  }

  const configuredExtent = numericExtent(response.preview_config?.focus_extent || response.preview_config?.initial_extent);
  const computedExtent = featureCollectionBounds(loaded.map((item) => item.collection));
  const [xmin, ymin, xmax, ymax] = bufferedBounds(configuredExtent || computedExtent);
  const width = Math.max(xmax - xmin, 0.0001);
  const height = Math.max(ymax - ymin, 0.0001);
  const project = ([x, y]: [number, number]): [number, number] => [
    ((x - xmin) / width) * SVG_WIDTH,
    SVG_HEIGHT - ((y - ymin) / height) * SVG_HEIGHT,
  ];
  const distance = distanceText(response);
  const routeWarning = response.proximity_result?.route_status === "network_route_not_available" ||
    (response.proximity_result?.warnings || []).some((warning) => warning.toLowerCase().includes("not a driving route"));
  const propertyNotResolved = response.proximity_result?.property_match_status === "not_resolved";

  return (
    <div className="composer-derived-preview page-stack">
      <section className="panel composer-derived-map-shell">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Focused result map</p>
            <h3>{panelTitle(response)}</h3>
            <p className="muted">
              {distance ? `Straight-line distance: ${distance}. Line shown on map.` : "Local derived overlays are drawn from AutoMap output GeoJSON."}
            </p>
          </div>
          <div className="chip-row">
            <StatusChip tone="success">Origin marker</StatusChip>
            <StatusChip tone="success">Target marker</StatusChip>
            <StatusChip tone="success">Line shown</StatusChip>
          </div>
        </div>

        {propertyNotResolved ? (
          <div className="inline-warning" role="status">
            Address matched, but related parcel was not resolved from verified fields. The preview shows the address point, nearest facility, and straight-line distance only.
          </div>
        ) : null}
        {routeWarning ? (
          <div className="inline-warning" role="status">
            Straight-line reference only. This is not a driving route.
          </div>
        ) : null}
        {loading ? <div className="preview-loading">Loading local origin, target, and line GeoJSON...</div> : null}
        {error ? <div className="preview-error">{error}</div> : null}

        <div className="derived-map-canvas" aria-label="Focused local derived map preview">
          <svg viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`} role="img">
            <defs>
              <pattern id="composer-map-grid" width="42" height="42" patternUnits="userSpaceOnUse">
                <path d="M 42 0 L 0 0 0 42" fill="none" stroke="#d7e3ee" strokeWidth="1" />
              </pattern>
            </defs>
            <rect width={SVG_WIDTH} height={SVG_HEIGHT} fill="#eef4f9" />
            <rect width={SVG_WIDTH} height={SVG_HEIGHT} fill="url(#composer-map-grid)" opacity="0.85" />
            <path d="M 80 390 C 220 340 300 430 440 372 S 710 250 900 310" fill="none" stroke="#c7d2de" strokeWidth="24" strokeLinecap="round" opacity="0.75" />
            <path d="M 80 390 C 220 340 300 430 440 372 S 710 250 900 310" fill="none" stroke="#ffffff" strokeWidth="10" strokeLinecap="round" opacity="0.88" />
            {loaded.map((item) => (
              <DerivedGeoJsonLayer key={item.overlay.id || item.overlay.title} overlay={item.overlay} collection={item.collection} project={project} />
            ))}
          </svg>
          <div className="derived-map-legend">
            <span><i className="legend-origin" /> Origin Address</span>
            <span><i className="legend-target" /> Nearest Fire Station</span>
            <span><i className="legend-line" /> Straight-Line Distance</span>
          </div>
        </div>
      </section>

      <ComposerLayerPanel derivedOverlays={derivedOverlays} contextLayers={contextLayers} />
    </div>
  );
}
