"use client";

import { PrintPreviewPanel } from "@/components/print-preview/print-preview-panel";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL } from "@/lib/api";
import type { ComposerMapState, ComposerResponse, ExhibitPackage } from "@/types/automap";
import type { LivePrintOptions, PrintExportMode } from "@/types/print-options";
import { includedPrintSections, printOptionsForMode } from "@/types/print-options";

import { MapStateCapture } from "./map-state-capture";
import { localFileUrl } from "./utils";

type PrintExportStepProps = {
  exhibitPackage?: ExhibitPackage | null;
  loadingExhibit?: boolean;
  loadingReport?: boolean;
  lockedMapState?: ComposerMapState | null;
  onGenerateExhibit: () => void;
  onGenerateReport: () => void;
  onGoToAdjust: () => void;
  onOpenPrintLayout: () => void;
  previewPacketId: string;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
  setPrintOptions: (options: LivePrintOptions) => void;
};

function packageFiles(response: ComposerResponse | null, exhibitPackage?: ExhibitPackage | null) {
  return [...(response?.export?.files || []), ...((response?.exhibit || exhibitPackage)?.files || [])];
}

function packageFileUrl(path?: string | null, url?: string | null): string {
  if (url) return `${API_BASE_URL}${url}`;
  return localFileUrl(path);
}

function toggleOption(options: LivePrintOptions, key: keyof LivePrintOptions): LivePrintOptions {
  if (key === "exportMode") return options;
  return printOptionsForMode(options.exportMode, { ...options, [key]: !options[key] });
}

const sectionOptions: Array<[keyof LivePrintOptions, string]> = [
  ["includeMapSummary", "Map summary"],
  ["includeKeyFindings", "Key findings"],
  ["includeProximitySummary", "Proximity / distance summary"],
  ["includeParcelSummary", "Parcel summary"],
  ["includeStatistics", "Statistics"],
  ["includeLayerTable", "Layer source table"],
  ["includeWarnings", "Warnings and limitations"],
  ["includeSourceNotes", "Source notes"],
  ["includePermitSummary", "Permit section"],
  ["includePlanningSummary", "Planning section"],
  ["includeDevelopmentProxySummary", "Development proxy section"],
  ["includeAppendix", "Appendix"],
  ["includeDraftDisclaimer", "Draft disclaimer"],
];

export function PrintExportStep({
  exhibitPackage,
  loadingExhibit,
  loadingReport,
  lockedMapState,
  onGenerateExhibit,
  onGenerateReport,
  onGoToAdjust,
  onOpenPrintLayout,
  previewPacketId,
  printOptions,
  response,
  setPrintOptions,
}: PrintExportStepProps) {
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
  const includedSections = includedPrintSections(printOptions);

  return (
    <section className="composer-export-layout print-export-step-layout">
      <aside className="panel composer-export-panel print-export-controls">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Print / Export</p>
            <h3>Choose final sections</h3>
            <p className="muted">Preview updates as you choose sections. Printed output uses the locked final map.</p>
          </div>
          <StatusChip tone="success">Locked final map</StatusChip>
        </div>

        <section className="definition-box export-mode-selector">
          <strong>Export mode</strong>
          <MapStateCapture response={response} exportMode={printOptions.exportMode} />
          <div className="segmented-control export-mode-control" role="radiogroup" aria-label="Print export mode">
            {[
              ["map_exhibit_only", "Map only", "One-page map exhibit first."],
              ["map_plus_summary", "Map + summary", "Adds concise findings below the map."],
              ["full_report", "Full report", "Includes appendices, tables, warnings, and statistics."],
            ].map(([mode, label, description]) => (
              <label className={printOptions.exportMode === mode ? "active" : ""} key={mode}>
                <input
                  checked={printOptions.exportMode === mode}
                  name="export-mode"
                  type="radio"
                  value={mode}
                  onChange={() => setPrintOptions(printOptionsForMode(mode as PrintExportMode, printOptions))}
                />
                <span>{label}</span>
                <small>{description}</small>
              </label>
            ))}
          </div>
        </section>

        <section className="definition-box report-section-options">
          <strong>Report sections</strong>
          <div className="composer-report-option-grid compact-report-options">
            {sectionOptions.map(([key, label]) => (
              <label className="toggle-line" key={key}>
                <input checked={Boolean(printOptions[key])} type="checkbox" onChange={() => setPrintOptions(toggleOption(printOptions, key))} />
                {label}
              </label>
            ))}
          </div>
          <p className="muted">Included now: {includedSections.join(", ") || "Map page only"}</p>
        </section>

        <div className="button-row composer-export-buttons">
          <button className="button" type="button" onClick={onOpenPrintLayout} disabled={loadingReport}>
            Open Browser Print
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
            Unlock and Edit Map
          </button>
        </div>

        <div className="definition-box">
          <strong>Export status</strong>
          <p>Print/export files are local draft artifacts. No ArcGIS item is created and no ArcGIS login is required.</p>
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
        ) : null}
      </aside>

      <PrintPreviewPanel mapState={lockedMapState} packetId={previewPacketId} printOptions={printOptions} response={response} />
    </section>
  );
}
