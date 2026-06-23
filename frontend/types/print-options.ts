import type { ExportMode, PrintExportOptions, ReportSectionConfig } from "@/types/automap";

export type PrintExportMode = "map_sheet" | "map_exhibit_only" | "map_plus_summary" | "full_report";
export type SheetSizePresetId = "letter" | "tabloid" | "arch_d" | "arch_e" | "square_12" | "custom";
export type SheetOrientation = "portrait" | "landscape";
export type SheetMargin = "none" | "narrow" | "standard";
export type MapFrameFillMode = "fit_width" | "fit_page" | "fixed_scale";
export type MapScaleMode = "fit_extent" | "fixed_scale";

export type SheetSizePreset = {
  id: SheetSizePresetId;
  label: string;
  width: number;
  height: number;
};

export const SHEET_SIZE_PRESETS: SheetSizePreset[] = [
  { id: "letter", label: "Letter 8.5 x 11 in", width: 8.5, height: 11 },
  { id: "tabloid", label: "Tabloid 11 x 17 in", width: 11, height: 17 },
  { id: "arch_d", label: "ARCH D 24 x 36 in", width: 24, height: 36 },
  { id: "arch_e", label: "ARCH E 36 x 48 in", width: 36, height: 48 },
  { id: "square_12", label: "Square 12 x 12 in", width: 12, height: 12 },
  { id: "custom", label: "Custom", width: 11, height: 17 },
];

export type LivePrintOptions = {
  exportMode: PrintExportMode;
  includeMapSummary: boolean;
  includeKeyFindings: boolean;
  includeLayerTable: boolean;
  includeWarnings: boolean;
  includeSourceNotes: boolean;
  includeStatistics: boolean;
  includeParcelSummary: boolean;
  includeProximitySummary: boolean;
  includePermitSummary: boolean;
  includePlanningSummary: boolean;
  includeDevelopmentProxySummary: boolean;
  includeAppendix: boolean;
  includeDraftDisclaimer: boolean;
  sheetSizePreset: SheetSizePresetId;
  sheetWidth: number;
  sheetHeight: number;
  sheetUnits: "inches";
  sheetOrientation: SheetOrientation;
  sheetDpi: 150 | 300;
  sheetMargin: SheetMargin;
  mapFrameFill: MapFrameFillMode;
  scaleMode: MapScaleMode;
  fixedScale: "2400" | "4800" | "12000" | "24000" | "custom";
  customScale: number;
  includeTitle: boolean;
  includeSubtitle: boolean;
  includeLegend: boolean;
  includeScaleBar: boolean;
  includeNorthArrow: boolean;
  includeSourceNote: boolean;
  includeDraftWatermark: boolean;
  includeScopeNote: boolean;
  includeRealPublishNote: boolean;
};

export const DEFAULT_LIVE_PRINT_OPTIONS: LivePrintOptions = {
  exportMode: "map_sheet",
  includeMapSummary: false,
  includeKeyFindings: false,
  includeLayerTable: false,
  includeWarnings: false,
  includeSourceNotes: false,
  includeStatistics: false,
  includeParcelSummary: false,
  includeProximitySummary: false,
  includePermitSummary: false,
  includePlanningSummary: false,
  includeDevelopmentProxySummary: false,
  includeAppendix: false,
  includeDraftDisclaimer: true,
  sheetSizePreset: "letter",
  sheetWidth: 8.5,
  sheetHeight: 11,
  sheetUnits: "inches",
  sheetOrientation: "landscape",
  sheetDpi: 300,
  sheetMargin: "narrow",
  mapFrameFill: "fit_page",
  scaleMode: "fit_extent",
  fixedScale: "4800",
  customScale: 4800,
  includeTitle: true,
  includeSubtitle: true,
  includeLegend: true,
  includeScaleBar: true,
  includeNorthArrow: true,
  includeSourceNote: true,
  includeDraftWatermark: true,
  includeScopeNote: true,
  includeRealPublishNote: true,
};

function presetFor(id?: SheetSizePresetId | null): SheetSizePreset {
  return SHEET_SIZE_PRESETS.find((preset) => preset.id === id) || SHEET_SIZE_PRESETS[0];
}

export function effectiveSheetDimensions(options: LivePrintOptions): { width: number; height: number } {
  const preset = presetFor(options.sheetSizePreset);
  const width = options.sheetSizePreset === "custom" ? options.sheetWidth : preset.width;
  const height = options.sheetSizePreset === "custom" ? options.sheetHeight : preset.height;
  if (options.sheetOrientation === "landscape" && width < height) {
    return { width: height, height: width };
  }
  if (options.sheetOrientation === "portrait" && width > height) {
    return { width: height, height: width };
  }
  return { width, height };
}

export function normalizeExportMode(mode?: ExportMode | string | null): PrintExportMode {
  if (mode === "full_report") return "full_report";
  if (mode === "map_plus_summary" || mode === "map_summary") return "map_plus_summary";
  if (mode === "map_exhibit_only" || mode === "map_sheet") return "map_sheet";
  return "map_sheet";
}

function withMapSheetDefaults(base: LivePrintOptions): LivePrintOptions {
  return {
    ...base,
    exportMode: "map_sheet",
    includeMapSummary: false,
    includeKeyFindings: false,
    includeLayerTable: false,
    includeWarnings: false,
    includeSourceNotes: false,
    includeStatistics: false,
    includeParcelSummary: false,
    includeProximitySummary: false,
    includePermitSummary: false,
    includePlanningSummary: false,
    includeDevelopmentProxySummary: false,
    includeAppendix: false,
  };
}

export function printOptionsForMode(mode: ExportMode | PrintExportMode, current?: LivePrintOptions): LivePrintOptions {
  const exportMode = normalizeExportMode(mode);
  const sameMode = normalizeExportMode(current?.exportMode) === exportMode;
  const base = { ...DEFAULT_LIVE_PRINT_OPTIONS, ...(current || {}), exportMode };
  if (sameMode) {
    return base;
  }
  if (exportMode === "map_sheet") {
    return withMapSheetDefaults(base);
  }
  if (exportMode === "full_report") {
    return {
      ...base,
      includeMapSummary: true,
      includeKeyFindings: true,
      includeLayerTable: true,
      includeWarnings: true,
      includeSourceNotes: true,
      includeStatistics: true,
      includeAppendix: true,
    };
  }
  return {
    ...base,
    includeMapSummary: true,
    includeKeyFindings: true,
    includeWarnings: true,
    includeProximitySummary: true,
    includeAppendix: false,
  };
}

export function printOptionsToReportConfig(options: LivePrintOptions): ReportSectionConfig {
  return {
    include_map_summary: options.includeMapSummary,
    include_layer_table: options.includeLayerTable,
    include_warnings: options.includeWarnings,
    include_source_notes: options.includeSourceNotes,
    include_proximity_summary: options.includeProximitySummary,
    include_parcel_summary: options.includeParcelSummary,
    include_statistics: options.includeStatistics,
    include_permit_summary: options.includePermitSummary,
    include_planning_summary: options.includePlanningSummary,
    include_development_proxy_summary: options.includeDevelopmentProxySummary,
    include_table_preview: false,
    include_table_export_summary: false,
  };
}

export function reportConfigToPrintOptions(exportMode: ExportMode, config?: ReportSectionConfig): LivePrintOptions {
  const base = printOptionsForMode(exportMode);
  return {
    ...base,
    includeMapSummary: config?.include_map_summary ?? base.includeMapSummary,
    includeLayerTable: config?.include_layer_table ?? base.includeLayerTable,
    includeWarnings: config?.include_warnings ?? base.includeWarnings,
    includeSourceNotes: config?.include_source_notes ?? base.includeSourceNotes,
    includeStatistics: config?.include_statistics ?? base.includeStatistics,
    includeParcelSummary: config?.include_parcel_summary ?? base.includeParcelSummary,
    includeProximitySummary: config?.include_proximity_summary ?? base.includeProximitySummary,
    includePermitSummary: config?.include_permit_summary ?? base.includePermitSummary,
    includePlanningSummary: config?.include_planning_summary ?? base.includePlanningSummary,
    includeDevelopmentProxySummary: config?.include_development_proxy_summary ?? base.includeDevelopmentProxySummary,
  };
}

export function backendExportOptionsToPrintOptions(options?: PrintExportOptions | null, config?: ReportSectionConfig): LivePrintOptions {
  const base = reportConfigToPrintOptions(options?.export_mode || "map_sheet", config);
  return {
    ...base,
    includeMapSummary: options?.include_map_summary ?? base.includeMapSummary,
    includeKeyFindings: options?.include_key_findings ?? base.includeKeyFindings,
    includeLayerTable: options?.include_layer_table ?? base.includeLayerTable,
    includeWarnings: options?.include_warnings ?? base.includeWarnings,
    includeSourceNotes: options?.include_source_notes ?? base.includeSourceNotes,
    includeStatistics: options?.include_statistics ?? base.includeStatistics,
    includeParcelSummary: options?.include_parcel_summary ?? base.includeParcelSummary,
    includeProximitySummary: options?.include_proximity_summary ?? base.includeProximitySummary,
    includePermitSummary: options?.include_permit_summary ?? base.includePermitSummary,
    includePlanningSummary: options?.include_planning_summary ?? base.includePlanningSummary,
    includeDevelopmentProxySummary: options?.include_development_proxy_summary ?? base.includeDevelopmentProxySummary,
    includeAppendix: options?.include_appendix ?? base.includeAppendix,
    includeDraftDisclaimer: options?.include_draft_disclaimer ?? base.includeDraftDisclaimer,
    sheetSizePreset: (options?.sheet_size_preset as SheetSizePresetId | undefined) ?? base.sheetSizePreset,
    sheetWidth: options?.sheet_width ?? base.sheetWidth,
    sheetHeight: options?.sheet_height ?? base.sheetHeight,
    sheetUnits: "inches",
    sheetOrientation: (options?.sheet_orientation as SheetOrientation | undefined) ?? base.sheetOrientation,
    sheetDpi: (options?.sheet_dpi as 150 | 300 | undefined) ?? base.sheetDpi,
    sheetMargin: (options?.sheet_margin as SheetMargin | undefined) ?? base.sheetMargin,
    mapFrameFill: (options?.map_frame_fill as MapFrameFillMode | undefined) ?? base.mapFrameFill,
    scaleMode: (options?.scale_mode as MapScaleMode | undefined) ?? base.scaleMode,
    fixedScale: (options?.fixed_scale as LivePrintOptions["fixedScale"] | undefined) ?? base.fixedScale,
    customScale: options?.custom_scale ?? base.customScale,
    includeTitle: options?.include_title ?? base.includeTitle,
    includeSubtitle: options?.include_subtitle ?? base.includeSubtitle,
    includeLegend: options?.include_legend ?? base.includeLegend,
    includeScaleBar: options?.include_scale_bar ?? base.includeScaleBar,
    includeNorthArrow: options?.include_north_arrow ?? base.includeNorthArrow,
    includeSourceNote: options?.include_source_note ?? base.includeSourceNote,
    includeDraftWatermark: options?.include_draft_watermark ?? base.includeDraftWatermark,
    includeScopeNote: options?.include_scope_note ?? base.includeScopeNote,
    includeRealPublishNote: options?.include_real_publish_note ?? base.includeRealPublishNote,
  };
}

export function printOptionsToBackendExportOptions(options: LivePrintOptions): PrintExportOptions {
  return {
    export_mode: options.exportMode,
    include_map_summary: options.includeMapSummary,
    include_key_findings: options.includeKeyFindings,
    include_layer_table: options.includeLayerTable,
    include_warnings: options.includeWarnings,
    include_source_notes: options.includeSourceNotes,
    include_statistics: options.includeStatistics,
    include_parcel_summary: options.includeParcelSummary,
    include_proximity_summary: options.includeProximitySummary,
    include_permit_summary: options.includePermitSummary,
    include_planning_summary: options.includePlanningSummary,
    include_development_proxy_summary: options.includeDevelopmentProxySummary,
    include_appendix: options.includeAppendix,
    include_draft_disclaimer: options.includeDraftDisclaimer,
    sheet_size_preset: options.sheetSizePreset,
    sheet_width: options.sheetWidth,
    sheet_height: options.sheetHeight,
    sheet_units: options.sheetUnits,
    sheet_orientation: options.sheetOrientation,
    sheet_dpi: options.sheetDpi,
    sheet_margin: options.sheetMargin,
    map_frame_fill: options.mapFrameFill,
    scale_mode: options.scaleMode,
    fixed_scale: options.fixedScale,
    custom_scale: options.customScale,
    include_title: options.includeTitle,
    include_subtitle: options.includeSubtitle,
    include_legend: options.includeLegend,
    include_scale_bar: options.includeScaleBar,
    include_north_arrow: options.includeNorthArrow,
    include_source_note: options.includeSourceNote,
    include_draft_watermark: options.includeDraftWatermark,
    include_scope_note: options.includeScopeNote,
    include_real_publish_note: options.includeRealPublishNote,
    preserve_extent: true,
    preserve_layer_state: true,
    wysiwyg: true,
  };
}

export function includedPrintSections(options: LivePrintOptions): string[] {
  if (normalizeExportMode(options.exportMode) === "map_sheet") {
    return [
      "Map Sheet",
      options.includeTitle ? "Title" : null,
      options.includeSubtitle ? "Subtitle" : null,
      options.includeLegend ? "Legend" : null,
      options.includeScaleBar ? "Scale bar" : null,
      options.includeNorthArrow ? "North arrow" : null,
      options.includeSourceNote ? "Source note" : null,
      options.includeDraftWatermark ? "Draft watermark" : null,
    ].filter(Boolean) as string[];
  }
  return [
    options.includeMapSummary ? "Map Summary" : null,
    options.includeKeyFindings ? "Key Findings" : null,
    options.includeProximitySummary ? "Proximity Summary" : null,
    options.includeParcelSummary ? "Parcel Summary" : null,
    options.includeStatistics ? "Statistics" : null,
    options.includeLayerTable ? "Layer Source Table" : null,
    options.includeWarnings ? "Warnings and Limitations" : null,
    options.includeSourceNotes ? "Source Notes" : null,
    options.includePermitSummary ? "Permit Summary" : null,
    options.includePlanningSummary ? "Planning Summary" : null,
    options.includeDevelopmentProxySummary ? "Development Proxy Summary" : null,
    options.includeAppendix ? "Appendix" : null,
    options.includeDraftDisclaimer ? "Draft Disclaimer" : null,
  ].filter(Boolean) as string[];
}
