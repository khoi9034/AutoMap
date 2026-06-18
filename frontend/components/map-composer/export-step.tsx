"use client";

import { SharedMapRenderer } from "@/components/map-renderer/shared-map-renderer";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL } from "@/lib/api";
import type { ComposerResponse, ExhibitPackage, ReportSectionConfig } from "@/types/automap";

import { composerDisplayTitle, localFileUrl } from "./utils";

type ExportStepProps = {
  exhibitPackage?: ExhibitPackage | null;
  loadingExhibit?: boolean;
  loadingReport?: boolean;
  onGenerateExhibit: () => void;
  onGenerateReport: () => void;
  onGoToAdjust: () => void;
  onOpenPrintLayout: () => void;
  previewPacketId: string;
  reportConfig: ReportSectionConfig;
  response: ComposerResponse | null;
  setReportConfig: (config: ReportSectionConfig) => void;
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
  onOpenPrintLayout,
  previewPacketId,
  reportConfig,
  response,
  setReportConfig,
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
  const toggleReportOption = (key: keyof ReportSectionConfig) => {
    setReportConfig({ ...reportConfig, [key]: !reportConfig[key] });
  };

  return (
    <section className="composer-export-layout">
      <div className="composer-export-preview">
        <SharedMapRenderer mode="exhibit" mapState={response.composer_map_state} response={response} packetId={previewPacketId} showLayerPanel={false} />
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
          <button className="button" type="button" onClick={onOpenPrintLayout} disabled={loadingReport}>
            Open Print Layout
          </button>
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
        <section className="definition-box report-section-options">
          <strong>Report sections</strong>
          <div className="composer-report-option-grid">
            {[
              ["include_map_summary", "Include map summary"],
              ["include_layer_table", "Include selected layer table"],
              ["include_warnings", "Include warnings and limitations"],
              ["include_source_notes", "Include source notes"],
              ["include_proximity_summary", "Include proximity/distance summary"],
              ["include_parcel_summary", "Include parcel summary if available"],
              ["include_statistics", "Include statistics section"],
              ["include_table_preview", "Include table preview if available"],
              ["include_table_export_summary", "Include table export summary"],
              ["include_permit_summary", "Include permit stats when available"],
              ["include_planning_summary", "Include planning stats when available"],
              ["include_development_proxy_summary", "Include development proxy stats when available"],
            ].map(([key, label]) => (
              <label className="toggle-line" key={key}>
                <input
                  checked={Boolean(reportConfig[key as keyof ReportSectionConfig])}
                  type="checkbox"
                  onChange={() => toggleReportOption(key as keyof ReportSectionConfig)}
                />
                {label}
              </label>
            ))}
          </div>
        </section>
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
