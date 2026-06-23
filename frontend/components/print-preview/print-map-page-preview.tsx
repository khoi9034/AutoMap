"use client";

/* eslint-disable @next/next/no-img-element */

import { SharedMapRenderer } from "@/components/map-renderer/shared-map-renderer";
import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import { effectiveSheetDimensions, type LivePrintOptions } from "@/types/print-options";
import { useState, type CSSProperties } from "react";

type PrintMapPagePreviewProps = {
  mapState?: ComposerMapState | null;
  onSnapshotReady?: (dataUrl: string) => void;
  packetId?: string;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
};

function routeSummary(response: ComposerResponse | null, mapState?: ComposerMapState | null): string {
  const proximity = mapState?.proximity_summary || response?.proximity_result;
  if (!proximity) return "Draft preview only.";
  const distance =
    typeof proximity.distance_value === "number"
      ? `${proximity.distance_value.toFixed(2)} ${proximity.distance_unit || "miles"}`
      : "distance not calculated";
  return `${proximity.route_label || proximity.route_mode || "Route draft"} - ${distance}`;
}

export function PrintMapPagePreview({ mapState, onSnapshotReady, packetId, printOptions, response }: PrintMapPagePreviewProps) {
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const title = mapState?.map_title || response?.map_title || "AutoMap Draft Exhibit";
  const subtitle = mapState?.map_subtitle || response?.map_layout?.subtitle || response?.preview_config?.map_layout?.subtitle || "Draft preview only.";
  const sheetDimensions = effectiveSheetDimensions(printOptions);
  const sheetMargin = printOptions.sheetMargin === "none" ? "10px" : printOptions.sheetMargin === "standard" ? "30px" : "18px";
  const fixedScale =
    printOptions.scaleMode === "fixed_scale"
      ? printOptions.fixedScale === "custom"
        ? `1:${printOptions.customScale.toLocaleString()}`
        : `1:${Number(printOptions.fixedScale).toLocaleString()}`
      : "Fit locked extent";
  const sheetStyle = {
    "--sheet-aspect-ratio": `${sheetDimensions.width} / ${sheetDimensions.height}`,
    "--sheet-margin-preview": sheetMargin,
    "--print-width": `${sheetDimensions.width}in`,
    "--print-height": `${sheetDimensions.height}in`,
  } as CSSProperties;
  const classes = [
    "print-preview-sheet",
    "print-map-page-preview",
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
  const handleSnapshotReady = (dataUrl: string) => {
    setSnapshotUrl(dataUrl);
    onSnapshotReady?.(dataUrl);
  };
  return (
    <section className={classes} data-locked-map-state="true" style={sheetStyle}>
      {(printOptions.includeTitle || printOptions.includeSubtitle || printOptions.includeDraftDisclaimer) ? (
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
        {snapshotUrl ? (
          <img className="print-map-snapshot" alt="Locked map snapshot for browser print" src={snapshotUrl} data-print-snapshot="true" />
        ) : null}
        <SharedMapRenderer
          mode="print_locked"
          mapState={mapState}
          onSnapshotReady={handleSnapshotReady}
          response={response}
          packetId={packetId}
          showLayerPanel={false}
        />
      </div>
      <footer className="print-preview-map-notes">
        {printOptions.includeSourceNote ? <span>{routeSummary(response, mapState)}</span> : null}
        {printOptions.includeScopeNote ? <span>Scope: Cabarrus County, NC</span> : null}
        {printOptions.includeRealPublishNote ? <span>Local only - no ArcGIS item published.</span> : null}
        <span>Sheet: {sheetDimensions.width} x {sheetDimensions.height} in, {fixedScale}</span>
      </footer>
    </section>
  );
}
