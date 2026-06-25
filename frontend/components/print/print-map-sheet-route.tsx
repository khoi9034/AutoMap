"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { LockedMapSheetPage } from "@/components/print/LockedMapSheetPage";
import { PrintReportSections } from "@/components/print/PrintReportSections";
import { loadComposerSession, loadLockedMapState } from "@/lib/composer-session-store";
import { validatePrintSnapshot } from "@/lib/print-snapshot";
import type { PrintJobPayload } from "@/types/print-job";
import { printJobStorageKey } from "@/types/print-job";

function isPrintJobPayload(value: unknown): value is PrintJobPayload {
  const payload = value as PrintJobPayload;
  return Boolean(
    payload &&
      typeof payload === "object" &&
      payload.jobId &&
      payload.locked_map_state &&
      payload.map_snapshot_data_url &&
      payload.print_options &&
      payload.response,
  );
}

export function PrintMapSheetRoute() {
  const searchParams = useSearchParams();
  const [payload, setPayload] = useState<PrintJobPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [imageReady, setImageReady] = useState(false);

  useEffect(() => {
    const jobId = searchParams.get("job");
    if (!jobId) {
      setError("Print job is missing. Return to Print / Export and choose Print Map again.");
      return;
    }
    try {
      const sessionId = searchParams.get("session");
      const storageKey = printJobStorageKey(jobId);
      const raw = window.sessionStorage.getItem(storageKey) || window.localStorage.getItem(storageKey);
      if (!raw) {
        if (sessionId && loadLockedMapState(sessionId)) {
          const stored = loadComposerSession(sessionId);
          setError(
            stored
              ? "Print snapshot expired, but the final map state is saved. Return to Print / Export and choose Print Map again."
              : "Final map state expired. Return to Map Composer and lock the map again.",
          );
          return;
        }
        setError("Print job expired. Return to Print / Export and choose Print Map again.");
        return;
      }
      const parsed = JSON.parse(raw) as unknown;
      if (!isPrintJobPayload(parsed)) {
        setError("Print job is incomplete. Reopen Adjust, lock the map, and try again.");
        return;
      }
      setPayload(parsed);
      setError(null);
      setImageReady(false);
    } catch {
      setError("Print job could not be loaded. Return to Print / Export and try again.");
    }
  }, [searchParams]);

  useEffect(() => {
    if (!payload?.map_snapshot_data_url) return;
    let cancelled = false;
    validatePrintSnapshot(payload.map_snapshot_data_url).then((validation) => {
      if (!cancelled) {
        setImageReady(validation.ok);
        if (!validation.ok) {
          setError("Print snapshot is still loading or invalid. Return to Print / Export and regenerate the print snapshot.");
        }
      }
    });
    return () => {
      cancelled = true;
    };
  }, [payload?.map_snapshot_data_url]);

  function printSheet() {
    if (!imageReady) return;
    window.print();
  }

  if (error) {
    return (
      <main className="print-only-route">
        <section className="panel print-only-error">
          <p className="eyebrow">AutoMap Print</p>
          <h1>Print sheet unavailable</h1>
          <p>{error}</p>
        </section>
      </main>
    );
  }

  if (!payload) {
    return (
      <main className="print-only-route">
        <section className="panel print-only-error">
          <p className="eyebrow">AutoMap Print</p>
          <h1>Loading print sheet</h1>
          <p>Preparing the locked map sheet.</p>
        </section>
      </main>
    );
  }

  return (
    <main className="print-only-route">
      <div className="print-only-toolbar no-print">
        <div>
          <p className="eyebrow">Print-only route</p>
          <h1>Locked map sheet</h1>
          <p>Page 1 is the map sheet. Summary and report pages, when selected, start after it.</p>
        </div>
        <button className="button" type="button" onClick={printSheet} disabled={!imageReady}>
          {imageReady ? "Print Map" : "Preparing snapshot..."}
        </button>
      </div>
      <div id="automap-print-root" className="automap-print-document print-only-document" data-print-root="true">
        <article className={`print-document-preview print-document-preview-${payload.print_options.exportMode}`}>
          <LockedMapSheetPage
            mapState={payload.locked_map_state}
            printOptions={payload.print_options}
            response={payload.response}
            snapshotDataUrl={payload.map_snapshot_data_url}
          />
          <PrintReportSections mapState={payload.locked_map_state} printOptions={payload.print_options} response={payload.response} />
        </article>
      </div>
    </main>
  );
}
