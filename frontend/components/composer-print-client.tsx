"use client";

import { useEffect, useState } from "react";

import { ComposerMapPreview } from "@/components/composer-map-preview";
import { ExhibitLayout } from "@/components/exhibit-layout";
import { API_BASE_URL, getComposerSession } from "@/lib/api";
import type { ComposerResponse } from "@/types/automap";

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

  useEffect(() => {
    getComposerSession(sessionId)
      .then(setResponse)
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Composer print session failed."));
  }, [sessionId]);

  const packetId = response?.adjusted_packet_id || response?.packet_id || response?.review_packet_id || undefined;

  if (error) {
    return (
      <main className="composer-print-page exhibit-layout">
        <section className="panel">
          <h1>Print layout unavailable</h1>
          <p className="error-text">{error}</p>
        </section>
      </main>
    );
  }

  if (!response) {
    return (
      <main className="composer-print-page exhibit-layout">
        <section className="panel">
          <h1>Loading print layout</h1>
          <p className="muted">AutoMap is loading the local composer session.</p>
        </section>
      </main>
    );
  }

  const actions = (
    <div className="button-row">
      <button className="button" type="button" onClick={() => window.print()}>
        Print Draft Map
      </button>
      {response.webmap_path ? (
        <a className="button button-secondary" href={localFileUrl(response.webmap_path)} target="_blank" rel="noreferrer">
          Open WebMap JSON
        </a>
      ) : null}
    </div>
  );

  return (
    <ExhibitLayout
      response={response}
      sessionId={sessionId}
      actions={actions}
      map={
        response.can_preview ? (
          <ComposerMapPreview response={response} packetId={packetId} />
        ) : (
          <div className="preview-error">
            <strong>Preview is not ready.</strong>
            <p>{warningList(response)[0] || "Generate a preview-ready composer session before printing."}</p>
          </div>
        )
      }
    />
  );
}
