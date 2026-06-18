"use client";

import Link from "next/link";

import { ComposerMapPreview } from "@/components/composer-map-preview";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL } from "@/lib/api";
import type { ComposerResponse, ExhibitPackage } from "@/types/automap";

import { composerDisplayTitle, localFileUrl } from "./utils";

type ExportStepProps = {
  exhibitPackage?: ExhibitPackage | null;
  loadingExhibit?: boolean;
  loadingReport?: boolean;
  onGenerateExhibit: () => void;
  onGenerateReport: () => void;
  onGoToAdjust: () => void;
  previewPacketId: string;
  response: ComposerResponse | null;
};

function packageFiles(response: ComposerResponse | null, exhibitPackage?: ExhibitPackage | null) {
  return [...(response?.export?.files || []), ...((response?.exhibit || exhibitPackage)?.files || [])];
}

function packageFileUrl(path?: string | null, url?: string | null): string {
  if (url) return `${API_BASE_URL}${url}`;
  return localFileUrl(path);
}

export function ExportStep({
  exhibitPackage,
  loadingExhibit,
  loadingReport,
  onGenerateExhibit,
  onGenerateReport,
  onGoToAdjust,
  previewPacketId,
  response,
}: ExportStepProps) {
  if (!response?.can_preview || !previewPacketId) {
    return (
      <section className="panel empty-state">
        <h3>Preview required</h3>
        <p>Export stays disabled until AutoMap can show a focused draft preview.</p>
      </section>
    );
  }
  const files = packageFiles(response, exhibitPackage);
  const layerSourceFile = files.find((file) => file.name === "layer_sources.csv");
  const warningFile = files.find((file) => file.name === "warnings.json");

  return (
    <section className="composer-export-layout">
      <div className="composer-export-preview">
        <ComposerMapPreview response={response} packetId={previewPacketId} showLayerPanel={false} />
      </div>
      <aside className="panel composer-export-panel">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Print / Export</p>
            <h3>{composerDisplayTitle(response)}</h3>
            <p className="muted">Local staff-report-style outputs. Nothing is published.</p>
          </div>
          <StatusChip tone="success">Draft only</StatusChip>
        </div>
        <div className="button-row composer-export-buttons">
          {response.composer_session_id ? (
            <Link className="button" href={`/map-composer/${response.composer_session_id}/print`}>
              Open Print Layout
            </Link>
          ) : null}
          <button className="button button-secondary" type="button" onClick={onGenerateExhibit} disabled={loadingExhibit}>
            {loadingExhibit ? "Generating..." : "Generate Exhibit Package"}
          </button>
          <button className="button button-secondary" type="button" onClick={onGenerateReport} disabled={loadingReport}>
            {loadingReport ? "Generating..." : "Generate Review Report"}
          </button>
          <a className="button button-secondary" href={localFileUrl(response.webmap_path)} target="_blank" rel="noreferrer">
            Export WebMap JSON
          </a>
          {layerSourceFile ? (
            <a className="button button-secondary" href={packageFileUrl(layerSourceFile.path, layerSourceFile.url)} target="_blank" rel="noreferrer">
              Export Layer Source CSV
            </a>
          ) : null}
          {warningFile ? (
            <a className="button button-secondary" href={packageFileUrl(warningFile.path, warningFile.url)} target="_blank" rel="noreferrer">
              Export Warning Summary
            </a>
          ) : null}
          <button className="button button-secondary" type="button" onClick={onGoToAdjust}>
            Back to Adjust
          </button>
        </div>
        <div className="definition-box">
          <strong>Draft-only disclaimer</strong>
          <p>Print and export files are local review artifacts. They are not official county maps and no ArcGIS item is created.</p>
        </div>
        {files.length ? (
          <div className="export-link-grid">
            {files.map((file) => (
              <a className="export-link" key={`${file.name}-${file.path}`} href={packageFileUrl(file.path, file.url)} target="_blank" rel="noreferrer">
                <strong>{file.name}</strong>
                <span>{file.path}</span>
              </a>
            ))}
          </div>
        ) : (
          <p className="muted">Generate a report or exhibit package to show output links here.</p>
        )}
      </aside>
    </section>
  );
}
