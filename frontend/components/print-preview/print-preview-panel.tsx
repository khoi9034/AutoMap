import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

import { MapSheetDocument } from "./map-sheet-document";

type PrintPreviewPanelProps = {
  mapState?: ComposerMapState | null;
  packetId?: string;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
};

export function PrintPreviewPanel({ mapState, packetId, printOptions, response }: PrintPreviewPanelProps) {
  return (
    <section className="print-preview-panel" aria-label="Live Print Preview">
      <div className="print-preview-panel-header">
        <div>
          <p className="eyebrow">Live Print Preview</p>
          <h3>Final printout</h3>
        </div>
        <span>Updates live</span>
      </div>
      <div className="print-preview-scroll">
        <MapSheetDocument mapState={mapState} packetId={packetId} printOptions={printOptions} response={response} />
      </div>
    </section>
  );
}
