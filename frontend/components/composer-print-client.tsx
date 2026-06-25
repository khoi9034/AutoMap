"use client";

import { useEffect, useState } from "react";

import { MapSheetDocument } from "@/components/print-preview/map-sheet-document";
import { API_BASE_URL, getComposerSession } from "@/lib/api";
import type { ComposerResponse } from "@/types/automap";
import { backendExportOptionsToPrintOptions } from "@/types/print-options";

function localFileUrl(path?: string | null): string {
  return path ? `${API_BASE_URL}/local-file?path=${encodeURIComponent(path)}` : "#";
}

function warningList(response: ComposerResponse | null): string[] {
  return [
    ...(response?.warnings || []),
    ...(response?.preview_blockers || []),
    ...(response?.missing_data || []).map((item) => `Missing data: ${item}`),
  ];
}

export function ComposerPrintClient({ sessionId }: { sessionId: string }) {
  const [response, setResponse] = useState<ComposerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [printWarning, setPrintWarning] = useState<string | null>(null);
  const [snapshotReady, setSnapshotReady] = useState(false);

  useEffect(() => {
    getComposerSession(sessionId)
      .then(setResponse)
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Composer print session failed."));
  }, [sessionId]);

  const packetId = response?.adjusted_packet_id || response?.packet_id || response?.review_packet_id || undefined;
  const lockedMapState = response?.composer_map_state || null;

  if (error) {
    return (
      <main className="composer-print-route">
        <section className="panel">
          <h1>Print layout unavailable</h1>
          <p className="error-text">{error}</p>
        </section>
      </main>
    );
  }

  if (!response) {
    return (
      <main className="composer-print-route">
        <section className="panel">
          <h1>Loading print layout</h1>
          <p className="muted">AutoMap is loading the local composer session.</p>
        </section>
      </main>
    );
  }

  async function openBrowserPrint() {
    if (!lockedMapState) {
      setPrintWarning("Lock final map before printing.");
      return;
    }
    if (!snapshotReady) {
      setPrintWarning("Print snapshot could not be created yet; Print Map may vary.");
    } else {
      setPrintWarning(null);
    }
    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
    window.print();
  }

  const actions = (
    <div className="button-row print-route-actions no-print">
      <button className="button" type="button" onClick={openBrowserPrint} disabled={!lockedMapState}>
        Print Map
      </button>
      {response.webmap_path ? (
        <details className="advanced-export-panel">
          <summary>Advanced exports</summary>
          <a className="button button-secondary" href={localFileUrl(response.webmap_path)} target="_blank" rel="noreferrer">
            Open WebMap JSON
          </a>
        </details>
      ) : null}
    </div>
  );
  const printOptions = backendExportOptionsToPrintOptions(response.composer_map_state?.export_options, response.composer_map_state?.report_section_config);

  return (
    <main className="composer-print-route">
      {actions}
      {printWarning ? <div className="inline-warning no-print">{printWarning}</div> : null}
      {response.can_preview ? (
        <MapSheetDocument
          mapState={lockedMapState}
          onSnapshotReady={() => setSnapshotReady(true)}
          packetId={packetId}
          printOptions={printOptions}
          response={response}
        />
      ) : (
        <div className="preview-error">
          <strong>Preview is not ready.</strong>
          <p>{warningList(response)[0] || "Generate a preview-ready composer session before printing."}</p>
        </div>
      )}
    </main>
  );
}
