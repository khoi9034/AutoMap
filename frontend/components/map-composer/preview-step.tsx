"use client";

import Link from "next/link";
import { useState } from "react";

import { SharedMapRenderer } from "@/components/map-renderer/shared-map-renderer";
import { StatusChip } from "@/components/status-chip";
import { isRoadRouteMode } from "@/lib/map-symbols";
import type { ComposerResponse, ProximityResult } from "@/types/automap";

import { actionLabel, canShowComposerMap, composerDisplayTitle, composerResultState, identifierText, isAddressFocused, isPartialContextMap } from "./utils";

type PreviewStepProps = {
  loading?: boolean;
  onGoToAdjust: () => void;
  onGoToExport: () => void;
  onGoToRequest: () => void;
  onRegenerate: () => void;
  onRouteRefine?: () => void;
  previewPacketId: string;
  response: ComposerResponse | null;
  routeRefineLoading?: boolean;
};

type PreviewDetailsTab = "summary" | "layers" | "route" | "notes" | "diagnostics";

const PREVIEW_DETAIL_TABS: Array<{ id: PreviewDetailsTab; label: string }> = [
  { id: "summary", label: "Summary" },
  { id: "layers", label: "Layers" },
  { id: "route", label: "Route / Analysis" },
  { id: "notes", label: "Notes" },
  { id: "diagnostics", label: "Diagnostics" },
];

function isPartialFloodplainContext(response: ComposerResponse): boolean {
  return Boolean(response.floodplain_screening && composerResultState(response) === "partial");
}

export function PreviewBlocker({
  response,
  onGoToRequest,
}: {
  response: ComposerResponse;
  onGoToRequest: () => void;
}) {
  const floodplainPartial = isPartialFloodplainContext(response);
  const resultState = composerResultState(response);
  if (resultState === "no_matches") {
    const triedRows = response.visible_feature_summary || response.preview_config?.visible_feature_summary || [];
    return (
      <section className="panel parcel-preview-blocked" role="status">
        <p className="eyebrow">No matches</p>
        <h3>No matching features found</h3>
        <p>
          AutoMap found relevant catalog layers, but the requested filter/AOI returned no visible features. A normal map preview is hidden so the
          legend does not imply layers were successfully drawn.
        </p>
        {triedRows.length ? (
          <div className="definition-box">
            <strong>What AutoMap tried</strong>
            <ul className="compact-list">
              {triedRows.slice(0, 4).map((row, index) => (
                <li key={`${String(row.layer_id || row.layer_title || "layer")}-${index}`}>
                  {String(row.layer_title || row.layer_id || "Layer")}: {String(row.feature_count ?? "unchecked")} features
                </li>
              ))}
            </ul>
          </div>
        ) : null}
        <div className="button-row">
          <button className="button" type="button" onClick={onGoToRequest}>
            Try broader request
          </button>
        </div>
      </section>
    );
  }
  if (floodplainPartial) {
    const blockerText =
      response.preview_blockers?.[0] ||
      "AutoMap found the Concord boundary and 100-year floodplain, but could not complete the parcel intersection.";
    if (isPartialContextMap(response)) {
      return (
        <section className="panel parcel-preview-blocked composer-partial-context-banner" role="status">
          <p className="eyebrow">Partial context map</p>
          <h3>Parcel intersection unavailable</h3>
          <p>{blockerText}</p>
          <div className="button-row">
            <button className="button button-secondary" type="button" onClick={onGoToRequest}>
              Try broader request
            </button>
          </div>
        </section>
      );
    }
    return (
      <section className="panel parcel-preview-blocked" role="alert">
        <p className="eyebrow">Floodplain screening partial</p>
        <h3>Parcel intersection unavailable</h3>
        <p>{blockerText}</p>
        <div className="definition-box">
          <strong>What AutoMap found</strong>
          <p>Concord boundary and 100-year floodplain context are available, but the requested affected parcel result is missing.</p>
        </div>
        <div className="button-row">
          <button className="button" type="button" onClick={onGoToRequest}>
            Try broader request
          </button>
        </div>
      </section>
    );
  }
  if (resultState === "blocked" && !response.parcel_context && !isAddressFocused(response)) {
    const blockerText = response.preview_blockers?.[0] || "AutoMap could not build a visible map preview for this request.";
    return (
      <section className="panel parcel-preview-blocked" role="alert">
        <p className="eyebrow">Preview blocked</p>
        <h3>Map data could not be shown</h3>
        <p>{blockerText}</p>
        <div className="button-row">
          <button className="button" type="button" onClick={onGoToRequest}>
            Try broader request
          </button>
        </div>
      </section>
    );
  }
  const context = response.parcel_context;
  const isAddress = isAddressFocused(response);
  const blockerText = response.preview_blockers?.[0] || context?.reason_if_not_focusable || "";
  if (!response.preview_blockers?.length && context?.can_focus_map !== false && response.recipe?.origin_context?.can_preview !== false) return null;
  const candidates = [...(response.origin_candidates || []), ...(context?.candidate_matches || [])];
  const hasAddressCandidates = isAddress && candidates.length > 0;
  const unsupportedArea = response.origin_match_status === "unsupported_area" || context?.match_status === "unsupported_area";
  const addressHeading = hasAddressCandidates
    ? "Multiple possible address matches"
    : unsupportedArea
      ? "Address not found in Cabarrus County records"
      : "Address not found";
  const addressGuidance =
    "AutoMap's live address lookup currently supports Cabarrus County, NC only. Try a Cabarrus County address, parcel/PIN, or planning request.";
  return (
    <section className="panel parcel-preview-blocked" role="alert">
      <p className="eyebrow">{isAddress ? "Address-focused preview blocked" : "Parcel-focused preview blocked"}</p>
      <h3>{isAddress ? addressHeading : "Parcel not matched"}</h3>
      <p>
        {blockerText ||
          (isAddress
            ? `Address not found in Cabarrus County records. ${addressGuidance}`
            : "Parcel not matched. AutoMap cannot zoom to or map this parcel until a valid parcel/PIN/address is provided.")}
      </p>
      {isAddress ? (
        <div className="definition-box">
          <strong>Supported address area</strong>
          <p>{addressGuidance}</p>
        </div>
      ) : null}
      <div className="detail-grid">
        <div>
          <span className="muted">Match status</span>
          <strong>{response.origin_match_status || context?.match_status || "needs_review"}</strong>
        </div>
        <div>
          <span className="muted">Origin type</span>
          <strong>{response.origin_type || context?.origin_type || context?.input_type || "unknown"}</strong>
        </div>
        <div>
          <span className="muted">Next action</span>
          <strong>{actionLabel(response.next_action)}</strong>
        </div>
      </div>
      <div className="definition-box">
        <strong>What AutoMap tried</strong>
        <p>
          {isAddress
            ? "It searched verified Cabarrus County public address and parcel/address fields without using owner/name fields."
            : "It searched verified parcel/PIN/PIN14 fields and did not fetch parcel geometry."}
        </p>
      </div>
      {context?.unmatched_identifiers?.length ? (
        <div className="definition-box">
          <strong>Unmatched identifiers</strong>
          <p>{context.unmatched_identifiers.map(identifierText).join(", ")}</p>
        </div>
      ) : null}
      {candidates.length ? (
        <div className="definition-box">
          <strong>Candidate matches</strong>
          <div className="candidate-choice-list">
            {candidates.slice(0, 6).map((candidate, index) => (
              <div className="candidate-choice-row" key={`${identifierText(candidate)}-${index}`}>
                <span>{identifierText(candidate)}</span>
                <button className="button button-secondary button-small" type="button" disabled>
                  Select Candidate
                </button>
              </div>
            ))}
          </div>
        </div>
      ) : null}
      <button className="button" type="button" onClick={onGoToRequest}>
        {isAddress ? "Try corrected address" : "Correct address/PIN"}
      </button>
    </section>
  );
}

export function ProximityResultSummary({
  result,
  onRouteRefine,
  routeRefineLoading = false,
}: {
  result?: ProximityResult | null;
  onRouteRefine?: () => void;
  routeRefineLoading?: boolean;
}) {
  if (!result) return null;
  const targetKind =
    result.target_type === "nearest_fire_ems_station" || result.target_classification === "mixed_fire_ems"
      ? "nearest fire/EMS station"
      : result.target_type === "nearest_fire_station"
        ? "nearest fire station"
        : "nearest facility";
  const targetLabel = result.target_name || targetKind || "Proximity result";
  const distance = typeof result.distance_value === "number" ? `${result.distance_value.toFixed(2)} ${result.distance_unit || "miles"}` : "Needs review";
  const lineReady = Boolean(result.line_geojson_path || result.line_geojson_url);
  const roadRoute = isRoadRouteMode(result.route_mode);
  const routeLabel = result.route_label || (roadRoute ? "Road-following draft route" : "Straight-line fallback");
  const routeWarning = result.route_warning || (roadRoute ? "Not official navigation." : "Road route unavailable.");
  const distanceMethod = result.nearest_facility_method === "road_distance" ? "road distance" : "straight-line fallback";
  return (
    <section className="panel proximity-summary-panel">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Nearest facility draft</p>
          <h3>
            {targetKind.charAt(0).toUpperCase() + targetKind.slice(1)} found: {targetLabel}
          </h3>
          <p className="muted">
            {routeLabel}. {routeWarning}
          </p>
        </div>
        <StatusChip tone={result.status === "ok" ? "success" : "warning"}>{result.status || "needs_review"}</StatusChip>
      </div>
      <div className="result-strip">
        <div>
          <span>Origin</span>
          <strong>{result.origin_type || "address"}</strong>
        </div>
        <div>
          <span>Target</span>
          <strong>{targetKind}</strong>
        </div>
        <div>
          <span>Distance</span>
          <strong>{distance}</strong>
        </div>
        <div>
          <span>Route mode</span>
          <strong>{lineReady ? routeLabel : "Needs review"}</strong>
        </div>
        <div>
          <span>Nearest method</span>
          <strong>{distanceMethod}</strong>
        </div>
      </div>
      {result.property_match_status === "not_resolved" ? (
        <p className="muted">Address matched, but related parcel was not resolved from verified fields.</p>
      ) : null}
      {result.route_refinement_available ? (
        <div className="definition-box">
          <strong>Road-following route refinement available</strong>
          <p>The live result is using a straight-line fallback. AutoMap can try a bounded road-following draft separately.</p>
          {onRouteRefine ? (
            <button className="button button-secondary" type="button" onClick={onRouteRefine} disabled={routeRefineLoading}>
              {routeRefineLoading ? "Trying Road-Following Route..." : "Try Road-Following Route"}
            </button>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}

export function SelectedLayersAndWarnings({ response }: { response: ComposerResponse }) {
  return (
    <section className="panel composer-layer-summary">
      <p className="eyebrow">Draft contents</p>
      <div className="composer-summary-columns">
        <div>
          <h4>Selected layers</h4>
          {response.selected_layers?.length ? (
            <ul className="compact-list">
              {response.selected_layers.slice(0, 8).map((layer) => (
                <li key={`${layer.layer_key}-${layer.role}`}>
                  <strong>{layer.layer_name || layer.layer_key}</strong>
                  <span>{layer.role || layer.category || "context"}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted">No map layers are ready until the origin is matched.</p>
          )}
        </div>
        <div>
          <h4>Warnings</h4>
          {response.warnings?.length ? (
            <ul className="compact-list">
              {response.warnings.slice(0, 8).map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : (
            <p className="muted">No warnings yet.</p>
          )}
        </div>
      </div>
    </section>
  );
}

function PreviewSummaryPanel({
  loading,
  onGoToAdjust,
  onGoToExport,
  onRegenerate,
  previewReady,
  response,
  statusLabel,
  statusTone,
}: {
  loading?: boolean;
  onGoToAdjust: () => void;
  onGoToExport: () => void;
  onRegenerate: () => void;
  previewReady: boolean;
  response: ComposerResponse;
  statusLabel: string;
  statusTone: "success" | "warning" | "danger";
}) {
  const proximity = response.proximity_result;
  const target = proximity?.target_name || "Needs review";
  const partialContext = composerResultState(response) === "partial";
  return (
    <section className="composer-preview-summary-card">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Preview</p>
          <h3>{composerDisplayTitle(response)}</h3>
          {response.map_layout?.subtitle ? <p className="muted">{response.map_layout.subtitle}</p> : null}
        </div>
        <StatusChip tone={statusTone}>{statusLabel}</StatusChip>
      </div>
      <div className="result-strip compact-result-strip">
        <div>
          <span>Layers</span>
          <strong>{response.selected_layers?.length || 0}</strong>
        </div>
        <div>
          <span>Next</span>
          <strong>{partialContext ? "Context map available" : actionLabel(response.next_action)}</strong>
        </div>
      </div>
      {proximity ? (
        <div className="definition-box composer-quick-facts">
          <strong>Nearest facility</strong>
          <p>{target}</p>
          <dl>
            <div>
              <dt>Route mode</dt>
              <dd>{proximity.route_label || proximity.route_mode || "Needs review"}</dd>
            </div>
            <div>
              <dt>Method</dt>
              <dd>{proximity.nearest_facility_method === "road_distance" ? "Road distance" : "Straight-line fallback"}</dd>
            </div>
          </dl>
        </div>
      ) : null}
      <WhyThisMapPanel response={response} />
      <div className="button-row composer-preview-actions">
        <button className="button" type="button" onClick={onGoToAdjust} disabled={!previewReady}>
          {partialContext ? "Adjust context map" : "Continue to Adjust"}
        </button>
        <button className="button button-secondary" type="button" onClick={onRegenerate} disabled={loading}>
          Regenerate Draft
        </button>
        <button className="button button-secondary" type="button" onClick={onGoToExport} disabled={!previewReady}>
          {partialContext ? "Print partial context map" : "Print / Export"}
        </button>
      </div>
    </section>
  );
}

function planFromResponse(response: ComposerResponse): Record<string, unknown> {
  return (response.request_plan || response.recipe?.request_plan || {}) as Record<string, unknown>;
}

function planParameters(response: ComposerResponse): Record<string, unknown> {
  const parameters = planFromResponse(response).parameters;
  return parameters && typeof parameters === "object" && !Array.isArray(parameters) ? (parameters as Record<string, unknown>) : {};
}

function valueList(value: unknown): string {
  if (Array.isArray(value)) return value.map((item) => String(item)).filter(Boolean).join(", ");
  if (value === null || value === undefined || value === "") return "Not specified";
  return String(value);
}

function visibleFeatureCount(response: ComposerResponse): number | null {
  const total = response.preview_config?.visible_feature_total;
  if (typeof total === "number") return total;
  const rows = response.visible_feature_summary || response.preview_config?.visible_feature_summary || [];
  if (!rows.length) return null;
  return rows.reduce((sum, row) => sum + (typeof row.feature_count === "number" ? row.feature_count : 0), 0);
}

function aoiSummary(response: ComposerResponse): string | null {
  const aoi = response.preview_config?.aoi;
  if (!aoi || typeof aoi !== "object") return null;
  if (typeof aoi.summary === "string" && aoi.summary.trim()) return aoi.summary;
  const geography = typeof aoi.geography_name === "string" ? aoi.geography_name : null;
  const buffer = aoi.buffer_distance && typeof aoi.buffer_distance === "object" && !Array.isArray(aoi.buffer_distance) ? aoi.buffer_distance : null;
  const bufferValue = typeof buffer?.value === "number" ? buffer.value : null;
  if (!geography) return null;
  return bufferValue && bufferValue > 0 ? `${geography} + ${bufferValue} mile buffer` : geography;
}

function WhyThisMapPanel({ response }: { response: ComposerResponse }) {
  const plan = planFromResponse(response);
  const params = planParameters(response);
  const screening = response.floodplain_screening;
  const resultState = composerResultState(response);
  const totalFeatures = visibleFeatureCount(response);
  const fallbackUsed = Boolean(response.preview_config?.visible_map_qa?.fallback_used);
  const screeningPartial = Boolean(screening && resultState === "partial");
  const aoi = aoiSummary(response);
  const requestedResult = response.requested_result || "Parcels in 100-year floodplain";
  const availableContext = response.available_context?.length ? response.available_context.join(", ") : "100-year floodplain, Concord boundary";
  const missingOperation = response.missing_operation || "Parcel-floodplain intersection";
  const howToRead = response.map_layout?.how_to_read || response.preview_config?.map_layout?.how_to_read || null;
  const requestLabel =
    response.analysis_type === "floodplain_parcel_screening" || screening
      ? "Floodplain parcel screening"
      : String(plan.request_type || response.request_type || "General map").replaceAll("_", " ");
  return (
    <div className="definition-box why-this-map-panel">
      <strong>Why this map?</strong>
      <dl>
        <div>
          <dt>Interpreted request</dt>
          <dd>{requestLabel}</dd>
        </div>
        <div>
          <dt>Area</dt>
          <dd>{valueList(params.geography)}</dd>
        </div>
        {aoi ? (
          <div>
            <dt>AOI</dt>
            <dd>{aoi}</dd>
          </div>
        ) : null}
        {screeningPartial ? (
          <>
            <div>
              <dt>Requested result</dt>
              <dd>{requestedResult}</dd>
            </div>
            <div>
              <dt>Available context</dt>
              <dd>{availableContext}</dd>
            </div>
            <div>
              <dt>Missing operation</dt>
              <dd>{missingOperation}</dd>
            </div>
          </>
        ) : (
          <div>
            <dt>Primary result</dt>
            <dd>{screening ? "Parcels in 100-year floodplain" : valueList(params.feature_type)}</dd>
          </div>
        )}
        <div>
          <dt>Filter</dt>
          <dd>{screening ? "100-year / 1% annual chance floodplain" : valueList(params.subtype_filter)}</dd>
        </div>
        <div>
          <dt>Status</dt>
          <dd>{screeningPartial ? "Partial context map" : resultState === "no_matches" ? "No matching parcels found" : fallbackUsed ? "Live result with fallback" : "Live result"}</dd>
        </div>
        {totalFeatures !== null ? (
          <div>
            <dt>Visible features</dt>
            <dd>{totalFeatures}</dd>
          </div>
        ) : null}
        {howToRead ? (
          <div>
            <dt>How to read</dt>
            <dd>{howToRead}</dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}

function FloodplainScreeningPanel({ response }: { response: ComposerResponse }) {
  const screening = response.floodplain_screening;
  if (!screening && response.analysis_type !== "floodplain_parcel_screening") return null;
  const affectedCount =
    typeof response.affected_feature_count === "number"
      ? response.affected_feature_count
      : typeof screening?.affected_feature_count === "number"
        ? screening.affected_feature_count
        : null;
  const area = response.aoi_name || (typeof screening?.aoi_name === "string" ? screening.aoi_name : "Concord");
  const warning = typeof screening?.warning === "string" ? screening.warning : null;
  const resultState = composerResultState(response);
  const partial = resultState === "partial";
  const noMatches = resultState === "no_matches";
  return (
    <section className="panel floodplain-screening-summary">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Spatial screening</p>
          <h3>Floodplain parcel screening</h3>
          <p className="muted">
            {partial
              ? `Affected parcel extraction unavailable; showing 100-year floodplain context in ${area}, NC.`
              : noMatches
                ? `No parcels were found intersecting the 100-year floodplain in ${area}, NC.`
              : `Parcels intersecting the 100-year floodplain in ${area}, NC.`}
          </p>
        </div>
        <StatusChip tone={partial || noMatches || warning ? "warning" : "success"}>{partial ? "Partial" : noMatches ? "No matches" : warning ? "Needs review" : "Live result"}</StatusChip>
      </div>
      <div className="result-strip">
        <div>
          <span>Area</span>
          <strong>{area}</strong>
        </div>
        <div>
          <span>Relationship</span>
          <strong>{response.spatial_relationship || "intersects"}</strong>
        </div>
        <div>
          <span>Affected parcels</span>
          <strong>{affectedCount ?? "n/a"}</strong>
        </div>
        <div>
          <span>Flood type</span>
          <strong>100-year</strong>
        </div>
      </div>
      <p className="muted">Draft screening only. Not an official flood determination.</p>
      {warning ? <p className="muted">{warning}</p> : null}
    </section>
  );
}

function TableContextPanel({ response }: { response: ComposerResponse }) {
  const tableContext = response.table_context;
  const recipe = tableContext?.table_recipe;
  if (!tableContext?.table_requested) return null;
  const previewRows = tableContext.preview_rows || recipe?.preview_rows || [];
  const fieldNames = (recipe?.selected_fields || [])
    .map((field) => field.alias || field.name)
    .filter(Boolean)
    .slice(0, 8) as string[];
  const exportDraft = tableContext.export_status !== "export_ready";
  return (
    <section className="panel table-preview-summary">
      <p className="eyebrow">Table/data request</p>
      <h3>{recipe?.table_title || "This looks like a table request"}</h3>
      <p className="muted">
        Table preview live. AutoMap planned a returnGeometry=false workflow with {recipe?.selected_fields?.length || 0} selected fields and
        an estimated {recipe?.estimated_count ?? "unknown"} rows.
      </p>
      <div className="result-strip">
        <div>
          <span>Output</span>
          <strong>Table preview</strong>
        </div>
        <div>
          <span>Safety</span>
          <strong>{recipe?.safety_status || "needs_review"}</strong>
        </div>
        <div>
          <span>CSV export</span>
          <strong>{exportDraft ? "Draft/refine" : "Ready"}</strong>
        </div>
      </div>
      <h4>Selected columns</h4>
      <p className="muted">{fieldNames.length ? fieldNames.join(", ") : "No verified fields selected yet."}</p>
      {previewRows.length ? (
        <div className="table-scroll compact-table-preview">
          <table className="data-table">
            <thead>
              <tr>
                {Object.keys(previewRows[0])
                  .slice(0, 6)
                  .map((field) => (
                    <th key={field}>{field}</th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {previewRows.slice(0, 5).map((row, index) => (
                <tr key={`composer-table-row-${index}`}>
                  {Object.keys(previewRows[0])
                    .slice(0, 6)
                    .map((field) => (
                      <td key={field}>{String(row[field] ?? "")}</td>
                    ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No preview rows yet. Field selection and safety limits are still visible without downloading geometry.</p>
      )}
      {recipe?.warnings?.length ? (
        <ul className="compact-list">
          {recipe.warnings.slice(0, 3).map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
      <div className="button-row">
        <Link className="button button-secondary" href={`/tables?prompt=${encodeURIComponent(response.raw_prompt || response.prompt || "")}`}>
          Open Table Center
        </Link>
      </div>
    </section>
  );
}

function PreviewNotesPanel({ response }: { response: ComposerResponse }) {
  return (
    <section className="composer-preview-notes">
      <div className="definition-box">
        <strong>Cabarrus County scope</strong>
        <p>Live address and parcel workflows support Cabarrus County, NC only.</p>
      </div>
      <div className="definition-box">
        <strong>Draft safety</strong>
        <p>Real ArcGIS publishing is disabled. Outputs are draft review artifacts, not official county maps.</p>
      </div>
      {response.warnings?.length ? (
        <div className="definition-box">
          <strong>Key limitations</strong>
          <ul className="compact-list">
            {response.warnings.slice(0, 5).map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function PreviewDiagnosticsPanel({ response }: { response: ComposerResponse }) {
  const qaRows = response.visible_feature_summary || response.preview_config?.visible_feature_summary || [];
  const qaWarnings = (response.preview_config?.visible_map_qa?.warnings as string[] | undefined) || [];
  const complexity = response.preview_config?.display_complexity || response.preview_config?.visible_map_qa?.display_complexity;
  const complexityRecord = complexity && typeof complexity === "object" && !Array.isArray(complexity) ? complexity : null;
  const planSummary = response.map_plan_summary && typeof response.map_plan_summary === "object" && !Array.isArray(response.map_plan_summary) ? response.map_plan_summary : null;
  return (
    <section className="composer-preview-diagnostics">
      <div className="result-strip compact-result-strip">
        <div>
          <span>Missing data</span>
          <strong>{response.missing_data?.length || 0}</strong>
        </div>
        <div>
          <span>Blockers</span>
          <strong>{response.preview_blockers?.length || 0}</strong>
        </div>
        <div>
          <span>Visible features</span>
          <strong>{visibleFeatureCount(response) ?? "n/a"}</strong>
        </div>
        <div>
          <span>AOI</span>
          <strong>{aoiSummary(response) || "n/a"}</strong>
        </div>
      </div>
      <div className="definition-box">
        <strong>Planner</strong>
        <p>
          {String(response.planner_used || "deterministic")}
          {response.ai_status ? ` · ${response.ai_status}` : ""}
          {response.ai_model_used ? ` · ${response.ai_model_used}` : ""}
          {typeof response.ai_confidence === "number" ? ` · ${Math.round(response.ai_confidence * 100)}% confidence` : ""}
        </p>
        {response.ai_error_message_safe ? <p className="muted">{response.ai_error_type || response.ai_error_category}: {response.ai_error_message_safe}</p> : null}
        {planSummary ? (
          <ul className="compact-list">
            {planSummary.interpreted_request ? <li>Interpreted request: {String(planSummary.interpreted_request)}</li> : null}
            {planSummary.main_operation ? <li>Main operation: {String(planSummary.main_operation)}</li> : null}
            {planSummary.primary_result ? <li>Primary result: {String(planSummary.primary_result)}</li> : null}
            {planSummary.fallback_strategy ? <li>Fallback: {String(planSummary.fallback_strategy)}</li> : null}
          </ul>
        ) : null}
      </div>
      {complexityRecord ? (
        <div className="definition-box">
          <strong>Display complexity</strong>
          <p>
            {String(complexityRecord.status || "checked")} · {String(complexityRecord.visible_layer_count ?? "n/a")} visible layers
            {complexityRecord.simplified ? " · simplified for readability" : ""}
          </p>
        </div>
      ) : null}
      {qaRows.length ? (
        <div className="definition-box">
          <strong>Visible map QA</strong>
          <ul className="compact-list">
            {qaRows.slice(0, 8).map((row, index) => (
              <li key={`${String(row.layer_id || row.layer_title || "layer")}-${index}`}>
                <strong>{String(row.layer_title || row.layer_id || "Layer")}</strong>
                <span>
                  {String(row.expected_role || "context")} · {row.visible === false ? "hidden" : `${String(row.feature_count ?? "unchecked")} features`}
                  {row.clipped_to_aoi ? " · clipped to AOI" : ""}
                  {row.fallback_used ? " · fallback used" : ""}
                  {row.simplification_applied ? " · simplified" : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {qaWarnings.length ? (
        <div className="definition-box">
          <strong>QA notes</strong>
          <ul className="compact-list">
            {qaWarnings.slice(0, 5).map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {response.preview_blockers?.length ? (
        <div className="definition-box">
          <strong>Preview blockers</strong>
          <ul className="compact-list">
            {response.preview_blockers.slice(0, 5).map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="muted">No technical blockers for this draft.</p>
      )}
    </section>
  );
}

function PreviewDetailsPanel({
  loading,
  onGoToAdjust,
  onGoToExport,
  onRegenerate,
  onRouteRefine,
  previewReady,
  response,
  routeRefineLoading,
  statusLabel,
  statusTone,
}: {
  loading?: boolean;
  onGoToAdjust: () => void;
  onGoToExport: () => void;
  onRegenerate: () => void;
  onRouteRefine?: () => void;
  previewReady: boolean;
  response: ComposerResponse;
  routeRefineLoading?: boolean;
  statusLabel: string;
  statusTone: "success" | "warning" | "danger";
}) {
  const [activeTab, setActiveTab] = useState<PreviewDetailsTab>("summary");
  const tableRequest = Boolean(response.table_context?.table_requested);
  return (
    <section className="panel composer-preview-details-panel">
      <div className="composer-preview-tab-list" role="tablist" aria-label="Preview details">
        {PREVIEW_DETAIL_TABS.map((tab) => (
          <button
            aria-selected={activeTab === tab.id}
            className={activeTab === tab.id ? "composer-preview-tab composer-preview-tab-active" : "composer-preview-tab"}
            key={tab.id}
            role="tab"
            type="button"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="composer-preview-tab-panel" role="tabpanel">
        {activeTab === "summary" ? (
          <PreviewSummaryPanel
            loading={loading}
            onGoToAdjust={onGoToAdjust}
            onGoToExport={onGoToExport}
            onRegenerate={onRegenerate}
            previewReady={previewReady}
            response={response}
            statusLabel={statusLabel}
            statusTone={statusTone}
          />
        ) : null}
        {activeTab === "layers" ? <SelectedLayersAndWarnings response={response} /> : null}
        {activeTab === "route" ? (
          <>
            <ProximityResultSummary result={response.proximity_result} onRouteRefine={onRouteRefine} routeRefineLoading={routeRefineLoading} />
            <FloodplainScreeningPanel response={response} />
            {tableRequest ? <TableContextPanel response={response} /> : null}
            {!response.proximity_result && !response.floodplain_screening && response.analysis_type !== "floodplain_parcel_screening" && !tableRequest ? (
              <p className="muted">No route or table analysis is attached to this draft.</p>
            ) : null}
          </>
        ) : null}
        {activeTab === "notes" ? <PreviewNotesPanel response={response} /> : null}
        {activeTab === "diagnostics" ? <PreviewDiagnosticsPanel response={response} /> : null}
      </div>
    </section>
  );
}

export function PreviewStep({
  loading,
  onGoToAdjust,
  onGoToExport,
  onGoToRequest,
  onRegenerate,
  onRouteRefine,
  previewPacketId,
  response,
  routeRefineLoading = false,
}: PreviewStepProps) {
  if (!response) {
    return (
      <section className="panel empty-state">
        <h3>No draft yet</h3>
        <p>Start with the Request step, then AutoMap will open a focused preview here.</p>
      </section>
    );
  }

  const previewReady = canShowComposerMap(response);
  const tableRequest = Boolean(response.table_context?.table_requested);
  const resultState = composerResultState(response);
  const floodplainPartial = isPartialFloodplainContext(response);
  const showMap = previewReady;
  const statusLabel = resultState === "ready" ? "Ready" : tableRequest ? "Table draft" : resultState === "no_matches" ? "No matches" : floodplainPartial ? "Partial" : resultState === "unsupported" ? "Unsupported" : "Blocked";
  const statusTone = resultState === "ready" ? "success" : tableRequest || resultState === "partial" || resultState === "no_matches" ? "warning" : "danger";
  return (
    <section className="composer-preview-layout">
      <div className="composer-preview-main">
        <div className="panel composer-compact-request">
          <span className="eyebrow">Original request</span>
          <p>{response.raw_prompt || response.prompt}</p>
        </div>
        {tableRequest && !previewReady ? (
          <TableContextPanel response={response} />
        ) : (
          <PreviewBlocker
            response={response}
            onGoToRequest={onGoToRequest}
          />
        )}
        {showMap ? (
          <SharedMapRenderer
            mode="preview_locked"
            mapState={response.composer_map_state}
            response={response}
            packetId={previewPacketId}
            showLayerPanel={false}
          />
        ) : null}
      </div>

      <aside className="composer-preview-sidebar">
        <PreviewDetailsPanel
          loading={loading}
          onGoToAdjust={onGoToAdjust}
          onGoToExport={onGoToExport}
          onRegenerate={onRegenerate}
          onRouteRefine={onRouteRefine}
          previewReady={previewReady}
          response={response}
          routeRefineLoading={routeRefineLoading}
          statusLabel={statusLabel}
          statusTone={statusTone}
        />
      </aside>
    </section>
  );
}
