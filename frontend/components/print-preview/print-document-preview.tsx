import type { ComposerMapState, ComposerResponse } from "@/types/automap";
import type { LivePrintOptions } from "@/types/print-options";

import { PrintLayerTableSection } from "./print-layer-table-section";
import { PrintMapPagePreview } from "./print-map-page-preview";
import { PrintSourceNotesSection } from "./print-source-notes-section";
import { PrintStatisticsSection } from "./print-statistics-section";
import { PrintSummarySection } from "./print-summary-section";
import { PrintWarningSection } from "./print-warning-section";

type PrintDocumentPreviewProps = {
  mapState?: ComposerMapState | null;
  packetId?: string;
  printOptions: LivePrintOptions;
  response: ComposerResponse | null;
};

function mapSummaryItems(response: ComposerResponse | null, mapState?: ComposerMapState | null) {
  return [
    { label: "Request type", value: response?.request_type || mapState?.request_type || "general_map" },
    { label: "Visible layers", value: String(mapState?.visible_layers?.length || response?.selected_layers?.length || 0) },
    { label: "Derived overlays", value: String(mapState?.derived_overlays?.length || response?.preview_config?.derived_overlays?.length || 0) },
    { label: "Locked state", value: mapState?.adjusted_state_applied ? "Adjusted and locked" : "Saved draft state" },
  ];
}

function keyFindingItems(response: ComposerResponse | null, mapState?: ComposerMapState | null) {
  const proximity = mapState?.proximity_summary || response?.proximity_result;
  if (proximity) {
    return [
      { label: "Origin", value: String(proximity.origin_input || response?.origin_type || "Not recorded") },
      { label: "Target", value: String(proximity.target_name || proximity.target_type || "Not recorded") },
      {
        label: "Distance",
        value:
          typeof proximity.distance_value === "number"
            ? `${proximity.distance_value.toFixed(2)} ${proximity.distance_unit || "miles"}`
            : "Not calculated",
      },
      { label: "Route mode", value: String(proximity.route_label || proximity.route_mode || "Not applicable") },
    ];
  }
  return mapSummaryItems(response, mapState);
}

function parcelItems(response: ComposerResponse | null, mapState?: ComposerMapState | null) {
  const parcel = mapState?.parcel_context || response?.parcel_context || {};
  return [
    { label: "Parcel match", value: String(parcel.match_status || parcel.origin_match_status || "Not available") },
    { label: "Matched count", value: String(parcel.matched_count ?? "Not available") },
    { label: "Selected geometry", value: parcel.selected_parcel_geojson_path ? "Resolved local output" : "Not resolved" },
  ];
}

function proximityItems(response: ComposerResponse | null, mapState?: ComposerMapState | null) {
  const proximity = mapState?.proximity_summary || response?.proximity_result || {};
  return [
    { label: "Origin", value: String(proximity.origin_input || "Not recorded") },
    { label: "Nearest target", value: String(proximity.target_name || proximity.target_type || "Not recorded") },
    {
      label: "Distance",
      value:
        typeof proximity.distance_value === "number"
          ? `${proximity.distance_value.toFixed(2)} ${proximity.distance_unit || "miles"}`
          : "Not calculated",
    },
    { label: "Route mode", value: String(proximity.route_label || proximity.route_mode || "Not available") },
  ];
}

export function PrintDocumentPreview({ mapState, packetId, printOptions, response }: PrintDocumentPreviewProps) {
  const isMapSheet = printOptions.exportMode === "map_sheet";
  return (
    <article className={`print-document-preview print-document-preview-${printOptions.exportMode}`}>
      <PrintMapPagePreview mapState={mapState} packetId={packetId} printOptions={printOptions} response={response} />
      {!isMapSheet && printOptions.includeMapSummary ? <PrintSummarySection title="Map Summary" items={mapSummaryItems(response, mapState)} /> : null}
      {!isMapSheet && printOptions.includeKeyFindings ? <PrintSummarySection title="Key Findings" items={keyFindingItems(response, mapState)} /> : null}
      {!isMapSheet && printOptions.includeProximitySummary ? (
        <PrintSummarySection title="Proximity Summary" items={proximityItems(response, mapState)} />
      ) : null}
      {!isMapSheet && printOptions.includeParcelSummary ? <PrintSummarySection title="Parcel Summary" items={parcelItems(response, mapState)} /> : null}
      {!isMapSheet && printOptions.includeStatistics ? <PrintStatisticsSection mapState={mapState} response={response} /> : null}
      {!isMapSheet && printOptions.includePermitSummary ? (
        <PrintSummarySection
          title="Permit Summary"
          note="Official current permit source remains unresolved."
          items={[{ label: "Status", value: "Unavailable - unresolved source" }]}
        />
      ) : null}
      {!isMapSheet && printOptions.includePlanningSummary ? (
        <PrintSummarySection
          title="Planning Case Summary"
          note="Planning case coverage depends on verified geography-specific sources."
          items={[{ label: "Status", value: "Unavailable unless verified source covers the request" }]}
        />
      ) : null}
      {!isMapSheet && printOptions.includeDevelopmentProxySummary ? (
        <PrintSummarySection
          title="Development Proxy Summary"
          note="Proxy sources are context only and not official approvals."
          items={[{ label: "Status", value: "Unavailable unless proxy source was requested and bounded" }]}
        />
      ) : null}
      {!isMapSheet && printOptions.includeLayerTable ? <PrintLayerTableSection mapState={mapState} response={response} /> : null}
      {!isMapSheet && printOptions.includeWarnings ? <PrintWarningSection mapState={mapState} response={response} /> : null}
      {!isMapSheet && printOptions.includeSourceNotes ? <PrintSourceNotesSection /> : null}
    </article>
  );
}
