import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

import { PrintReportSections } from "@/components/print/PrintReportSections";

import { PrintMapPagePreview } from "./print-map-page-preview";

type PrintDocumentPreviewProps = {
  mapState?: ComposerMapState | null;
  onSnapshotReady?: (dataUrl: string) => void;
  packetId?: string;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
};

export function PrintDocumentPreview({ mapState, onSnapshotReady, packetId, printOptions, response }: PrintDocumentPreviewProps) {
  return (
    <article className={`print-document-preview print-document-preview-${printOptions.exportMode}`}>
      <PrintMapPagePreview mapState={mapState} onSnapshotReady={onSnapshotReady} packetId={packetId} printOptions={printOptions} response={response} />
      <PrintReportSections mapState={mapState} printOptions={printOptions} response={response} />
    </article>
  );
}
