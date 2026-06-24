"use client";

import { PrintPreviewPanel } from "@/components/print-preview/print-preview-panel";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL } from "@/lib/api";
import type { ComposerMapState, ComposerResponse, ExhibitPackage } from "@/types/automap";
import type { LivePrintOptions, PrintExportMode } from "@/types/print-options";
import { effectiveSheetDimensions, includedPrintSections, printOptionsForMode, SHEET_SIZE_PRESETS } from "@/types/print-options";

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

type BooleanPrintOption =
  | "includeMapSummary"
  | "includeKeyFindings"
  | "includeLayerTable"
  | "includeWarnings"
  | "includeSourceNotes"
  | "includeStatistics"
  | "includeParcelSummary"
  | "includeProximitySummary"
  | "includePermitSummary"
  | "includePlanningSummary"
  | "includeDevelopmentProxySummary"
  | "includeAppendix"
  | "includeDraftDisclaimer"
  | "includeTitle"
  | "includeSubtitle"
  | "includeLegend"
  | "includeScaleBar"
  | "includeNorthArrow"
  | "includeSourceNote"
  | "includeDraftWatermark"
  | "includeScopeNote"
  | "includeRealPublishNote";

function toggleOption(options: LivePrintOptions, key: BooleanPrintOption): LivePrintOptions {
  return printOptionsForMode(options.exportMode, { ...options, [key]: !options[key] });
}

function updateOption<K extends keyof LivePrintOptions>(options: LivePrintOptions, key: K, value: LivePrintOptions[K]): LivePrintOptions {
  return printOptionsForMode(options.exportMode, { ...options, [key]: value });
}

function updateSheetPreset(options: LivePrintOptions, value: LivePrintOptions["sheetSizePreset"]): LivePrintOptions {
  const preset = SHEET_SIZE_PRESETS.find((item) => item.id === value);
  return printOptionsForMode(options.exportMode, {
    ...options,
    sheetSizePreset: value,
    sheetWidth: value === "custom" ? options.sheetWidth : preset?.width || options.sheetWidth,
    sheetHeight: value === "custom" ? options.sheetHeight : preset?.height || options.sheetHeight,
  });
}

const sectionOptions: Array<[BooleanPrintOption, string]> = [
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

const furnitureOptions: Array<[BooleanPrintOption, string]> = [
  ["includeTitle", "Title"],
  ["includeSubtitle", "Subtitle"],
  ["includeLegend", "Legend"],
  ["includeScaleBar", "Scale bar"],
  ["includeNorthArrow", "North arrow"],
  ["includeSourceNote", "Source note"],
  ["includeDraftWatermark", "Draft watermark"],
  ["includeScopeNote", "Cabarrus County scope note"],
  ["includeRealPublishNote", "Real publish disabled note"],
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
  const isMapSheet = printOptions.exportMode === "map_sheet";
  const canOpenPrint = Boolean(lockedMapState);
  const sheetDimensions = effectiveSheetDimensions(printOptions);
  const customSizeWarning =
    printOptions.sheetSizePreset === "custom" &&
    (printOptions.sheetWidth < 4 ||
      printOptions.sheetWidth > 60 ||
      printOptions.sheetHeight < 4 ||
      printOptions.sheetHeight > 60 ||
      Math.max(printOptions.sheetWidth, printOptions.sheetHeight) / Math.max(1, Math.min(printOptions.sheetWidth, printOptions.sheetHeight)) > 5);

  return (
    <section className="composer-export-layout print-export-step-layout">
      <aside className="panel composer-export-panel print-export-controls">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Print / Export</p>
            <h3>Choose output</h3>
            <p className="muted">Preview updates as you choose options. Printed output uses the locked final map.</p>
          </div>
          <StatusChip tone="success">Locked final map</StatusChip>
        </div>

        <section className="definition-box export-mode-selector">
          <strong>Export mode</strong>
          <MapStateCapture response={response} exportMode={printOptions.exportMode} />
          <div className="segmented-control export-mode-control" role="radiogroup" aria-label="Print export mode">
            {[
              ["map_sheet", "Map Sheet", "Map only / standalone sheet with custom size."],
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
          <p className="muted export-mode-note">Changing export mode adds pages after the locked map sheet. It does not change the map.</p>
        </section>

        <section className="definition-box sheet-size-panel">
          <strong>Map Sheet Size</strong>
          <p className="muted">Use Map Sheet for zoning maps, floodplain maps, voting precinct maps, route maps, and parcel context maps.</p>
          <div className="sheet-control-grid">
            <label>
              <span>Preset size</span>
              <select
                value={printOptions.sheetSizePreset}
                onChange={(event) => setPrintOptions(updateSheetPreset(printOptions, event.target.value as LivePrintOptions["sheetSizePreset"]))}
              >
                {SHEET_SIZE_PRESETS.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Orientation</span>
              <select
                value={printOptions.sheetOrientation}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "sheetOrientation", event.target.value as LivePrintOptions["sheetOrientation"]))}
              >
                <option value="landscape">Landscape</option>
                <option value="portrait">Portrait</option>
              </select>
            </label>
            <label>
              <span>Width</span>
              <input
                disabled={printOptions.sheetSizePreset !== "custom"}
                max={60}
                min={4}
                step={0.25}
                type="number"
                value={printOptions.sheetWidth}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "sheetWidth", Number(event.target.value)))}
              />
            </label>
            <label>
              <span>Height</span>
              <input
                disabled={printOptions.sheetSizePreset !== "custom"}
                max={60}
                min={4}
                step={0.25}
                type="number"
                value={printOptions.sheetHeight}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "sheetHeight", Number(event.target.value)))}
              />
            </label>
            <label>
              <span>Units</span>
              <select value={printOptions.sheetUnits} onChange={() => undefined}>
                <option value="inches">Inches</option>
              </select>
            </label>
            <label>
              <span>DPI</span>
              <select
                value={printOptions.sheetDpi}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "sheetDpi", Number(event.target.value) as LivePrintOptions["sheetDpi"]))}
              >
                <option value={150}>150</option>
                <option value={300}>300</option>
              </select>
            </label>
            <label>
              <span>Margin</span>
              <select
                value={printOptions.sheetMargin}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "sheetMargin", event.target.value as LivePrintOptions["sheetMargin"]))}
              >
                <option value="none">None</option>
                <option value="narrow">Narrow</option>
                <option value="standard">Standard</option>
              </select>
            </label>
            <label>
              <span>Map frame fill</span>
              <select
                value={printOptions.mapFrameFill}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "mapFrameFill", event.target.value as LivePrintOptions["mapFrameFill"]))}
              >
                <option value="fit_width">Fit width</option>
                <option value="fit_page">Fit page</option>
                <option value="fixed_scale">Fixed scale</option>
              </select>
            </label>
          </div>
          <p className="muted">
            Sheet preview: {sheetDimensions.width} x {sheetDimensions.height} in at {printOptions.sheetDpi} DPI.
          </p>
          {customSizeWarning ? <p className="sheet-warning">Custom sheet sizes should stay within 4-60 inches and use a practical aspect ratio.</p> : null}
        </section>

        <section className="definition-box sheet-size-panel">
          <strong>Map Scale</strong>
          <div className="sheet-control-grid sheet-control-grid-two">
            <label>
              <span>Scale mode</span>
              <select
                value={printOptions.scaleMode}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "scaleMode", event.target.value as LivePrintOptions["scaleMode"]))}
              >
                <option value="fit_extent">Fit locked extent to sheet</option>
                <option value="fixed_scale">Fixed map scale</option>
              </select>
            </label>
            <label>
              <span>Fixed scale</span>
              <select
                disabled={printOptions.scaleMode !== "fixed_scale"}
                value={printOptions.fixedScale}
                onChange={(event) => setPrintOptions(updateOption(printOptions, "fixedScale", event.target.value as LivePrintOptions["fixedScale"]))}
              >
                <option value="2400">1:2,400</option>
                <option value="4800">1:4,800</option>
                <option value="12000">1:12,000</option>
                <option value="24000">1:24,000</option>
                <option value="custom">Custom</option>
              </select>
            </label>
            {printOptions.scaleMode === "fixed_scale" && printOptions.fixedScale === "custom" ? (
              <label>
                <span>Custom scale</span>
                <input
                  min={100}
                  step={100}
                  type="number"
                  value={printOptions.customScale}
                  onChange={(event) => setPrintOptions(updateOption(printOptions, "customScale", Number(event.target.value)))}
                />
              </label>
            ) : null}
          </div>
          {printOptions.scaleMode === "fixed_scale" ? (
            <p className="sheet-warning">This scale may crop the locked extent. Use Adjust step to change map extent or choose Fit locked extent.</p>
          ) : null}
        </section>

        <section className="definition-box report-section-options">
          <strong>Map furniture</strong>
          <div className="composer-report-option-grid compact-report-options">
            {furnitureOptions.map(([key, label]) => (
              <label className="toggle-line" key={key}>
                <input checked={Boolean(printOptions[key])} type="checkbox" onChange={() => setPrintOptions(toggleOption(printOptions, key))} />
                {label}
              </label>
            ))}
          </div>
        </section>

        {isMapSheet ? (
          <section className="definition-box report-section-options">
            <strong>Report sections</strong>
            <p className="muted">Map Sheet mode keeps long report sections off. Choose Map + summary or Full report for narrative sections, tables, and appendix pages.</p>
            <p className="muted">Included now: {includedSections.join(", ") || "Map sheet only"}</p>
          </section>
        ) : (
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
        )}

        <section className="definition-box">
          <strong>Locked map state</strong>
          <p>If you need to change the extent, zoom, or layer visibility, use Unlock and Edit Map. Print/export does not pan or zoom the locked map.</p>
        </section>

        <div className="button-row composer-export-buttons">
          <button className="button" type="button" onClick={onOpenPrintLayout} disabled={loadingReport || !canOpenPrint}>
            Open Browser Print
          </button>
          <button className="button button-secondary" type="button" onClick={onOpenPrintLayout} disabled={loadingReport || !isMapSheet || !canOpenPrint}>
            Export Map Sheet PDF
          </button>
          <button className="button button-secondary" type="button" disabled title="PNG export draft">
            Export Map Sheet PNG
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
          <p>
            {canOpenPrint ? "Print/export files are local draft artifacts." : "Lock final map before printing."} No ArcGIS item is created and no ArcGIS login is required.
          </p>
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
