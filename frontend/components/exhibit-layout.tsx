import type { ReactNode } from "react";

import { ExhibitFooter } from "@/components/exhibit-footer";
import { ExhibitLayerTable } from "@/components/exhibit-layer-table";
import { ExhibitMapFrame } from "@/components/exhibit-map-frame";
import { ExhibitSourceNotes } from "@/components/exhibit-source-notes";
import { ExhibitTitleBlock } from "@/components/exhibit-title-block";
import { ExhibitWarningSummary } from "@/components/exhibit-warning-summary";
import type { ComposerResponse, PreviewLayer } from "@/types/automap";

type ExhibitLayoutProps = {
  response: ComposerResponse;
  sessionId: string;
  map: ReactNode;
  actions?: ReactNode;
};

function exhibitType(response: ComposerResponse): string {
  const requestType = response.request_type || "";
  const title = `${response.map_layout?.title || response.map_title || ""} ${response.raw_prompt || ""}`.toLowerCase();
  if (requestType.includes("proximity") || title.includes("nearest") || title.includes("route")) return "proximity_exhibit";
  if (requestType.includes("parcel") || title.includes("parcel")) return "parcel_context_exhibit";
  if (title.includes("flood")) return "flood_exposure_exhibit";
  if (title.includes("zoning")) return "zoning_context_exhibit";
  if (requestType.includes("scenario") || title.includes("suitability")) return "scenario_exhibit";
  return "general_reference_exhibit";
}

function warningList(response: ComposerResponse): string[] {
  const warnings = [
    ...(response.warnings || []),
    ...(response.preview_blockers || []),
    ...(response.missing_data || []).map((item) => `Missing data: ${item}`),
  ];
  if (response.proximity_result?.route_warning) warnings.push(response.proximity_result.route_warning);
  if (response.proximity_result?.property_match_status === "not_resolved") {
    warnings.push("Related parcel was not resolved from verified fields.");
  }
  warnings.push("Draft only - not an official county map.");
  warnings.push("No ArcGIS item was published.");
  return Array.from(new Set(warnings.filter(Boolean)));
}

function keyFindings(response: ComposerResponse): Array<{ label: string; value: string }> {
  const result = response.proximity_result;
  if (result) {
    return [
      { label: "Origin", value: String(result.origin_input || response.origin_type || "Not recorded") },
      { label: "Nearest target", value: String(result.target_name || result.target_type || "Not recorded") },
      {
        label: "Distance",
        value:
          typeof result.distance_value === "number"
            ? `${result.distance_value.toFixed(2)} ${result.distance_unit || "miles"}`
            : "Not calculated",
      },
      { label: "Route mode", value: String(result.route_label || result.route_mode || "Not a route map") },
      { label: "Related parcel", value: String(result.property_match_status || "Not applicable") },
    ];
  }
  return [
    { label: "Preview", value: response.can_preview ? "Ready" : "Needs review" },
    { label: "Selected layers", value: String(response.selected_layers?.length || 0) },
    { label: "Request type", value: response.request_type || "general_map" },
  ];
}

export function ExhibitLayout({ response, sessionId, map, actions }: ExhibitLayoutProps) {
  const preview = response.preview_config;
  const layout = response.map_layout || preview?.map_layout || {};
  const generatedAt = response.created_at ? new Date(response.created_at).toLocaleString() : new Date().toLocaleString();
  const contextLayers: PreviewLayer[] = preview?.context_layers || preview?.operational_layers || [];
  const derivedLayers = preview?.derived_overlays || [];
  const findings = keyFindings(response);
  const mapState = response.composer_map_state || {};
  const exportMode = mapState.export_mode || mapState.export_options?.export_mode || "map_exhibit_only";
  const reportConfig = mapState.report_section_config || {};
  const isFullReport = exportMode === "full_report";
  const isMapSummary = exportMode === "map_plus_summary" || exportMode === "map_summary";
  const showKeyFindings = mapState.export_options?.include_key_findings !== false || isMapSummary || isFullReport;
  const showLayerTable = Boolean(reportConfig.include_layer_table || isFullReport);
  const showWarnings = Boolean(reportConfig.include_warnings || isFullReport);
  const showSourceNotes = Boolean(reportConfig.include_source_notes && exportMode !== "map_exhibit_only") || isFullReport;
  const warningItems = warningList(response);
  const visibleWarnings = exportMode === "map_exhibit_only" ? warningItems.slice(0, 4) : warningItems;

  return (
    <main className={`composer-print-page exhibit-layout exhibit-layout-${exportMode}`} data-export-mode={exportMode}>
      <ExhibitTitleBlock
        title={layout.title || response.map_title || "AutoMap Draft Exhibit"}
        subtitle={layout.subtitle || "Draft preview only."}
        prompt={response.raw_prompt || response.prompt}
        generatedAt={generatedAt}
        mapType={exhibitType(response)}
        requestType={response.request_type}
        sessionId={sessionId}
        disclaimer={layout.disclaimer}
      />

      {actions ? <div className="exhibit-actions no-print">{actions}</div> : null}

      <ExhibitMapFrame>{map}</ExhibitMapFrame>

      {showKeyFindings ? (
      <section className="exhibit-key-findings">
        <h2>Key findings / map notes</h2>
        <dl>
          {findings.map((finding) => (
            <div key={finding.label}>
              <dt>{finding.label}</dt>
              <dd>{finding.value}</dd>
            </div>
          ))}
        </dl>
      </section>
      ) : null}

      {showLayerTable ? <ExhibitLayerTable contextLayers={contextLayers} derivedLayers={derivedLayers} /> : null}
      {showWarnings ? <ExhibitWarningSummary warnings={visibleWarnings} /> : null}
      {showSourceNotes ? <ExhibitSourceNotes /> : null}
      <ExhibitFooter />
    </main>
  );
}
