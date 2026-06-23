import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

import { PrintDocumentPreview } from "./print-document-preview";

type MapSheetDocumentProps = {
  mapState?: ComposerMapState | null;
  packetId?: string;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
  onSnapshotReady?: (dataUrl: string) => void;
};

export function MapSheetDocument({ mapState, packetId, printOptions, response, onSnapshotReady }: MapSheetDocumentProps) {
  return (
    <div id="automap-print-root" className="automap-print-document" data-print-root="true">
      <PrintDocumentPreview
        mapState={mapState}
        onSnapshotReady={onSnapshotReady}
        packetId={packetId}
        printOptions={printOptions}
        response={response}
      />
    </div>
  );
}
