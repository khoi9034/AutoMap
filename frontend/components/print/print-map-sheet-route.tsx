"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { LockedMapSheetPage } from "@/components/print/LockedMapSheetPage";
import { PrintReportSections } from "@/components/print/PrintReportSections";
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

  useEffect(() => {
    const jobId = searchParams.get("job");
    if (!jobId) {
      setError("Print job is missing. Return to Print / Export and open Browser Print again.");
      return;
    }
    try {
      const raw = window.sessionStorage.getItem(printJobStorageKey(jobId));
      if (!raw) {
        setError("Print job expired. Return to Print / Export and open Browser Print again.");
        return;
      }
      const parsed = JSON.parse(raw) as unknown;
      if (!isPrintJobPayload(parsed)) {
        setError("Print job is incomplete. Reopen Adjust, lock the map, and try again.");
        return;
      }
      setPayload(parsed);
      setError(null);
    } catch {
      setError("Print job could not be loaded. Return to Print / Export and try again.");
    }
  }, [searchParams]);

  function printSheet() {
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
        <button className="button" type="button" onClick={printSheet}>
          Print this sheet
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
