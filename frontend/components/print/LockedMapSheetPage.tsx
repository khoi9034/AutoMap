"use client";

/* eslint-disable @next/next/no-img-element */

import type { ReactNode, CSSProperties } from "react";

import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import { effectiveSheetDimensions, type LivePrintOptions } from "@/types/print-options";

type LockedMapSheetPageProps = {
  mapFallback?: ReactNode;
  mapState?: ComposerMapState | null;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
  snapshotDataUrl?: string | null;
};

function routeSummary(response: ComposerResponse | null, mapState?: ComposerMapState | null): string {
  const proximity = mapState?.proximity_summary || response?.proximity_result;
  if (!proximity) return "Draft preview only.";
  const distance =
    typeof proximity.distance_value === "number"
      ? `${proximity.distance_value.toFixed(2)} ${proximity.distance_unit || "miles"}`
      : "distance not calculated";
  const roadRoute = proximity.route_mode === "road_network" || proximity.nearest_facility_method === "road_distance";
  const label = roadRoute ? "Road-following draft route" : proximity.route_label || proximity.route_mode || "Route draft";
  return `${label} - ${distance}`;
}

function sheetMarginValue(printOptions: LivePrintOptions): string {
  if (printOptions.sheetMargin === "none") return "10px";
  if (printOptions.sheetMargin === "standard") return "30px";
  return "18px";
}

export function LockedMapSheetPage({ mapFallback, mapState, printOptions, response, snapshotDataUrl }: LockedMapSheetPageProps) {
  const title = mapState?.map_title || response?.map_title || "AutoMap Draft Exhibit";
  const subtitle = mapState?.map_subtitle || response?.map_layout?.subtitle || response?.preview_config?.map_layout?.subtitle || "Draft preview only.";
  const sheetDimensions = effectiveSheetDimensions(printOptions);
  const fixedScale =
    printOptions.scaleMode === "fixed_scale"
      ? printOptions.fixedScale === "custom"
        ? `1:${printOptions.customScale.toLocaleString()}`
        : `1:${Number(printOptions.fixedScale).toLocaleString()}`
      : "Fit locked extent";
  const sheetStyle = {
    "--sheet-aspect-ratio": `${sheetDimensions.width} / ${sheetDimensions.height}`,
    "--sheet-margin-preview": sheetMarginValue(printOptions),
    "--print-width": `${sheetDimensions.width}in`,
    "--print-height": `${sheetDimensions.height}in`,
  } as CSSProperties;
  const classes = [
    "print-preview-sheet",
    "print-map-page-preview",
    "locked-map-sheet-page",
    "print-sheet-sized",
    `print-sheet-mode-${printOptions.exportMode}`,
    `print-sheet-margin-${printOptions.sheetMargin}`,
    `print-sheet-orientation-${printOptions.sheetOrientation}`,
    printOptions.includeTitle ? "print-furniture-title" : null,
    printOptions.includeSubtitle ? "print-furniture-subtitle" : null,
    printOptions.includeLegend ? "print-furniture-legend" : null,
    printOptions.includeScaleBar ? "print-furniture-scale" : null,
    printOptions.includeNorthArrow ? "print-furniture-north" : null,
    printOptions.includeSourceNote ? "print-furniture-source" : null,
    printOptions.includeDraftWatermark ? "print-furniture-watermark" : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section className={classes} data-locked-map-state="true" style={sheetStyle}>
      {printOptions.includeTitle || printOptions.includeSubtitle || printOptions.includeDraftDisclaimer ? (
        <header className="print-preview-title-block">
          <div>
            <p className="eyebrow">{printOptions.exportMode === "map_sheet" ? "Map Sheet" : "Map Exhibit"}</p>
            {printOptions.includeTitle ? <h1>{title}</h1> : null}
            {printOptions.includeSubtitle ? <p>{subtitle}</p> : null}
          </div>
          {printOptions.includeDraftDisclaimer ? <strong>DRAFT - For GIS review only</strong> : null}
        </header>
      ) : null}
      <div className="print-preview-map-frame">
        {printOptions.includeDraftWatermark ? <span className="print-preview-watermark">DRAFT</span> : null}
        {snapshotDataUrl ? (
          <img
            className="print-map-snapshot print-static-map-image"
            alt="Locked map snapshot for browser print"
            src={snapshotDataUrl}
            data-print-snapshot="true"
          />
        ) : (
          mapFallback || <div className="print-snapshot-missing">Print snapshot is required before this map sheet can be printed.</div>
        )}
      </div>
      <footer className="print-preview-map-notes">
        {printOptions.includeSourceNote ? <span>{routeSummary(response, mapState)}</span> : null}
        {printOptions.includeScopeNote ? <span>Scope: Cabarrus County, NC</span> : null}
        {printOptions.includeRealPublishNote ? <span>Local only - no ArcGIS item published.</span> : null}
        <span>
          Sheet: {sheetDimensions.width} x {sheetDimensions.height} in, {fixedScale}
        </span>
      </footer>
    </section>
  );
}
