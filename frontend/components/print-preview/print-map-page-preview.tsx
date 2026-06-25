"use client";

import { SharedMapRenderer } from "@/components/map-renderer/shared-map-renderer";
import { LockedMapSheetPage } from "@/components/print/LockedMapSheetPage";
import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";
import { useState } from "react";

type PrintMapPagePreviewProps = {
  mapState?: ComposerMapState | null;
  onSnapshotReady?: (dataUrl: string) => void;
  packetId?: string;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
};

export function PrintMapPagePreview({ mapState, onSnapshotReady, packetId, printOptions, response }: PrintMapPagePreviewProps) {
  const [snapshotUrl, setSnapshotUrl] = useState<string | null>(null);
  const handleSnapshotReady = (dataUrl: string) => {
    setSnapshotUrl(dataUrl);
    onSnapshotReady?.(dataUrl);
  };
  const liveMapFallback = (
    <SharedMapRenderer
      mode="print_locked"
      mapOnly
      mapState={mapState}
      onSnapshotReady={handleSnapshotReady}
      response={response}
      packetId={packetId}
      showLayerPanel={false}
    />
  );
  return (
    <LockedMapSheetPage
      mapFallback={liveMapFallback}
      mapState={mapState}
      printOptions={printOptions}
      response={response}
      snapshotDataUrl={snapshotUrl}
    />
  );
}
