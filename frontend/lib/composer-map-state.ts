import type {
  ComposerAdjustPayload,
  ComposerMapState,
  ComposerResponse,
  ExportMode,
  PrintExportOptions,
  ReportSectionConfig,
} from "@/types/automap";
import type { ComposerLayerEdit } from "@/components/map-composer/types";
import {
  DEFAULT_LIVE_PRINT_OPTIONS,
  printOptionsForMode,
  printOptionsToBackendExportOptions,
  printOptionsToReportConfig,
  type LivePrintOptions,
} from "@/types/print-options";

type BuildComposerMapStateSnapshotArgs = {
  response: ComposerResponse;
  layers: ComposerLayerEdit[];
  mapTitle: string;
  mapSubtitle: string;
  notes: string;
  reportConfig: ReportSectionConfig;
  exportMode: ExportMode;
  printOptions?: LivePrintOptions;
  activeMapViewState?: Partial<ComposerMapState> | null;
};

export const defaultPrintExportOptions: PrintExportOptions = printOptionsToBackendExportOptions(DEFAULT_LIVE_PRINT_OPTIONS);

export function reportConfigForExportMode(exportMode: ExportMode, current?: ReportSectionConfig): ReportSectionConfig {
  const defaults = printOptionsToReportConfig(printOptionsForMode(exportMode));
  const merged = { ...defaults, ...(current || {}) };
  if (exportMode === "map_exhibit_only") {
    return {
      ...merged,
      include_layer_table: false,
      include_statistics: false,
      include_permit_summary: false,
      include_planning_summary: false,
      include_development_proxy_summary: false,
      include_table_preview: false,
      include_table_export_summary: false,
    };
  }
  return merged;
}

export function printExportOptionsForMode(exportMode: ExportMode, printOptions?: LivePrintOptions): PrintExportOptions {
  return printOptionsToBackendExportOptions(printOptionsForMode(exportMode, printOptions));
}

export function buildComposerMapStateSnapshot({
  response,
  layers,
  mapTitle,
  mapSubtitle,
  notes,
  reportConfig,
  exportMode,
  printOptions,
  activeMapViewState,
}: BuildComposerMapStateSnapshotArgs): ComposerMapState {
  const priorState = response.composer_map_state || {};
  const previewConfig = response.preview_config || priorState.preview_config || {};
  const normalizedPrintOptions = printOptionsForMode(exportMode, printOptions);
  const exportOptions = printOptionsToBackendExportOptions(normalizedPrintOptions);
  const normalizedReportConfig = {
    ...printOptionsToReportConfig(normalizedPrintOptions),
    include_table_preview: reportConfig.include_table_preview || false,
    include_table_export_summary: reportConfig.include_table_export_summary || false,
  };
  const visibleLayers = layers.filter((layer) => layer.visibility && !layer.remove_layer);
  const hiddenLayers = layers.filter((layer) => !layer.visibility || layer.remove_layer);
  const layerOpacity = Object.fromEntries(layers.map((layer) => [layer.layer_key, layer.opacity]));
  const layerTitles = Object.fromEntries(layers.map((layer) => [layer.layer_key, layer.title]));
  const layerRoles = Object.fromEntries(layers.map((layer) => [layer.layer_key, layer.role || "context"]));
  const layerSymbology = Object.fromEntries(
    layers.map((layer) => [
      layer.layer_key,
      {
        line_style: layer.line_style || null,
        line_thickness: layer.line_thickness ?? null,
        symbol_key: layer.symbol_key || null,
      },
    ]),
  );

  return {
    ...priorState,
    composer_session_id: response.composer_session_id,
    map_title: mapTitle || priorState.map_title || response.map_title,
    map_subtitle: mapSubtitle || priorState.map_subtitle || response.map_layout?.subtitle || response.preview_config?.map_layout?.subtitle,
    raw_prompt: response.raw_prompt || response.prompt || priorState.raw_prompt,
    request_type: response.request_type || priorState.request_type,
    preview_config: previewConfig,
    map_extent: activeMapViewState?.map_extent || priorState.map_extent || previewConfig.focus_extent || previewConfig.initial_extent || null,
    current_center: activeMapViewState?.current_center || priorState.current_center || null,
    current_scale: activeMapViewState?.current_scale ?? priorState.current_scale ?? null,
    current_zoom: activeMapViewState?.current_zoom ?? priorState.current_zoom ?? null,
    current_rotation: activeMapViewState?.current_rotation ?? priorState.current_rotation ?? 0,
    basemap: previewConfig.basemap || priorState.basemap || "streets-vector",
    visible_layers: visibleLayers,
    hidden_layers: hiddenLayers,
    layer_order: layers.map((layer) => layer.layer_key),
    layer_opacity: layerOpacity,
    layer_titles: layerTitles,
    layer_roles: layerRoles,
    layer_symbology: layerSymbology,
    derived_overlays: previewConfig.derived_overlays || priorState.derived_overlays || [],
    legend_items: response.map_layout?.legend_items || previewConfig.map_layout?.legend_items || priorState.legend_items || [],
    scale_bar_config: priorState.scale_bar_config || { enabled: true, position: "bottom-center", width_percent: 64 },
    north_arrow_config: priorState.north_arrow_config || { enabled: true, position: "top-right" },
    route_summary: priorState.route_summary || response.proximity_result || {},
    proximity_summary: response.proximity_result || priorState.proximity_summary,
    parcel_context: response.parcel_context || priorState.parcel_context,
    table_context: response.table_context || priorState.table_context,
    warnings: response.warnings || priorState.warnings || [],
    missing_data: response.missing_data || priorState.missing_data || [],
    reviewer_notes: notes,
    adjusted_state_applied: Boolean(response.applied_adjustments || layers.length),
    export_mode: exportMode,
    export_options: exportOptions,
    print_export_options: exportOptions,
    report_section_config: normalizedReportConfig,
    updated_at: new Date().toISOString(),
  };
}

export function buildComposerExportPayload(args: BuildComposerMapStateSnapshotArgs): ComposerAdjustPayload | null {
  const { response, layers, mapTitle, mapSubtitle, notes, exportMode } = args;
  if (!response.composer_session_id) return null;
  const mapState = buildComposerMapStateSnapshot(args);
  return {
    composer_session_id: response.composer_session_id,
    map_title: mapTitle,
    map_description: mapSubtitle,
    notes,
    layer_order: layers.map((layer) => layer.layer_key),
    layers,
    active_map_extent: (mapState.map_extent || undefined) as ComposerAdjustPayload["active_map_extent"],
    report_config: mapState.report_section_config,
    export_mode: exportMode,
    export_options: mapState.export_options,
    map_state: mapState,
  };
}
