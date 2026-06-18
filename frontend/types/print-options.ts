import type { ExportMode, PrintExportOptions, ReportSectionConfig } from "@/types/automap";

export type PrintExportMode = "map_exhibit_only" | "map_plus_summary" | "full_report";

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
};

export const DEFAULT_LIVE_PRINT_OPTIONS: LivePrintOptions = {
  exportMode: "map_exhibit_only",
  includeMapSummary: true,
  includeKeyFindings: true,
  includeLayerTable: false,
  includeWarnings: true,
  includeSourceNotes: false,
  includeStatistics: false,
  includeParcelSummary: false,
  includeProximitySummary: true,
  includePermitSummary: false,
  includePlanningSummary: false,
  includeDevelopmentProxySummary: false,
  includeAppendix: false,
  includeDraftDisclaimer: true,
};

function normalizeExportMode(mode?: ExportMode | string | null): PrintExportMode {
  if (mode === "full_report") return "full_report";
  if (mode === "map_plus_summary" || mode === "map_summary") return "map_plus_summary";
  return "map_exhibit_only";
}

export function printOptionsForMode(mode: ExportMode | PrintExportMode, current?: LivePrintOptions): LivePrintOptions {
  const exportMode = normalizeExportMode(mode);
  const sameMode = normalizeExportMode(current?.exportMode) === exportMode;
  const base = { ...DEFAULT_LIVE_PRINT_OPTIONS, ...(current || {}), exportMode };
  if (sameMode) {
    return base;
  }
  if (exportMode === "map_exhibit_only") {
    return {
      ...base,
      includeLayerTable: false,
      includeStatistics: false,
      includePermitSummary: false,
      includePlanningSummary: false,
      includeDevelopmentProxySummary: false,
      includeAppendix: false,
    };
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
  const base = reportConfigToPrintOptions(options?.export_mode || "map_exhibit_only", config);
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
    preserve_extent: true,
    preserve_layer_state: true,
    wysiwyg: true,
  };
}

export function includedPrintSections(options: LivePrintOptions): string[] {
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
