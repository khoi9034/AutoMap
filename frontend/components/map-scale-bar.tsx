"use client";

import type { CSSProperties } from "react";

type ScaleBarProps = {
  scale?: number | null;
  mapWidth?: number | null;
};

const CANDIDATE_FEET = [50, 100, 200, 500, 1000, 1320, 2640, 5280, 10560, 26400, 52800];
const ENTERPRISE_WIDTH_PERCENT = 64;

function formatMiles(value: number): string {
  if (value < 1) return value.toFixed(2).replace(/0$/, "");
  if (value < 10) return value.toFixed(1).replace(/\.0$/, "");
  return String(Math.round(value));
}

function formatFeet(value: number): string {
  return String(Math.round(value));
}

function scaleDefinition(scale?: number | null, mapWidth?: number | null) {
  if (!scale || !Number.isFinite(scale) || scale <= 0) {
    return {
      widthPercent: ENTERPRISE_WIDTH_PERCENT,
      midpoint: "0.25",
      end: "0.5 mi",
      aria: "Map scale bar centered enterprise 0 0.25 0.5 miles",
    };
  }

  const representativeMapWidthPx = typeof mapWidth === "number" && Number.isFinite(mapWidth) && mapWidth > 0 ? mapWidth : 900;
  const barPixelWidth = Math.max(240, representativeMapWidthPx * (ENTERPRISE_WIDTH_PERCENT / 100));
  const feetPerPixel = scale / 1152;
  const maxFeet = feetPerPixel * barPixelWidth;
  const totalFeet = [...CANDIDATE_FEET].reverse().find((candidate) => candidate <= maxFeet) || 50;
  const midpointFeet = totalFeet / 2;

  if (totalFeet < 1320) {
    const midpoint = formatFeet(midpointFeet);
    const end = `${formatFeet(totalFeet)} ft`;
    return {
      widthPercent: ENTERPRISE_WIDTH_PERCENT,
      midpoint,
      end,
      aria: `Map scale bar centered enterprise 0 ${midpoint} ${end}`,
    };
  }

  const midpoint = formatMiles(midpointFeet / 5280);
  const end = `${formatMiles(totalFeet / 5280)} mi`;
  return {
    widthPercent: ENTERPRISE_WIDTH_PERCENT,
    midpoint,
    end,
    aria: `Map scale bar centered enterprise 0 ${midpoint} ${end}`,
  };
}

export function MapScaleBar({ scale, mapWidth }: ScaleBarProps) {
  const definition = scaleDefinition(scale, mapWidth);
  return (
    <div
      className="map-scale-bar map-scale-bar-centered"
      aria-label={definition.aria}
      style={{ "--scale-bar-width": `${definition.widthPercent}%` } as CSSProperties}
    >
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
