"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { ComposerMapPreview } from "@/components/composer-map-preview";
import { samplePrompts } from "@/components/navigation";
import { SimpleMapComposerStepper } from "@/components/simple-map-composer-stepper";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { API_BASE_URL, adjustComposerDraft, exportComposerDraft, generateComposerDraft } from "@/lib/api";
import { mergeWorkflowState, packetIdFromPath } from "@/lib/workflow-store";
import type { ComposerResponse, PreviewLayer, ProximityResult } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

type ComposerLayerEdit = {
  layer_key: string;
  title: string;
  visibility: boolean;
  opacity: number;
  role?: string;
  definition_expression?: string;
  is_derived?: boolean;
};

const defaultPrompt = "make a map of my address 793 bartram ave and include nearest line to the nearest fire station";

function localFileUrl(path?: string | null): string {
  return path ? `${API_BASE_URL}/local-file?path=${encodeURIComponent(path)}` : "#";
}

function actionLabel(action?: string): string {
  if (action === "correct_address") return "Correct address";
  if (action === "correct_parcel_identifier") return "Correct parcel/PIN/address";
  if (action === "preview_map") return "Preview Map";
  if (action === "preview_adjusted_map") return "Preview Adjusted Map";
  if (action === "print_or_export") return "Print / Export";
  return "Review Draft";
}

function isAddressFocused(response: ComposerResponse): boolean {
  const blockerText = (response.preview_blockers || []).join(" ").toLowerCase();
  return (
    response.origin_type === "address" ||
    response.request_type === "address_context" ||
    blockerText.includes("address not matched") ||
    response.recipe?.origin_context?.origin_type === "address" ||
    response.parcel_context?.origin_type === "address" ||
    response.parcel_context?.input_type === "address"
  );
}

function identifierText(value: unknown): string {
  if (!value || typeof value !== "object") return String(value || "");
  const item = value as { value?: string; normalized_value?: string; identifier_type?: string };
  return item.value || item.normalized_value || item.identifier_type || JSON.stringify(item);
}

function layerEditsFromResponse(response: ComposerResponse): ComposerLayerEdit[] {
  const previewLayers = response.preview_config?.operational_layers || [];
  const derivedOverlays = response.preview_config?.derived_overlays || response.proximity_result?.derived_overlays || [];
  const derivedEdits: ComposerLayerEdit[] = derivedOverlays.map((overlay, index) => ({
    layer_key: overlay.id || `derived_overlay_${index}`,
    title: overlay.title || overlay.id || `Derived overlay ${index + 1}`,
    visibility: overlay.visible !== false,
    opacity: 1,
    role: overlay.role,
    definition_expression: "",
    is_derived: true,
  }));
  if (previewLayers.length) {
    const contextEdits = previewLayers
      .filter((layer: PreviewLayer) => !layer.derived_local_analysis && !layer.local_output)
      .map((layer: PreviewLayer, index) => ({
      layer_key: layer.layer_key || layer.id || `layer_${index}`,
      title: layer.title || layer.layer_key || `Layer ${index + 1}`,
      visibility: layer.visibility !== false,
      opacity: typeof layer.opacity === "number" ? layer.opacity : 1,
      role: layer.role,
      definition_expression: layer.definition_expression || "",
    }));
    return [...derivedEdits, ...contextEdits];
  }
  return [
    ...derivedEdits,
    ...(response.selected_layers || []).map((layer, index) => ({
    layer_key: layer.layer_key || `layer_${index}`,
    title: layer.layer_name || layer.layer_key || `Layer ${index + 1}`,
    visibility: true,
    opacity: layer.category === "flood" ? 0.35 : layer.category === "zoning" ? 0.65 : 0.85,
    role: layer.role,
    definition_expression: "",
    })),
  ];
}

function packetIdForPreview(response: ComposerResponse | null): string {
  if (!response?.can_preview) return "";
  return response.adjusted_packet_id || response.packet_id || response.review_packet_id || packetIdFromPath(response.packet_path || "");
}

function ComposerSteps({ response, exported }: { response: ComposerResponse | null; exported: boolean }) {
  const previewReady = Boolean(response?.can_preview);
  const adjusted = Boolean(response?.adjusted_packet_id || response?.applied_adjustments);
  const blocked = Boolean(response?.preview_blockers?.length);

  return (
    <section className="panel composer-status-panel">
      <SimpleMapComposerStepper
        statuses={{
          request: response ? "complete" : "active",
          preview: blocked ? "blocked" : previewReady ? "complete" : "pending",
          adjust: adjusted ? "complete" : previewReady ? "active" : "pending",
          export: exported ? "complete" : previewReady ? "active" : "pending",
        }}
        notes={{
          request: response?.map_title || "Describe the map you need.",
          preview: response?.preview_blockers?.[0] || "Only appears when the map can focus correctly.",
          adjust: previewReady ? "Use the controls on this page." : "Preview must be ready first.",
          export: "Local draft files only.",
        }}
      />
    </section>
  );
}

function PreviewBlocker({ response }: { response: ComposerResponse }) {
  const context = response.parcel_context;
  const isAddress = isAddressFocused(response);
  const blockerText = response.preview_blockers?.[0] || context?.reason_if_not_focusable || "";
  if (!response.preview_blockers?.length && context?.can_focus_map !== false && response.recipe?.origin_context?.can_preview !== false) return null;
  const candidates = [
    ...(response.origin_candidates || []),
    ...(context?.candidate_matches || []),
  ];
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
      <p className="muted">Try corrected address/PIN in the request box, then generate the draft again.</p>
    </section>
  );
}

function ProximityResultSummary({ result }: { result?: ProximityResult | null }) {
  if (!result) return null;
  const targetKind = result.target_type === "nearest_fire_ems_station" || result.target_classification === "mixed_fire_ems"
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
          <h3>{targetKind.charAt(0).toUpperCase() + targetKind.slice(1)} found: {targetLabel}</h3>
          <p className="muted">{routeLabel}. {routeWarning}</p>
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
      {result.line_geojson_path ? <p className="muted">Line output: {result.line_geojson_path}</p> : null}
    </section>
  );
}

function SelectedLayersAndWarnings({ response }: { response: ComposerResponse }) {
  return (
    <section className="panel composer-layer-summary">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Draft contents</p>
          <h3>Layers and review notes</h3>
        </div>
      </div>
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

function LayerAdjustmentControls({
  layers,
  setLayers,
}: {
  layers: ComposerLayerEdit[];
  setLayers: (layers: ComposerLayerEdit[]) => void;
}) {
  function updateLayer(index: number, patch: Partial<ComposerLayerEdit>) {
    setLayers(layers.map((layer, layerIndex) => (layerIndex === index ? { ...layer, ...patch } : layer)));
  }

  function moveLayer(index: number, direction: -1 | 1) {
    const targetIndex = index + direction;
    if (targetIndex < 0 || targetIndex >= layers.length) return;
    const next = [...layers];
    const [item] = next.splice(index, 1);
    next.splice(targetIndex, 0, item);
    setLayers(next);
  }

  return (
    <div className="composer-layer-editor">
      {layers.map((layer, index) => (
        <article className="composer-layer-row" key={`${layer.layer_key}-${index}`}>
          <div className="composer-layer-main">
            <label>
              <span>Layer title</span>
              <input value={layer.title} onChange={(event) => updateLayer(index, { title: event.target.value })} />
            </label>
            <label>
              <span>{layer.is_derived ? "Derived output" : "Definition expression"}</span>
              {layer.is_derived ? (
                <input value="Local derived GeoJSON overlay" disabled />
              ) : (
                <input
                  value={layer.definition_expression || ""}
                  onChange={(event) => updateLayer(index, { definition_expression: event.target.value })}
                  placeholder="Optional SQL where clause"
                />
              )}
            </label>
          </div>
          <div className="composer-layer-actions">
            <label className="toggle-line">
              <input
                checked={layer.visibility}
                type="checkbox"
                onChange={(event) => updateLayer(index, { visibility: event.target.checked })}
              />
              Visible
            </label>
            <label>
              <span>Opacity {Math.round(layer.opacity * 100)}%</span>
              <input
                min="0"
                max="1"
                step="0.05"
                type="range"
                value={layer.opacity}
                onChange={(event) => updateLayer(index, { opacity: Number(event.target.value) })}
              />
            </label>
            <div className="button-row compact-buttons">
              <button className="icon-button" type="button" onClick={() => moveLayer(index, -1)} aria-label={`Move ${layer.title} up`}>
                Up
              </button>
              <button className="icon-button" type="button" onClick={() => moveLayer(index, 1)} aria-label={`Move ${layer.title} down`}>
                Down
              </button>
              <button className="button button-secondary" type="button" onClick={() => updateLayer(index, { visibility: false })}>
                Remove
              </button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

export function MapComposerClient() {
  const searchParams = useSearchParams();
  const [prompt, setPrompt] = useState(searchParams.get("prompt") || defaultPrompt);
  const [response, setResponse] = useState<ComposerResponse | null>(null);
  const [layers, setLayers] = useState<ComposerLayerEdit[]>([]);
  const [mapTitle, setMapTitle] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState<"generate" | "adjust" | "export" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  const previewPacketId = useMemo(() => packetIdForPreview(response), [response]);
  const canAdjust = Boolean(response?.composer_session_id && response.can_preview && layers.length);
  const canExport = Boolean(response?.composer_session_id && response.can_report);

  async function generateDraft() {
    setLoading("generate");
    setError(null);
    try {
      const result = await generateComposerDraft(prompt);
      setResponse(result);
      setLayers(layerEditsFromResponse(result));
      setMapTitle(result.map_title || result.recipe?.map_title || "");
      mergeWorkflowState({
        rawPrompt: prompt,
        recipe: result.recipe,
        reviewPacket: result.packet_path ? { packet_path: result.packet_path, packet_id: result.packet_id } : undefined,
        selectedPacketPath: result.packet_path || undefined,
        selectedPacketId: result.packet_id || undefined,
        warnings: result.warnings || [],
        missingData: result.missing_data || [],
        activeStep: result.can_preview ? "preview" : "recipe",
      });
      setToast({
        tone: result.can_preview ? "success" : "warning",
        message: result.can_preview ? "Draft map and preview are ready." : "Draft created, but preview is blocked until the address or parcel matches.",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Composer draft generation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function applyAdjustments() {
    if (!response?.composer_session_id) return;
    setLoading("adjust");
    setError(null);
    try {
      const result = await adjustComposerDraft({
        composer_session_id: response.composer_session_id,
        map_title: mapTitle,
        notes,
        layer_order: layers.map((layer) => layer.layer_key),
        layers,
      });
      setResponse(result);
      setLayers(layerEditsFromResponse(result));
      mergeWorkflowState({
        rawPrompt: prompt,
        recipe: result.recipe,
        adjustedPacket: result.adjusted_packet_path ? { adjusted_packet_path: result.adjusted_packet_path } : undefined,
        selectedAdjustedPacketPath: result.adjusted_packet_path || undefined,
        selectedAdjustedPacketId: result.adjusted_packet_id || undefined,
        activeStep: "adjustments",
      });
      setToast({ tone: "success", message: "Adjustments applied and adjusted preview is ready." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Adjustment failed.");
    } finally {
      setLoading(null);
    }
  }

  async function exportDraft() {
    if (!response?.composer_session_id) return;
    setLoading("export");
    setError(null);
    try {
      const result = await exportComposerDraft(response.composer_session_id);
      setResponse(result);
      setToast({ tone: "success", message: "Draft report and export files are ready." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Export failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="map-composer-grid">
      <section className="panel composer-prompt-panel">
        <textarea
          className="textarea composer-textarea"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Describe the draft map..."
        />
        <div className="sample-grid">
          {samplePrompts.slice(0, 7).map((sample) => (
            <button className="sample-button" key={sample} type="button" onClick={() => setPrompt(sample)}>
              {sample}
            </button>
          ))}
        </div>
        <button className="button" type="button" onClick={generateDraft} disabled={loading !== null || !prompt.trim()}>
          {loading === "generate" ? "Generating Draft Map..." : "Generate Draft Map"}
        </button>
        {loading ? <p className="muted">AutoMap is checking catalog layers, parcel match status, and preview readiness...</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast} />
      </section>

      <main className="composer-main">
        <ComposerSteps response={response} exported={Boolean(response?.export)} />

        {!response ? (
          <section className="panel empty-state">
            <h3>One simple map workflow</h3>
            <p>Request to Preview to Adjust to Print / Export.</p>
            <p className="muted">Analysis is optional unless the request asks to calculate, select, count, summarize, or measure.</p>
          </section>
        ) : null}

        {response ? (
          <>
            <section className="panel">
              <div className="panel-title-row">
                <div>
                  <p className="eyebrow">Draft map</p>
                  <h3>{response.map_title || "AutoMap Draft Map"}</h3>
                  <p className="muted">{response.raw_prompt}</p>
                </div>
                <div className="chip-row">
                  <StatusChip tone={response.can_preview ? "success" : "danger"}>
                    {response.can_preview ? "Preview ready" : "Preview blocked"}
                  </StatusChip>
                  <StatusChip tone={response.can_analyze ? "warning" : "success"}>
                    {response.can_analyze ? "Analysis available" : "Analysis not forced"}
                  </StatusChip>
                </div>
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
            </section>

            <PreviewBlocker response={response} />
            <ProximityResultSummary result={response.proximity_result} />

            {previewPacketId ? (
              <section className="composer-preview-section">
                <ComposerMapPreview response={response} packetId={previewPacketId} />
              </section>
            ) : null}

            <SelectedLayersAndWarnings response={response} />

            {response.can_preview ? (
              <section className="panel">
                <div className="panel-title-row">
                  <div>
                    <p className="eyebrow">Adjust Map</p>
                    <h3>Simple draft controls</h3>
                    <p className="muted">Normal edits happen here; advanced file-based adjustments remain available for GIS analysts.</p>
                  </div>
                  <StatusChip tone={canAdjust ? "success" : "default"}>{canAdjust ? "Ready" : "Waiting for preview"}</StatusChip>
                </div>
                <label className="field-stack">
                  <span>Map title</span>
                  <input value={mapTitle} onChange={(event) => setMapTitle(event.target.value)} />
                </label>
                <LayerAdjustmentControls layers={layers} setLayers={setLayers} />
                <label className="field-stack">
                  <span>Reviewer notes</span>
                  <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional draft review notes" />
                </label>
                <button className="button" type="button" onClick={applyAdjustments} disabled={loading !== null || !canAdjust}>
                  {loading === "adjust" ? "Applying..." : "Apply Adjustments"}
                </button>
              </section>
            ) : null}

            {response.can_preview ? (
              <section className="panel">
                <div className="panel-title-row">
                  <div>
                    <p className="eyebrow">Print / Export</p>
                    <h3>Local draft outputs</h3>
                    <p className="muted">Draft report/export, not an official print map. Nothing is published.</p>
                  </div>
                  <StatusChip tone={canExport ? "success" : "default"}>{canExport ? "Export available" : "Preview required"}</StatusChip>
                </div>
                <div className="button-row">
                  <button className="button" type="button" onClick={exportDraft} disabled={loading !== null || !canExport}>
                    {loading === "export" ? "Exporting..." : "Generate Review Report"}
                  </button>
                  <a className="button button-secondary" href={localFileUrl(response.webmap_path)} target="_blank" rel="noreferrer">
                    Export WebMap JSON
                  </a>
                  {response.composer_session_id ? (
                    <Link className="button button-secondary" href={`/map-composer/${response.composer_session_id}/print`}>
                      Print Draft Map
                    </Link>
                  ) : null}
                </div>
                {response.export?.files?.length ? (
                  <div className="export-link-grid">
                    {response.export.files.map((file) => (
                      <a className="export-link" key={`${file.name}-${file.path}`} href={file.url ? `${API_BASE_URL}${file.url}` : localFileUrl(file.path)} target="_blank" rel="noreferrer">
                        <strong>{file.name}</strong>
                        <span>{file.path}</span>
                      </a>
                    ))}
                  </div>
                ) : null}
              </section>
            ) : null}
          </>
        ) : null}
      </main>
    </div>
  );
}
