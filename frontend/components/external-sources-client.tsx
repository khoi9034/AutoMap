"use client";

import { useEffect, useMemo, useState } from "react";

import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { getExternalSources, inspectExternalSources, loadExternalSources } from "@/lib/api";
import type { ExternalSource, JsonValue } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

function toneForStatus(status?: string): "default" | "success" | "warning" | "danger" {
  if (status === "approved" || status === "active") {
    return "success";
  }
  if (status === "candidate" || status === "needs_review" || status === "proxy" || status === "reference") {
    return "warning";
  }
  if (status === "failed" || status === "rejected") {
    return "danger";
  }
  return "default";
}

function metadataValue(metadata: Record<string, JsonValue> | undefined, key: string): string {
  const value = metadata?.[key];
  if (value === null || value === undefined) {
    return "not recorded";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value);
}

export function ExternalSourcesClient() {
  const [sources, setSources] = useState<ExternalSource[]>([]);
  const [selectedKey, setSelectedKey] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  async function refresh() {
    const response = await getExternalSources();
    setSources(response.external_sources || []);
  }

  useEffect(() => {
    refresh().catch((exc) => setError(exc instanceof Error ? exc.message : "External sources failed to load."));
  }, []);

  async function onLoad() {
    setLoading("load");
    setError(null);
    try {
      const result = await loadExternalSources();
      setSources(result.sources || []);
      setToast({ tone: "success", message: `Loaded ${result.loaded} external source records.` });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "External source loading failed.");
    } finally {
      setLoading(null);
    }
  }

  async function onInspect() {
    setLoading("inspect");
    setError(null);
    try {
      const result = await inspectExternalSources();
      setSources(result.sources || []);
      setToast({
        tone: "success",
        message: `Inspected ${result.inspected} sources; ${result.catalog_upserts} verified layer rows upserted.`,
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "External source inspection failed.");
    } finally {
      setLoading(null);
    }
  }

  const selectedSource = useMemo(
    () => sources.find((source) => source.source_key === selectedKey) || sources[0],
    [selectedKey, sources],
  );

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Candidate and proxy source review</strong>
        <p>
          AutoMap can inspect source metadata, fields, domains, counts, and small non-geometry samples only. Proxy
          sources remain context layers and are not official permit issuance, development approval, utility capacity, or
          final planning action records.
        </p>
      </section>

      <div className="button-row">
        <button className="button" type="button" onClick={onLoad} disabled={loading !== null}>
          {loading === "load" ? "Loading..." : "Load Seed Sources"}
        </button>
        <button className="button button-secondary" type="button" onClick={onInspect} disabled={loading !== null}>
          {loading === "inspect" ? "Inspect Metadata" : "Inspect Metadata"}
        </button>
      </div>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>External sources issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
      <ToastMessage toast={toast} />

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Registered sources</h3>
                <p className="muted">Sources are local registry records and do not include credentials or secrets.</p>
              </div>
              <StatusChip>{sources.length} sources</StatusChip>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Approval</th>
                    <th>Status</th>
                    <th>Intended gaps</th>
                    <th>Inspection</th>
                  </tr>
                </thead>
                <tbody>
                  {sources.map((source) => (
                    <tr key={source.source_key}>
                      <td>
                        <button
                          className="small-button"
                          type="button"
                          onClick={() => setSelectedKey(source.source_key || null)}
                        >
                          {source.source_name || source.source_key}
                        </button>
                        <p className="path-text">{source.source_key}</p>
                      </td>
                      <td>
                        <StatusChip tone={toneForStatus(source.approval_status)}>{source.approval_status}</StatusChip>
                      </td>
                      <td>
                        <StatusChip tone={toneForStatus(source.source_status)}>{source.source_status}</StatusChip>
                      </td>
                      <td>{(source.intended_gaps || []).join(", ") || "none"}</td>
                      <td>{metadataValue(source.inspected_metadata, "inspection_status")}</td>
                    </tr>
                  ))}
                  {!sources.length ? (
                    <tr>
                      <td colSpan={5}>No external source registry rows are loaded yet.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <aside className="dashboard-side">
          <section className="panel safety-card">
            <h3>Connector safety</h3>
            <ul className="check-list">
              <li>No ArcGIS login is required.</li>
              <li>No full feature datasets are downloaded.</li>
              <li>No real publish action is exposed.</li>
              <li>Candidate sources keep missing data visible until reviewed.</li>
            </ul>
          </section>
          <section className="panel">
            <h3>Selected source detail</h3>
            {selectedSource ? (
              <div className="page-stack">
                <div className="chip-row">
                  <StatusChip tone={toneForStatus(selectedSource.approval_status)}>
                    {selectedSource.approval_status}
                  </StatusChip>
                  <StatusChip tone={toneForStatus(selectedSource.source_status)}>{selectedSource.source_status}</StatusChip>
                </div>
                <dl className="layer-meta">
                  <div>
                    <dt>Source key</dt>
                    <dd>{selectedSource.source_key}</dd>
                  </div>
                  <div>
                    <dt>Type</dt>
                    <dd>{selectedSource.source_type}</dd>
                  </div>
                  <div>
                    <dt>Verified</dt>
                    <dd>{metadataValue(selectedSource.inspected_metadata, "is_verified")}</dd>
                  </div>
                  <div>
                    <dt>Record count</dt>
                    <dd>{metadataValue(selectedSource.inspected_metadata, "record_count")}</dd>
                  </div>
                </dl>
                <p className="muted">{selectedSource.limitations || "No limitation text recorded."}</p>
                {(selectedSource.categories || []).length ? (
                  <div className="chip-row">
                    {(selectedSource.categories || []).map((category) => (
                      <StatusChip key={category}>{category}</StatusChip>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : (
              <p className="muted">Select a source to review metadata and limitations.</p>
            )}
          </section>
        </aside>
      </section>
    </div>
  );
}
