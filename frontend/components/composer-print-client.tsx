"use client";

import { useEffect, useState } from "react";

import { ComposerMapPreview } from "@/components/composer-map-preview";
import { API_BASE_URL, getComposerSession } from "@/lib/api";
import type { ComposerResponse, PreviewLayer } from "@/types/automap";

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
  const layers: PreviewLayer[] = response?.preview_config?.context_layers || response?.preview_config?.operational_layers || [];
  const derivedLayers = response?.preview_config?.derived_overlays || [];
  const layout = response?.map_layout || response?.preview_config?.map_layout;
  const packetId = response?.adjusted_packet_id || response?.packet_id || response?.review_packet_id || undefined;
  const routeResult = response?.proximity_result;
  const generatedAt = response?.created_at ? new Date(response.created_at).toLocaleString() : new Date().toLocaleString();

  return (
    <main className="composer-print-page">
      <header>
        <p className="eyebrow">AutoMap draft print/export</p>
        <h1>{layout?.title || response?.map_title || "AutoMap Draft Map"}</h1>
        <p className="composer-print-subtitle">{layout?.subtitle || "Draft AutoMap preview, not an official county map."}</p>
        <p>{response?.raw_prompt || "Loading composer session..."}</p>
        <p className="muted">{layout?.disclaimer || "Draft only - not official county map. Not published to ArcGIS."} Not an official print map.</p>
        <p className="muted">Generated: {generatedAt}</p>
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

      {response?.can_preview ? (
        <section className="composer-print-map-section">
          <ComposerMapPreview response={response} packetId={packetId} />
        </section>
      ) : null}

      <section>
        <h2>Route and Distance Summary</h2>
        <dl className="status-list">
          <div>
            <dt>Route mode</dt>
            <dd>{layout?.route_mode_label || routeResult?.route_label || "Not a route map"}</dd>
          </div>
          <div>
            <dt>Distance</dt>
            <dd>
              {typeof routeResult?.distance_value === "number"
                ? `${routeResult.distance_value.toFixed(2)} ${routeResult.distance_unit || "miles"}`
                : "Not calculated"}
            </dd>
          </div>
          <div>
            <dt>Target</dt>
            <dd>{routeResult?.target_name || routeResult?.target_type || "Not applicable"}</dd>
          </div>
          <div>
            <dt>Disclaimer</dt>
            <dd>Draft only - not official driving navigation.</dd>
          </div>
        </dl>
      </section>

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
          <div>
            <dt>Print ready</dt>
            <dd>{layout?.print_ready ? "Yes" : "Needs review"}</dd>
          </div>
        </dl>
      </section>

      <section>
        <h2>Map Layers</h2>
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
            {derivedLayers.map((layer) => (
              <tr key={layer.id || layer.title}>
                <td>{layer.title}</td>
                <td>{layer.route_label || layer.role}</td>
                <td>{layer.visible === false ? "No" : "Yes"}</td>
                <td>1</td>
                <td>Local derived output</td>
              </tr>
            ))}
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
            ) : !derivedLayers.length ? (
              <tr>
                <td colSpan={5}>No preview layers available.</td>
              </tr>
            ) : null}
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
