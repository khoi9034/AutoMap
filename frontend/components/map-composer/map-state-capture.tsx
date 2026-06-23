"use client";

import type { ComposerResponse, ExportMode } from "@/types/automap";

type MapStateCaptureProps = {
  response: ComposerResponse | null;
  exportMode: ExportMode;
};

export function MapStateCapture({ response, exportMode }: MapStateCaptureProps) {
  const state = response?.composer_map_state;
  const layerCount = (state?.visible_layers || []).length;
  const extentReady = Boolean(state?.map_extent || response?.preview_config?.focus_extent || response?.preview_config?.initial_extent);
  return (
    <div className="map-state-capture">
      <strong>Exact composer state</strong>
      <span>{exportMode === "full_report" ? "Full report appendix enabled" : exportMode === "map_sheet" ? "Standalone map sheet" : "Map exhibit first"}</span>
      <span>{layerCount} visible layer{layerCount === 1 ? "" : "s"}</span>
      <span>{extentReady ? "Extent saved" : "Extent pending"}</span>
    </div>
  );
}
