"use client";

import { useEffect, useState } from "react";

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

  const warnings = warningList(response);
  const layers = response?.preview_config?.operational_layers || [];

  return (
    <main className="composer-print-page">
      <header>
        <p className="eyebrow">AutoMap draft print/export</p>
        <h1>{response?.map_title || "AutoMap Draft Map"}</h1>
        <p>{response?.raw_prompt || "Loading composer session..."}</p>
        <p className="muted">Draft-only local output. Not an official print map and not published to ArcGIS.</p>
        <div className="button-row no-print">
          <button className="button" type="button" onClick={() => window.print()} disabled={!response}>
            Print Draft Map
          </button>
          {response?.webmap_path ? (
            <a className="button button-secondary" href={localFileUrl(response.webmap_path)} target="_blank" rel="noreferrer">
              Open WebMap JSON
            </a>
          ) : null}
        </div>
      </header>

      {error ? <p className="error-text">{error}</p> : null}

      <section>
        <h2>Preview Status</h2>
        <dl className="status-list">
          <div>
            <dt>Composer session</dt>
            <dd>{sessionId}</dd>
          </div>
          <div>
            <dt>Can preview</dt>
            <dd>{response?.can_preview ? "Yes" : "No"}</dd>
          </div>
          <div>
            <dt>Parcel match</dt>
            <dd>{response?.parcel_context?.match_status || "Not parcel-focused"}</dd>
          </div>
          <div>
            <dt>Packet</dt>
            <dd>{response?.packet_id || "No packet"}</dd>
          </div>
        </dl>
      </section>

      <section>
        <h2>Selected Layers</h2>
        <table>
          <thead>
            <tr>
              <th>Layer</th>
              <th>Role</th>
              <th>Visible</th>
              <th>Opacity</th>
              <th>Definition</th>
            </tr>
          </thead>
          <tbody>
            {layers.length ? (
              layers.map((layer) => (
                <tr key={layer.id || layer.layer_key || layer.title}>
                  <td>{layer.title}</td>
                  <td>{layer.role}</td>
                  <td>{layer.visibility === false ? "No" : "Yes"}</td>
                  <td>{layer.opacity}</td>
                  <td>{layer.definition_expression || ""}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={5}>No preview layers available.</td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <section>
        <h2>Warnings</h2>
        {warnings.length ? (
          <ul>
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        ) : (
          <p>No warnings recorded.</p>
        )}
      </section>
    </main>
  );
}
