"use client";

import { SharedMapRenderer } from "@/components/map-renderer/shared-map-renderer";
import { StatusChip } from "@/components/status-chip";
import type { ComposerResponse, ProximityResult } from "@/types/automap";

import { actionLabel, composerDisplayTitle, identifierText, isAddressFocused } from "./utils";

type PreviewStepProps = {
  loading?: boolean;
  onGoToAdjust: () => void;
  onGoToExport: () => void;
  onGoToRequest: () => void;
  onRegenerate: () => void;
  previewPacketId: string;
  response: ComposerResponse | null;
};

export function PreviewBlocker({ response, onGoToRequest }: { response: ComposerResponse; onGoToRequest: () => void }) {
  const context = response.parcel_context;
  const isAddress = isAddressFocused(response);
  const blockerText = response.preview_blockers?.[0] || context?.reason_if_not_focusable || "";
  if (!response.preview_blockers?.length && context?.can_focus_map !== false && response.recipe?.origin_context?.can_preview !== false) return null;
  const candidates = [...(response.origin_candidates || []), ...(context?.candidate_matches || [])];
  return (
    <section className="panel parcel-preview-blocked" role="alert">
      <p className="eyebrow">{isAddress ? "Address-focused preview blocked" : "Parcel-focused preview blocked"}</p>
      <h3>{isAddress ? "Address not matched" : "Parcel not matched"}</h3>
      <p>
        {blockerText ||
          (isAddress
            ? "Address not matched. AutoMap cannot zoom to or map this address until a valid public address record or related parcel/PIN is matched."
            : "Parcel not matched. AutoMap cannot zoom to or map this parcel until a valid parcel/PIN/address is provided.")}
      </p>
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
            ? "It searched verified public address and parcel/address fields without using owner/name fields."
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
          <p>{candidates.slice(0, 4).map(identifierText).join(", ")}</p>
        </div>
      ) : null}
      <button className="button" type="button" onClick={onGoToRequest}>
        Correct address/PIN
      </button>
    </section>
  );
}

export function ProximityResultSummary({ result }: { result?: ProximityResult | null }) {
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
  const routeLabel = result.route_label || (result.route_mode === "road_following_draft" ? "Road-following draft" : "Straight-line reference");
  const routeWarning = result.route_warning || (result.route_mode === "road_following_draft" ? "Not official driving directions." : "This is not a driving route.");
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
      </div>
      {result.property_match_status === "not_resolved" ? (
        <p className="muted">Address matched, but related parcel was not resolved from verified fields.</p>
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

export function PreviewStep({ loading, onGoToAdjust, onGoToExport, onGoToRequest, onRegenerate, previewPacketId, response }: PreviewStepProps) {
  if (!response) {
    return (
      <section className="panel empty-state">
        <h3>No draft yet</h3>
        <p>Start with the Request step, then AutoMap will open a focused preview here.</p>
      </section>
    );
  }

  const previewReady = Boolean(response.can_preview && previewPacketId);
  return (
    <section className="composer-preview-layout">
      <div className="composer-preview-main">
        <div className="panel composer-compact-request">
          <span className="eyebrow">Original request</span>
          <p>{response.raw_prompt || response.prompt}</p>
        </div>
        <PreviewBlocker response={response} onGoToRequest={onGoToRequest} />
        {previewReady ? (
          <SharedMapRenderer mapState={response.composer_map_state} response={response} packetId={previewPacketId} showLayerPanel={false} />
        ) : null}
      </div>

      <aside className="composer-preview-sidebar">
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <p className="eyebrow">Preview</p>
              <h3>{composerDisplayTitle(response)}</h3>
              {response.map_layout?.subtitle ? <p className="muted">{response.map_layout.subtitle}</p> : null}
            </div>
            <StatusChip tone={previewReady ? "success" : "danger"}>{previewReady ? "Ready" : "Blocked"}</StatusChip>
          </div>
          <div className="result-strip">
            <div>
              <span>Layers</span>
              <strong>{response.selected_layers?.length || 0}</strong>
            </div>
            <div>
              <span>Missing data</span>
              <strong>{response.missing_data?.length || 0}</strong>
            </div>
            <div>
              <span>Next</span>
              <strong>{actionLabel(response.next_action)}</strong>
            </div>
          </div>
          <div className="button-row">
            <button className="button" type="button" onClick={onGoToAdjust} disabled={!previewReady}>
              Continue to Adjust
            </button>
            <button className="button button-secondary" type="button" onClick={onRegenerate} disabled={loading}>
              Regenerate Draft
            </button>
            <button className="button button-secondary" type="button" onClick={onGoToExport} disabled={!previewReady}>
              Print / Export
            </button>
          </div>
        </section>
        <ProximityResultSummary result={response.proximity_result} />
        <SelectedLayersAndWarnings response={response} />
      </aside>
    </section>
  );
}
