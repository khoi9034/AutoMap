import { SharedMapRenderer } from "@/components/map-renderer/shared-map-renderer";
import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

type PrintMapPagePreviewProps = {
  mapState?: ComposerMapState | null;
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

export function PrintMapPagePreview({ mapState, packetId, printOptions, response }: PrintMapPagePreviewProps) {
  const title = mapState?.map_title || response?.map_title || "AutoMap Draft Exhibit";
  const subtitle = mapState?.map_subtitle || response?.map_layout?.subtitle || response?.preview_config?.map_layout?.subtitle || "Draft preview only.";
  return (
    <section className="print-preview-sheet print-map-page-preview" data-locked-map-state="true">
      <header className="print-preview-title-block">
        <div>
          <p className="eyebrow">Map Exhibit</p>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        {printOptions.includeDraftDisclaimer ? <strong>DRAFT - For GIS review only</strong> : null}
      </header>
      <div className="print-preview-map-frame">
        <SharedMapRenderer mode="print" mapState={mapState} response={response} packetId={packetId} showLayerPanel={false} />
      </div>
      <footer className="print-preview-map-notes">
        <span>{routeSummary(response, mapState)}</span>
        <span>Local only - no ArcGIS item published.</span>
      </footer>
    </section>
  );
}
