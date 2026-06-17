"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ArcGISMapPreview } from "@/components/arcgis-map-preview";
import { ComposerLayerPanel } from "@/components/composer-layer-panel";
import { featureCollectionBounds, type GeoJsonFeature, type GeoJsonFeatureCollection } from "@/components/derived-geojson-layer";
import { MapSymbolLegend } from "@/components/map-symbol-legend";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL } from "@/lib/api";
import { arcgisSymbolForOverlay } from "@/lib/map-symbols";
import type { ComposerResponse, DerivedOverlay, PreviewLayer } from "@/types/automap";

type LoadedOverlay = {
  overlay: DerivedOverlay;
  collection: GeoJsonFeatureCollection;
};

type ArcLayer = {
  addMany?: (items: unknown[]) => void;
};

type ArcMap = {
  add: (layer: unknown) => void;
};

type ArcView = {
  when: (callback?: () => unknown) => Promise<unknown>;
  goTo: (target: unknown, options?: Record<string, unknown>) => Promise<unknown>;
  destroy: () => void;
};

type ArcConstructor<T = unknown> = new (props?: Record<string, unknown>) => T;

type ArcModules = {
  EsriMap: ArcConstructor<ArcMap>;
  MapView: ArcConstructor<ArcView>;
  GraphicsLayer: ArcConstructor<ArcLayer>;
  Graphic: ArcConstructor;
  FeatureLayer: ArcConstructor;
  MapImageLayer: ArcConstructor;
  Extent: ArcConstructor;
  Point: ArcConstructor;
  Polyline: ArcConstructor;
  Polygon: ArcConstructor;
};

const WGS84 = { wkid: 4326 };

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
  const classification = response.proximity_result?.target_classification;
  if (target && classification === "mixed_fire_ems") return `Nearest fire/EMS station found: ${target}`;
  if (target) return `Nearest fire station found: ${target}`;
  if (response.proximity_result?.target_type) return "Nearest facility result";
  return response.map_title || "Composer preview";
}

function distanceText(response: ComposerResponse): string | null {
  const result = response.proximity_result;
  if (typeof result?.distance_value !== "number") return null;
  return `${result.distance_value.toFixed(2)} ${result.distance_unit || "miles"}`;
}

function routeLabel(response: ComposerResponse): string {
  const result = response.proximity_result;
  if (result?.route_label) return result.route_label;
  if (result?.route_mode === "road_following_draft") return "Road-following draft route";
  return "Straight-line reference";
}

function contextLayerUrl(layer: PreviewLayer): string {
  if (layer.layer_url || layer.url) return layer.layer_url || layer.url || "";
  if (layer.service_url && typeof layer.layer_id === "number") return `${layer.service_url.replace(/\/$/, "")}/${layer.layer_id}`;
  return layer.service_url || "";
}

function graphicsForFeature(feature: GeoJsonFeature, overlay: DerivedOverlay, modules: ArcModules): unknown[] {
  const geometry = feature.geometry;
  const properties = feature.properties || {};
  if (!geometry || !geometry.type) return [];
  const baseGraphic = (arcGeometry: unknown, geometryType: "point" | "line" | "polygon") =>
    new modules.Graphic({
      geometry: arcGeometry,
      attributes: properties,
      popupTemplate: {
        title: overlay.title || "{automap_title}",
        content: Object.entries(properties)
          .slice(0, 10)
          .map(([key, value]) => `<strong>${key}</strong>: ${String(value)}`)
          .join("<br />"),
      },
      symbol: arcgisSymbolForOverlay(overlay, geometryType),
    });

  if (geometry.type === "Point" && Array.isArray(geometry.coordinates)) {
    return [
      baseGraphic(
        new modules.Point({
          longitude: Number(geometry.coordinates[0]),
          latitude: Number(geometry.coordinates[1]),
          spatialReference: WGS84,
        }),
        "point",
      ),
    ];
  }
  if (geometry.type === "LineString" && Array.isArray(geometry.coordinates)) {
    return [baseGraphic(new modules.Polyline({ paths: [geometry.coordinates], spatialReference: WGS84 }), "line")];
  }
  if (geometry.type === "MultiLineString" && Array.isArray(geometry.coordinates)) {
    return geometry.coordinates
      .filter(Array.isArray)
      .map((path) => baseGraphic(new modules.Polyline({ paths: [path], spatialReference: WGS84 }), "line"));
  }
  if (geometry.type === "Polygon" && Array.isArray(geometry.coordinates)) {
    return [baseGraphic(new modules.Polygon({ rings: geometry.coordinates, spatialReference: WGS84 }), "polygon")];
  }
  if (geometry.type === "MultiPolygon" && Array.isArray(geometry.coordinates)) {
    return geometry.coordinates
      .filter(Array.isArray)
      .map((polygon) => baseGraphic(new modules.Polygon({ rings: polygon, spatialReference: WGS84 }), "polygon"));
  }
  return [];
}

function addContextLayers(map: ArcMap, contextLayers: PreviewLayer[], modules: ArcModules): void {
  contextLayers.forEach((layer) => {
    const url = contextLayerUrl(layer);
    if (!url) return;
    const title = layer.title || layer.layer_key || "Context layer";
    const visible = layer.default_visible ?? layer.visibility ?? true;
    const opacity = typeof layer.opacity === "number" ? layer.opacity : layer.role?.includes("constraint") ? 0.45 : 0.72;
    const definitionExpression = layer.definition_expression || undefined;
    try {
      if (layer.service_url && typeof layer.layer_id === "number" && /MapServer/i.test(layer.service_url)) {
        map.add(
          new modules.MapImageLayer({
            url: layer.service_url,
            title,
            opacity,
            visible,
            sublayers: [
              {
                id: layer.layer_id,
                title,
                visible,
                definitionExpression,
              },
            ],
          }),
        );
        return;
      }
      map.add(
        new modules.FeatureLayer({
          url,
          title,
          opacity,
          visible,
          definitionExpression,
          outFields: ["*"],
        }),
      );
    } catch {
      // Layer failures are surfaced by ArcGIS layer view errors; a single context
      // layer should not prevent local origin/target/line overlays from drawing.
    }
  });
}

async function loadArcModules(): Promise<ArcModules> {
  const [
    { default: EsriMap },
    { default: MapView },
    { default: GraphicsLayer },
    { default: Graphic },
    { default: FeatureLayer },
    { default: MapImageLayer },
    { default: Extent },
    { default: Point },
    { default: Polyline },
    { default: Polygon },
  ] = await Promise.all([
    import("@arcgis/core/Map"),
    import("@arcgis/core/views/MapView"),
    import("@arcgis/core/layers/GraphicsLayer"),
    import("@arcgis/core/Graphic"),
    import("@arcgis/core/layers/FeatureLayer"),
    import("@arcgis/core/layers/MapImageLayer"),
    import("@arcgis/core/geometry/Extent"),
    import("@arcgis/core/geometry/Point"),
    import("@arcgis/core/geometry/Polyline"),
    import("@arcgis/core/geometry/Polygon"),
  ]);
  return {
    EsriMap: EsriMap as unknown as ArcConstructor<ArcMap>,
    MapView: MapView as unknown as ArcConstructor<ArcView>,
    GraphicsLayer: GraphicsLayer as unknown as ArcConstructor<ArcLayer>,
    Graphic: Graphic as unknown as ArcConstructor,
    FeatureLayer: FeatureLayer as unknown as ArcConstructor,
    MapImageLayer: MapImageLayer as unknown as ArcConstructor,
    Extent: Extent as unknown as ArcConstructor,
    Point: Point as unknown as ArcConstructor,
    Polyline: Polyline as unknown as ArcConstructor,
    Polygon: Polygon as unknown as ArcConstructor,
  };
}

export function ComposerMapPreview({ response, packetId }: { response: ComposerResponse; packetId?: string }) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<ArcView | null>(null);
  const derivedOverlays = useMemo(
    () => response.preview_config?.derived_overlays || response.proximity_result?.derived_overlays || [],
    [response.preview_config?.derived_overlays, response.proximity_result?.derived_overlays],
  );
  const contextLayers = useMemo(
    () => (response.preview_config?.context_layers || response.preview_config?.operational_layers || []).filter((layer: PreviewLayer) => !layer.derived_local_analysis && !layer.local_output),
    [response.preview_config?.context_layers, response.preview_config?.operational_layers],
  );
  const [loaded, setLoaded] = useState<LoadedOverlay[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [mapError, setMapError] = useState<string | null>(null);

  useEffect(() => {
    if (!derivedOverlays.length) {
      setLoaded([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setLoadError(null);
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
        if (!cancelled) setLoadError(exc instanceof Error ? exc.message : "Derived GeoJSON failed to load.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [derivedOverlays]);

  useEffect(() => {
    if (!derivedOverlays.length || loading || loadError || !containerRef.current) return;
    let cancelled = false;
    let view: ArcView | undefined;
    setMapError(null);

    loadArcModules()
      .then((modules) => {
        if (cancelled || !containerRef.current) return;
        const map = new modules.EsriMap({
          basemap: response.preview_config?.basemap || "streets-vector",
        });
        addContextLayers(map, contextLayers, modules);
        loaded.forEach((item) => {
          const layer = new modules.GraphicsLayer({
            title: item.overlay.title || item.overlay.id || "Derived overlay",
            visible: item.overlay.visible !== false,
          });
          (item.collection.features || []).forEach((feature) => {
            layer.addMany?.(graphicsForFeature(feature, item.overlay, modules));
          });
          map.add(layer);
        });

        const configuredExtent = numericExtent(response.preview_config?.focus_extent || response.preview_config?.initial_extent);
        const computedExtent = featureCollectionBounds(loaded.map((item) => item.collection));
        const [xmin, ymin, xmax, ymax] = bufferedBounds(configuredExtent || computedExtent);
        const extent = new modules.Extent({ xmin, ymin, xmax, ymax, spatialReference: WGS84 });

        const nextView = new modules.MapView({
          container: containerRef.current,
          map,
          extent,
          constraints: {
            snapToZoom: false,
          },
          ui: {
            components: ["attribution", "zoom"],
          },
        });
        view = nextView;
        viewRef.current = view;
        return nextView.when(() => nextView.goTo(extent, { animate: false }));
      })
      .catch((exc) => {
        if (!cancelled) {
          setMapError(exc instanceof Error ? exc.message : "Map preview failed to load.");
        }
      });

    return () => {
      cancelled = true;
      if (viewRef.current) {
        viewRef.current.destroy();
        viewRef.current = null;
      } else if (view) {
        view.destroy();
      }
    };
  }, [contextLayers, derivedOverlays.length, loadError, loaded, loading, response.preview_config?.basemap, response.preview_config?.focus_extent, response.preview_config?.initial_extent]);

  if (!derivedOverlays.length && packetId) {
    return <ArcGISMapPreview packetId={packetId} />;
  }

  const distance = distanceText(response);
  const lineLabel = routeLabel(response);
  const routeMode = response.proximity_result?.route_mode || "straight_line_reference";
  const routeWarning = routeMode !== "road_following_draft" ||
    Boolean(response.proximity_result?.route_warning) ||
    (response.proximity_result?.warnings || []).some((warning) => warning.toLowerCase().includes("not a driving route"));
  const propertyNotResolved = response.proximity_result?.property_match_status === "not_resolved";
  const fireEmsWarning = (response.proximity_result?.warnings || []).some((warning) => warning.toLowerCase().includes("fire") && warning.toLowerCase().includes("ems"));
  const clutterWarning = (response.warnings || []).some((warning) => warning.toLowerCase().includes("address layer hidden"));

  return (
    <div className="composer-derived-preview page-stack">
      <section className="panel composer-derived-map-shell">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Focused ArcGIS map</p>
            <h3>{panelTitle(response)}</h3>
            <p className="muted">
              {distance ? `${lineLabel}: ${distance}. Line shown on map.` : "Local derived overlays are drawn on a real ArcGIS basemap."}
            </p>
          </div>
          <div className="chip-row">
            <StatusChip tone="success">Real basemap</StatusChip>
            <StatusChip tone="success">Home marker</StatusChip>
            <StatusChip tone="success">Facility marker</StatusChip>
            <StatusChip tone={routeMode === "road_following_draft" ? "success" : "warning"}>{lineLabel}</StatusChip>
          </div>
        </div>

        {propertyNotResolved ? (
          <div className="inline-warning" role="status">
            Address matched, but related parcel was not resolved from verified fields. The preview shows the address point, nearest facility, and straight-line distance only.
          </div>
        ) : null}
        {fireEmsWarning ? (
          <div className="inline-warning" role="status">
            The verified layer combines Fire and EMS stations; AutoMap could not confirm a fire-only filter.
          </div>
        ) : null}
        {routeWarning ? (
          <div className="inline-warning" role="status">
            {response.proximity_result?.route_warning || "Straight-line reference only. This is not a driving route."}
          </div>
        ) : null}
        {clutterWarning ? (
          <div className="inline-warning" role="status">
            Full address layer hidden to reduce clutter. The origin address marker remains visible.
          </div>
        ) : null}
        {loading ? <div className="preview-loading">Loading local origin, target, and line GeoJSON...</div> : null}
        {loadError ? <div className="preview-error">Map preview failed to load. {loadError}</div> : null}
        {mapError ? <div className="preview-error">Map preview failed to load. {mapError}</div> : null}

        <div className="composer-real-map" ref={containerRef} aria-label="Focused ArcGIS composer map preview" />
        <MapSymbolLegend overlays={derivedOverlays} />
      </section>

      <ComposerLayerPanel derivedOverlays={derivedOverlays} contextLayers={contextLayers} />
    </div>
  );
}
