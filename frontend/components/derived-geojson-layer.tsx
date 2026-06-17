"use client";

import type { DerivedOverlay, JsonValue } from "@/types/automap";

type GeoJsonGeometry = {
  type?: string;
  coordinates?: JsonValue;
};

export type GeoJsonFeature = {
  type?: string;
  properties?: Record<string, JsonValue>;
  geometry?: GeoJsonGeometry | null;
};

export type GeoJsonFeatureCollection = {
  type?: string;
  features?: GeoJsonFeature[];
};

type Projector = (coordinate: [number, number]) => [number, number];

function asNumberPair(value: unknown): [number, number] | null {
  if (!Array.isArray(value) || value.length < 2) return null;
  const x = Number(value[0]);
  const y = Number(value[1]);
  return Number.isFinite(x) && Number.isFinite(y) ? [x, y] : null;
}

function coordinatePairs(value: unknown): Array<[number, number]> {
  const pair = asNumberPair(value);
  if (pair) return [pair];
  if (!Array.isArray(value)) return [];
  return value.flatMap((item) => coordinatePairs(item));
}

export function featureCollectionBounds(collections: GeoJsonFeatureCollection[]): [number, number, number, number] | null {
  const pairs = collections.flatMap((collection) =>
    (collection.features || []).flatMap((feature) => coordinatePairs(feature.geometry?.coordinates)),
  );
  if (!pairs.length) return null;
  return pairs.reduce(
    (bounds, [x, y]) => [Math.min(bounds[0], x), Math.min(bounds[1], y), Math.max(bounds[2], x), Math.max(bounds[3], y)],
    [pairs[0][0], pairs[0][1], pairs[0][0], pairs[0][1]],
  );
}

function pathFromCoordinates(value: unknown, project: Projector, close = false): string {
  const points = coordinatePairs(value).map(project);
  if (!points.length) return "";
  const [first, ...rest] = points;
  const segments = [`M ${first[0].toFixed(2)} ${first[1].toFixed(2)}`];
  rest.forEach(([x, y]) => segments.push(`L ${x.toFixed(2)} ${y.toFixed(2)}`));
  if (close) segments.push("Z");
  return segments.join(" ");
}

function overlayColor(overlay: DerivedOverlay, fallback: string): string {
  const color = overlay.symbol?.color;
  return typeof color === "string" ? color : fallback;
}

export function DerivedGeoJsonLayer({
  overlay,
  collection,
  project,
}: {
  overlay: DerivedOverlay;
  collection: GeoJsonFeatureCollection;
  project: Projector;
}) {
  const role = (overlay.role || "").toLowerCase();
  const color = overlayColor(overlay, role.includes("target") ? "#dc2626" : role.includes("line") ? "#2563eb" : "#0ea5a3");
  const width = typeof overlay.symbol?.width === "number" ? overlay.symbol.width : 4;
  const size = typeof overlay.symbol?.size === "number" ? overlay.symbol.size : 12;

  return (
    <g className={`derived-geojson-layer derived-geojson-${role || "overlay"}`}>
      {(collection.features || []).map((feature, index) => {
        const geometry = feature.geometry;
        const key = `${overlay.id || overlay.title || "overlay"}-${index}`;
        if (!geometry) return null;
        if (geometry.type === "Point") {
          const point = asNumberPair(geometry.coordinates);
          if (!point) return null;
          const [cx, cy] = project(point);
          if (role.includes("target")) {
            return <rect key={key} x={cx - size / 2} y={cy - size / 2} width={size} height={size} fill={color} stroke="#ffffff" strokeWidth="2" transform={`rotate(45 ${cx} ${cy})`} />;
          }
          return <circle key={key} cx={cx} cy={cy} r={size / 2} fill={color} stroke="#ffffff" strokeWidth="2.5" />;
        }
        if (geometry.type === "LineString" || geometry.type === "MultiLineString") {
          return <path key={key} d={pathFromCoordinates(geometry.coordinates, project)} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" />;
        }
        if (geometry.type === "Polygon") {
          const rings = Array.isArray(geometry.coordinates) ? geometry.coordinates : [];
          return rings.map((ring, ringIndex) => (
            <path key={`${key}-${ringIndex}`} d={pathFromCoordinates(ring, project, true)} fill="rgba(245,158,11,0.16)" stroke={color} strokeWidth={width} />
          ));
        }
        if (geometry.type === "MultiPolygon") {
          const polygons = Array.isArray(geometry.coordinates) ? geometry.coordinates : [];
          return polygons.flatMap((polygon, polygonIndex) =>
            (Array.isArray(polygon) ? polygon : []).map((ring, ringIndex) => (
              <path key={`${key}-${polygonIndex}-${ringIndex}`} d={pathFromCoordinates(ring, project, true)} fill="rgba(245,158,11,0.16)" stroke={color} strokeWidth={width} />
            )),
          );
        }
        return null;
      })}
    </g>
  );
}
