"use client";

import type { CSSProperties } from "react";

type ScaleBarProps = {
  scale?: number | null;
};

const CANDIDATE_FEET = [50, 100, 200, 500, 1000, 1320, 2640, 5280, 10560, 26400, 52800];

function formatMiles(value: number): string {
  if (value < 1) return value.toFixed(2).replace(/0$/, "");
  if (value < 10) return value.toFixed(1).replace(/\.0$/, "");
  return String(Math.round(value));
}

function formatFeet(value: number): string {
  return String(Math.round(value));
}

function scaleDefinition(scale?: number | null) {
  if (!scale || !Number.isFinite(scale) || scale <= 0) {
    return { width: 132, midpoint: "0.25", end: "0.5 mi", aria: "Map scale bar 0 0.25 0.5 miles" };
  }

  const maxWidthPx = 150;
  const minWidthPx = 88;
  const feetPerPixel = scale / 1152;
  const maxFeet = feetPerPixel * maxWidthPx;
  const totalFeet = [...CANDIDATE_FEET].reverse().find((candidate) => candidate <= maxFeet) || 50;
  const width = Math.max(minWidthPx, Math.min(maxWidthPx, Math.round(totalFeet / feetPerPixel)));
  const midpointFeet = totalFeet / 2;

  if (totalFeet < 1320) {
    const midpoint = formatFeet(midpointFeet);
    const end = `${formatFeet(totalFeet)} ft`;
    return { width, midpoint, end, aria: `Map scale bar 0 ${midpoint} ${end}` };
  }

  const midpoint = formatMiles(midpointFeet / 5280);
  const end = `${formatMiles(totalFeet / 5280)} mi`;
  return { width, midpoint, end, aria: `Map scale bar 0 ${midpoint} ${end}` };
}

export function MapScaleBar({ scale }: ScaleBarProps) {
  const definition = scaleDefinition(scale);
  return (
    <div className="map-scale-bar" aria-label={definition.aria} style={{ "--scale-bar-width": `${definition.width}px` } as CSSProperties}>
      <div className="map-scale-bar-rule" aria-hidden="true">
        <span />
        <span />
      </div>
      <div className="map-scale-bar-ticks" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <div className="map-scale-bar-labels">
        <span>0</span>
        <span>{definition.midpoint}</span>
        <span>{definition.end}</span>
      </div>
    </div>
  );
}
