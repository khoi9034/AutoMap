"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ArcGISMapPreview } from "@/components/arcgis-map-preview";
import { ComposerLayerPanel } from "@/components/composer-layer-panel";
import { featureCollectionBounds, type GeoJsonFeature, type GeoJsonFeatureCollection } from "@/components/derived-geojson-layer";
import { MapFrame, type MapFrameMode } from "@/components/map-renderer/map-frame";
import type { MapViewCommand, SharedMapRendererMode } from "@/components/map-renderer/shared-map-renderer";
import { MapLegend } from "@/components/map-legend";
import { MapScaleBar } from "@/components/map-scale-bar";
import { NorthArrow } from "@/components/north-arrow";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL } from "@/lib/api";
import { arcgisSymbolForOverlay, isRoadRouteMode } from "@/lib/map-symbols";
import type { ComposerMapState, ComposerResponse, DerivedOverlay, JsonValue, PreviewLayer } from "@/types/automap";

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
  takeScreenshot?: (options?: Record<string, unknown>) => Promise<{ dataUrl?: string; data?: string }>;
  center?: unknown;
  extent?: unknown;
  zoom?: number;
  scale?: number;
  rotation?: number;
  width?: number;
  watch?: (property: string, callback: (value: unknown) => void) => { remove?: () => void };
  ui?: { add?: (item: unknown, position: string) => void; components?: string[] };
  navigation?: Record<string, unknown>;
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

function isLockedMode(mode: SharedMapRendererMode): boolean {
  return mode !== "adjust_interactive";
}

function lockedModeLabel(mode: SharedMapRendererMode): string {
  if (mode === "print_locked") return "Locked for print";
  if (mode === "exhibit_locked") return "Locked exhibit";
  return "Locked preview";
}

function frameModeForInteraction(mode: SharedMapRendererMode): MapFrameMode {
  if (mode === "adjust_interactive") return "adjust";
  if (mode === "print_locked") return "print";
  if (mode === "exhibit_locked") return "exhibit";
  return "preview";
}

function frameSizingForInteraction(mode: SharedMapRendererMode): { aspectRatio?: string; minHeight?: string; maxHeight?: string } {
  if (mode === "adjust_interactive") {
    return { minHeight: "600px" };
  }
  if (mode === "print_locked" || mode === "exhibit_locked") {
    return { aspectRatio: "16 / 10", minHeight: "560px" };
  }
  return { aspectRatio: "16 / 10", minHeight: "clamp(520px, 68vh, 760px)", maxHeight: "760px" };
}

function serializeArcObject(value: unknown): Record<string, JsonValue> | null {
  if (!value || typeof value !== "object") return null;
  const withToJSON = value as { toJSON?: () => Record<string, JsonValue> };
  if (typeof withToJSON.toJSON === "function") return withToJSON.toJSON();
  return value as Record<string, JsonValue>;
}

function viewStateFromArcView(view: ArcView): Partial<ComposerMapState> {
  return {
    current_center: serializeArcObject(view.center),
    current_zoom: typeof view.zoom === "number" ? view.zoom : null,
    current_scale: typeof view.scale === "number" ? view.scale : null,
    current_rotation: typeof view.rotation === "number" ? view.rotation : 0,
    map_extent: serializeArcObject(view.extent),
  };
}

function panelTitle(response: ComposerResponse): string {
  const target = response.proximity_result?.target_name;
  const classification = response.proximity_result?.target_classification;
  if (target && classification === "mixed_fire_ems") return `Nearest fire/EMS station found: ${target}`;
  if (target) return `Nearest fire station found: ${target}`;
  if (response.proximity_result?.target_type) return "Nearest facility result";
  return response.map_title || "Composer preview";
}

function routeSummary(response: ComposerResponse, lineLabel: string, distance: string | null): string {
  const target = panelTitle(response);
  if (distance) return `${target} - ${lineLabel}: ${distance}. Line shown on map.`;
  return "Local derived overlays are drawn on a real ArcGIS basemap.";
}

function distanceText(response: ComposerResponse): string | null {
  const result = response.proximity_result;
  if (typeof result?.distance_value !== "number") return null;
  return `${result.distance_value.toFixed(2)} ${result.distance_unit || "miles"}`;
}

function mapLayout(response: ComposerResponse) {
  return response.map_layout || response.preview_config?.map_layout || null;
}

function routeLabel(response: ComposerResponse): string {
  const result = response.proximity_result;
  if (result?.route_label) return result.route_label;
  if (isRoadRouteMode(result?.route_mode)) return "Road-following draft route";
  if (result?.route_mode === "unavailable") return "Route unavailable";
  return "Straight-line fallback";
}

function contextLayerUrl(layer: PreviewLayer): string {
  if (layer.layer_url || layer.url) return layer.layer_url || layer.url || "";
  if (layer.service_url && typeof layer.layer_id === "number") return `${layer.service_url.replace(/\/$/, "")}/${layer.layer_id}`;
  return layer.service_url || "";
}

function graphicsForFeature(
  feature: GeoJsonFeature,
  overlay: DerivedOverlay,
  modules: ArcModules,
  options: { casing?: boolean } = {},
): unknown[] {
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
      symbol: arcgisSymbolForOverlay(overlay, geometryType, options),
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

function overlayKind(overlay: DerivedOverlay): "route" | "parcel" | "origin" | "target" | "other" {
  const blob = `${overlay.role || ""} ${overlay.geometry_role || ""} ${overlay.symbol_key || ""} ${overlay.id || ""}`.toLowerCase();
  if (blob.includes("route") || blob.includes("distance_line") || blob.includes("straight_line")) return "route";
  if (blob.includes("parcel")) return "parcel";
  if (blob.includes("origin")) return "origin";
  if (blob.includes("target") || blob.includes("facility")) return "target";
  return "other";
}

function overlayVisible(overlay: DerivedOverlay): boolean {
  return overlay.default_visible ?? overlay.visible ?? true;
}

function addOverlayGraphicsLayer(
  map: ArcMap,
  item: LoadedOverlay,
  modules: ArcModules,
  titleSuffix = "",
  options: { casing?: boolean } = {},
): void {
  const layer = new modules.GraphicsLayer({
    title: `${item.overlay.title || item.overlay.id || "Derived overlay"}${titleSuffix}`,
    visible: overlayVisible(item.overlay),
  });
  (item.collection.features || []).forEach((feature) => {
    layer.addMany?.(graphicsForFeature(feature, item.overlay, modules, options));
  });
  map.add(layer);
}

function addDerivedOverlayLayers(map: ArcMap, items: LoadedOverlay[], modules: ArcModules): void {
  const visibleItems = items.filter((item) => overlayVisible(item.overlay));
  const byKind = (kind: ReturnType<typeof overlayKind>) => visibleItems.filter((item) => overlayKind(item.overlay) === kind);
  const routeItems = byKind("route");

  routeItems.forEach((item) => addOverlayGraphicsLayer(map, item, modules, " casing", { casing: true }));
  routeItems.forEach((item) => addOverlayGraphicsLayer(map, item, modules));
  byKind("parcel").forEach((item) => addOverlayGraphicsLayer(map, item, modules));
  byKind("other").forEach((item) => addOverlayGraphicsLayer(map, item, modules));
  byKind("origin").forEach((item) => addOverlayGraphicsLayer(map, item, modules));
  byKind("target").forEach((item) => addOverlayGraphicsLayer(map, item, modules));
}

function contextDrawRank(layer: PreviewLayer): number {
  const blob = `${layer.role || ""} ${layer.layer_key || ""} ${layer.title || ""} ${layer.category || ""}`.toLowerCase();
  if (blob.includes("boundary") || blob.includes("municipal") || blob.includes("district")) return 10;
  if (blob.includes("zoning") || blob.includes("flood") || blob.includes("school")) return 20;
  if (blob.includes("parcel")) return 30;
  if (blob.includes("road") || blob.includes("street") || blob.includes("centerline")) return 40;
  return 25;
}

function addContextLayers(map: ArcMap, contextLayers: PreviewLayer[], modules: ArcModules): void {
  [...contextLayers].sort((a, b) => contextDrawRank(a) - contextDrawRank(b)).forEach((layer) => {
    const url = contextLayerUrl(layer);
    if (!url) return;
    const title = layer.title || layer.layer_key || "Context layer";
    const visible = layer.default_visible ?? layer.visibility ?? true;
    const blob = `${layer.role || ""} ${layer.layer_key || ""} ${layer.title || ""}`.toLowerCase();
    const opacity =
      typeof layer.opacity === "number"
        ? layer.opacity
        : blob.includes("flood") || blob.includes("zoning") || blob.includes("district")
          ? 0.36
          : blob.includes("road") || blob.includes("street")
            ? 0.58
            : 0.62;
    const definitionExpression = layer.definition_expression || undefined;
    const renderer = layer.drawing_info?.renderer;
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
                renderer,
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
          renderer,
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

export function ComposerMapPreview({
  interactionMode = "preview_locked",
  mapOnly = false,
  onSnapshotReady,
  onViewStateChange,
  response,
  packetId,
  showLayerPanel = true,
  viewCommand,
}: {
  interactionMode?: SharedMapRendererMode;
  mapOnly?: boolean;
  onSnapshotReady?: (dataUrl: string) => void;
  onViewStateChange?: (state: Partial<ComposerMapState>) => void;
  response: ComposerResponse;
  packetId?: string;
  showLayerPanel?: boolean;
  viewCommand?: MapViewCommand | null;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const viewRef = useRef<ArcView | null>(null);
  const modulesRef = useRef<ArcModules | null>(null);
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
  const [viewScale, setViewScale] = useState<number | null>(null);
  const [viewWidth, setViewWidth] = useState<number | null>(null);
  const locked = isLockedMode(interactionMode);

  useEffect(() => {
    if (!derivedOverlays.length) {
      setLoaded([]);
      setLoading(false);
      setLoadError(null);
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
    if ((!derivedOverlays.length && !contextLayers.length) || loading || loadError || !containerRef.current) return;
    let cancelled = false;
    let view: ArcView | undefined;
    let scaleHandle: { remove?: () => void } | undefined;
    let widthHandle: { remove?: () => void } | undefined;
    let extentHandle: { remove?: () => void } | undefined;
    let centerHandle: { remove?: () => void } | undefined;
    let zoomHandle: { remove?: () => void } | undefined;
    setMapError(null);
    setViewWidth(containerRef.current?.clientWidth || null);

    loadArcModules()
      .then((modules) => {
        if (cancelled || !containerRef.current) return;
        modulesRef.current = modules;
        const map = new modules.EsriMap({
          basemap: response.preview_config?.basemap || "streets-vector",
        });
        addContextLayers(map, contextLayers, modules);
        addDerivedOverlayLayers(map, loaded, modules);

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
            rotationEnabled: false,
          },
          navigation: locked
            ? {
                browserTouchPanEnabled: false,
                gamepadEnabled: false,
                momentumEnabled: false,
                mouseWheelZoomEnabled: false,
              }
            : undefined,
          ui: {
            components: locked ? ["attribution"] : ["attribution", "zoom"],
          },
        });
        view = nextView;
        viewRef.current = view;
        return nextView.when(() => {
          if (cancelled) return undefined;
          setViewScale(typeof nextView.scale === "number" ? nextView.scale : null);
          setViewWidth(typeof nextView.width === "number" ? nextView.width : containerRef.current?.clientWidth || null);
          scaleHandle = nextView.watch?.("scale", (value) => {
            if (!cancelled) setViewScale(typeof value === "number" && Number.isFinite(value) ? value : null);
          });
          widthHandle = nextView.watch?.("width", (value) => {
            if (!cancelled) setViewWidth(typeof value === "number" && Number.isFinite(value) ? value : null);
          });
          const emitState = () => {
            if (!cancelled) onViewStateChange?.(viewStateFromArcView(nextView));
          };
          extentHandle = nextView.watch?.("extent", emitState);
          centerHandle = nextView.watch?.("center", emitState);
          zoomHandle = nextView.watch?.("zoom", emitState);
          return nextView.goTo(extent, { animate: false }).finally(() => {
            emitState();
            if ((interactionMode === "print_locked" || interactionMode === "exhibit_locked") && typeof nextView.takeScreenshot === "function") {
              window.setTimeout(() => {
                if (cancelled) return;
                nextView
                  .takeScreenshot?.({ format: "png" })
                  .then((snapshot) => {
                    const dataUrl = snapshot?.dataUrl || snapshot?.data;
                    if (!cancelled && dataUrl) onSnapshotReady?.(dataUrl);
                  })
                  .catch(() => {
                    // Browser print can still use the locked live map if ArcGIS screenshot capture is unavailable.
                  });
              }, 450);
            }
          });
        });
      })
      .catch((exc) => {
        if (!cancelled) {
          setMapError(exc instanceof Error ? exc.message : "Map preview failed to load.");
        }
      });

    return () => {
      cancelled = true;
      scaleHandle?.remove?.();
      widthHandle?.remove?.();
      extentHandle?.remove?.();
      centerHandle?.remove?.();
      zoomHandle?.remove?.();
      if (viewRef.current) {
        viewRef.current.destroy();
        viewRef.current = null;
      } else if (view) {
        view.destroy();
      }
    };
  }, [
    contextLayers,
    derivedOverlays.length,
    interactionMode,
    loadError,
    loaded,
    loading,
    locked,
    onViewStateChange,
    onSnapshotReady,
    response.preview_config?.basemap,
    response.preview_config?.focus_extent,
    response.preview_config?.initial_extent,
  ]);

  useEffect(() => {
    if (!viewCommand || !viewRef.current || !modulesRef.current) return;
    const modules = modulesRef.current;
    const configuredExtent = numericExtent(response.preview_config?.focus_extent || response.preview_config?.initial_extent);
    const boundsForKind = (kind: ReturnType<typeof overlayKind>) =>
      featureCollectionBounds(loaded.filter((item) => overlayKind(item.overlay) === kind).map((item) => item.collection));
    const commandBounds =
      viewCommand.type === "reset_generated"
        ? configuredExtent
        : viewCommand.type === "center_origin"
          ? boundsForKind("origin")
          : viewCommand.type === "center_target"
            ? boundsForKind("target")
            : featureCollectionBounds(loaded.map((item) => item.collection));
    const [xmin, ymin, xmax, ymax] = bufferedBounds(commandBounds || configuredExtent);
    const extent = new modules.Extent({ xmin, ymin, xmax, ymax, spatialReference: WGS84 });
    viewRef.current.goTo(extent, { animate: true }).finally(() => {
      if (viewRef.current) onViewStateChange?.(viewStateFromArcView(viewRef.current));
    });
  }, [loaded, onViewStateChange, response.preview_config?.focus_extent, response.preview_config?.initial_extent, viewCommand]);

  if (!derivedOverlays.length && !contextLayers.length && packetId) {
    return <ArcGISMapPreview packetId={packetId} />;
  }

  const distance = distanceText(response);
  const lineLabel = routeLabel(response);
  const routeMode = response.proximity_result?.route_mode || "straight_line_fallback";
  const roadRoute = isRoadRouteMode(routeMode);
  const layout = mapLayout(response);
  const layoutTitle = layout?.title || response.map_title || panelTitle(response);
  const layoutSubtitle =
    layout?.subtitle ||
    (roadRoute ? "Road-following draft route. Not official navigation." : "Straight-line fallback. Road route unavailable.");
  const frameMode = frameModeForInteraction(interactionMode);
  const frameSizing = frameSizingForInteraction(interactionMode);
  const routeWarningText = roadRoute
    ? "Draft route based on public road centerlines. Not official navigation."
    : response.proximity_result?.route_warning || "Straight-line fallback only. Road route unavailable.";
  const routeWarning =
    !roadRoute ||
    Boolean(response.proximity_result?.route_warning) ||
    (response.proximity_result?.warnings || []).some((warning) => warning.toLowerCase().includes("not a driving route"));
  const propertyNotResolved = response.proximity_result?.property_match_status === "not_resolved";
  const fireEmsWarning = (response.proximity_result?.warnings || []).some((warning) => warning.toLowerCase().includes("fire") && warning.toLowerCase().includes("ems"));
  const clutterWarning = (response.warnings || []).some((warning) => warning.toLowerCase().includes("address layer hidden"));

  return (
    <div className={mapOnly ? "composer-derived-preview composer-map-only" : "composer-derived-preview page-stack"}>
      <section className="panel composer-derived-map-shell enterprise-map-shell">
        {!mapOnly ? (
          <div className="panel-title-row">
            <div>
              <p className="eyebrow">Focused ArcGIS map</p>
              <h3>Route and distance</h3>
              <p className="muted">{routeSummary(response, lineLabel, distance)}</p>
            </div>
            <div className="chip-row">
              <StatusChip tone="success">Real basemap</StatusChip>
              <StatusChip tone="success">Home marker</StatusChip>
              <StatusChip tone="success">Facility marker</StatusChip>
              <StatusChip tone={roadRoute ? "success" : "warning"}>{lineLabel}</StatusChip>
            </div>
          </div>
        ) : null}

        {!mapOnly && propertyNotResolved ? (
          <div className="inline-warning" role="status">
            Address matched. Related parcel was not resolved from verified fields, so the origin marker is shown as an address point.
          </div>
        ) : null}
        {!mapOnly && fireEmsWarning ? (
          <div className="inline-warning" role="status">
            The verified layer combines Fire and EMS stations; AutoMap could not confirm a fire-only filter.
          </div>
        ) : null}
        {!mapOnly && routeWarning ? (
          <div className="inline-warning" role="status">
            {routeWarningText}
          </div>
        ) : null}
        {!mapOnly && clutterWarning ? (
          <div className="inline-warning" role="status">
            Full address layer hidden to reduce clutter. The origin address marker remains visible.
          </div>
        ) : null}
        {loading ? <div className="preview-loading">Loading local origin, target, and line GeoJSON...</div> : null}
        {loadError ? <div className="preview-error">Map preview failed to load. {loadError}</div> : null}
        {mapError ? <div className="preview-error">Map preview failed to load. {mapError}</div> : null}

        <MapFrame
          mode={frameMode}
          locked={locked}
          title={layoutTitle}
          subtitle={layoutSubtitle}
          badge="Draft - local only"
          aspectRatio={frameSizing.aspectRatio}
          minHeight={frameSizing.minHeight}
          maxHeight={frameSizing.maxHeight}
        >
          <div className="composer-real-map" ref={containerRef} aria-label="Focused ArcGIS composer map preview" />
          {locked ? (
            <div className="map-interaction-blocker" aria-hidden="true" data-map-mode={interactionMode}>
              <span>{lockedModeLabel(interactionMode)}</span>
            </div>
          ) : null}
          <NorthArrow />
          <MapScaleBar scale={viewScale} mapWidth={viewWidth} />
          <MapLegend overlays={derivedOverlays} contextLayers={contextLayers} />
        </MapFrame>
      </section>

      {showLayerPanel ? <ComposerLayerPanel derivedOverlays={derivedOverlays} contextLayers={contextLayers} /> : null}
    </div>
  );
}
