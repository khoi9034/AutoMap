"use client";

import { useEffect, useMemo, useState } from "react";

import { LayerPanel } from "@/components/layer-panel";
import { StatusChip } from "@/components/status-chip";
import { WarningPanel } from "@/components/warning-panel";
import { API_BASE_URL, getPreviewConfig } from "@/lib/api";
import { loadWorkflowState } from "@/lib/workflow-store";
import type { PreviewConfig, PreviewLayer } from "@/types/automap";

type ArcGISMapPreviewProps = {
  packetId: string;
};

function layerCountLabel(preview: PreviewConfig | null): string {
  const count = preview?.operational_layers?.length || 0;
  return `${count} operational layer${count === 1 ? "" : "s"}`;
}

export function ArcGISMapPreview({ packetId }: ArcGISMapPreviewProps) {
  const [preview, setPreview] = useState<PreviewConfig | null>(null);
  const [derivedLayer, setDerivedLayer] = useState<PreviewLayer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!packetId) {
      setPreview(null);
      return;
    }
    setLoading(true);
    setError(null);
    getPreviewConfig(packetId)
      .then(setPreview)
      .catch((exc) => {
        setPreview(null);
        setError(exc instanceof Error ? exc.message : "Preview config failed.");
      })
      .finally(() => setLoading(false));
    const workflow = loadWorkflowState();
    const analysisRun = workflow.analysisRun || {};
    const candidate = analysisRun.derived_layer;
    setDerivedLayer(candidate && typeof candidate === "object" ? (candidate as PreviewLayer) : null);
  }, [packetId]);

  const previewUrl = useMemo(
    () => `${API_BASE_URL}/preview/${encodeURIComponent(packetId || "latest")}`,
    [packetId],
  );
  const panelLayers = useMemo(
    () => [
      ...(preview?.operational_layers || []),
      ...(derivedLayer ? [{ ...derivedLayer, derived_local_analysis: true }] : []),
    ],
    [preview, derivedLayer],
  );

  if (!packetId) {
    return (
      <section className="panel empty-state">
        <h3>No packet selected</h3>
        <p>Select or create a review, adjusted, or approved packet before opening the local map preview.</p>
      </section>
    );
  }

  return (
    <div className="page-stack">
      <section className="map-preview-shell">
        <div className="preview-stage">
          <div className="draft-banner">
            <div>
              <strong>Draft-only local preview</strong>
              <p>No ArcGIS login, item creation, public sharing, or organization sharing occurs here.</p>
            </div>
            <div className="chip-row">
              <StatusChip tone="success">Backend iframe</StatusChip>
              <StatusChip tone="success">No publish</StatusChip>
            </div>
          </div>
          {loading ? (
            <div className="preview-loading" role="status">
              Loading preview config and local map frame...
            </div>
          ) : null}
          {error ? (
            <div className="preview-error" role="alert">
              <strong>Preview config unavailable</strong>
              <p>{error}</p>
              <p className="muted">The backend preview route remains linked below if the packet exists locally.</p>
            </div>
          ) : null}
          <iframe className="preview-frame" title="AutoMap draft preview" src={previewUrl} />
        </div>

        <aside className="preview-side-panel">
          <div className="preview-summary">
            <p className="eyebrow">Preview packet</p>
            <h3>{preview?.map_title || "Selected draft map"}</h3>
            <p className="muted">{preview?.original_prompt || "Waiting for preview metadata from the backend."}</p>
            <div className="chip-row">
              <StatusChip tone="success">{layerCountLabel(preview)}</StatusChip>
              {derivedLayer ? <StatusChip tone="warning">Derived Local Analysis Result</StatusChip> : null}
              <StatusChip tone={preview?.preview_only === false ? "warning" : "success"}>
                {preview?.preview_only === false ? "Review mode" : "Preview only"}
              </StatusChip>
            </div>
          </div>
          <dl className="status-list">
            <div>
              <dt>Draft status</dt>
              <dd>{preview?.draft_status || "preview"}</dd>
            </div>
            <div>
              <dt>Packet id</dt>
              <dd>{preview?.packet_id || packetId}</dd>
            </div>
            <div>
              <dt>WebMap path</dt>
              <dd className="path-text">{preview?.webmap_path || "Not loaded"}</dd>
            </div>
          </dl>
        </aside>
      </section>

      <WarningPanel warnings={preview?.warnings} missingData={preview?.missing_data || []} />
      <LayerPanel layers={panelLayers} />
    </div>
  );
}
