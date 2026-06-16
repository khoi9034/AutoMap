"use client";

import Link from "next/link";
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

function identifierLabel(value: unknown): string {
  if (!value || typeof value !== "object") {
    return String(value || "");
  }
  const item = value as { value?: string; normalized_value?: string; identifier_type?: string };
  return item.value || item.normalized_value || item.identifier_type || JSON.stringify(item);
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
  const parcelContext = preview?.parcel_context;
  const parcelPreviewBlocked = Boolean(preview?.parcel_preview_blocked || parcelContext?.can_focus_map === false);

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
          {parcelPreviewBlocked ? (
            <div className="parcel-preview-blocked" role="alert">
              <p className="eyebrow">Parcel-focused preview blocked</p>
              <h3>Parcel not matched - preview cannot focus on parcel.</h3>
              <p>
                {parcelContext?.reason_if_not_focusable ||
                  "AutoMap cannot zoom to or analyze this parcel until a valid parcel/PIN/address is provided."}
              </p>
              <div className="detail-grid">
                <div>
                  <span className="muted">Match status</span>
                  <strong>{parcelContext?.match_status || "needs_review"}</strong>
                </div>
                <div>
                  <span className="muted">Matched count</span>
                  <strong>{parcelContext?.matched_count ?? 0}</strong>
                </div>
                <div>
                  <span className="muted">Preview status</span>
                  <strong>{preview?.preview_status || parcelContext?.preview_status || "blocked_until_parcel_matched"}</strong>
                </div>
              </div>
              {parcelContext?.unmatched_identifiers?.length ? (
                <div className="definition-box">
                  <strong>Unmatched identifiers</strong>
                  <p>{parcelContext.unmatched_identifiers.map(identifierLabel).join(", ")}</p>
                </div>
              ) : null}
              <div className="button-row">
                <Link className="button" href="/map-composer">
                  Try another parcel/PIN/address
                </Link>
                <Link className="button button-secondary" href="/parcel-workspace">
                  Open Parcel Workspace
                </Link>
              </div>
            </div>
          ) : (
            <iframe className="preview-frame" title="AutoMap draft preview" src={previewUrl} />
          )}
        </div>

        <aside className="preview-side-panel">
          <div className="preview-summary">
            <p className="eyebrow">Preview packet</p>
            <h3>{preview?.map_title || "Selected draft map"}</h3>
            <p className="muted">{preview?.original_prompt || "Waiting for preview metadata from the backend."}</p>
            <div className="chip-row">
              <StatusChip tone="success">{layerCountLabel(preview)}</StatusChip>
              {derivedLayer ? <StatusChip tone="warning">Derived Local Analysis Result</StatusChip> : null}
              {parcelContext?.can_focus_map ? <StatusChip tone="success">Parcel focus</StatusChip> : null}
              {parcelPreviewBlocked ? <StatusChip tone="danger">Parcel not matched</StatusChip> : null}
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
