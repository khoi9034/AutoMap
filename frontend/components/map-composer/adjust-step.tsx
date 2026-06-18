"use client";

import { ComposerMapPreview } from "@/components/composer-map-preview";
import { StatusChip } from "@/components/status-chip";
import type { ComposerResponse } from "@/types/automap";

import type { ComposerLayerEdit } from "./types";
import { composerDisplaySubtitle, composerDisplayTitle, isRouteLayer } from "./utils";

type AdjustStepProps = {
  layers: ComposerLayerEdit[];
  loading?: boolean;
  mapSubtitle: string;
  mapTitle: string;
  notes: string;
  onApply: () => void;
  onGoToPreview: () => void;
  onReset: () => void;
  previewPacketId: string;
  response: ComposerResponse | null;
  setLayers: (layers: ComposerLayerEdit[]) => void;
  setMapSubtitle: (value: string) => void;
  setMapTitle: (value: string) => void;
  setNotes: (value: string) => void;
};

function updateLayer(layers: ComposerLayerEdit[], setLayers: (layers: ComposerLayerEdit[]) => void, index: number, patch: Partial<ComposerLayerEdit>) {
  setLayers(layers.map((layer, layerIndex) => (layerIndex === index ? { ...layer, ...patch } : layer)));
}

function moveLayer(layers: ComposerLayerEdit[], setLayers: (layers: ComposerLayerEdit[]) => void, index: number, direction: -1 | 1) {
  const targetIndex = index + direction;
  if (targetIndex < 0 || targetIndex >= layers.length) return;
  const next = [...layers];
  const [item] = next.splice(index, 1);
  next.splice(targetIndex, 0, item);
  setLayers(next);
}

function LayerAdjustmentControls({ layers, setLayers }: { layers: ComposerLayerEdit[]; setLayers: (layers: ComposerLayerEdit[]) => void }) {
  return (
    <div className="composer-layer-editor composer-adjust-layer-editor">
      {layers.map((layer, index) => (
        <article className="composer-layer-row" key={`${layer.layer_key}-${index}`}>
          <div className="composer-layer-main">
            <label>
              <span>Display name</span>
              <input value={layer.title} onChange={(event) => updateLayer(layers, setLayers, index, { title: event.target.value })} />
            </label>
            <label>
              <span>{layer.is_derived ? "Derived output" : "Definition expression"}</span>
              {layer.is_derived ? (
                <input value="Local derived GeoJSON overlay" disabled />
              ) : (
                <input
                  value={layer.definition_expression || ""}
                  onChange={(event) => updateLayer(layers, setLayers, index, { definition_expression: event.target.value })}
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
                onChange={(event) => updateLayer(layers, setLayers, index, { visibility: event.target.checked })}
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
                onChange={(event) => updateLayer(layers, setLayers, index, { opacity: Number(event.target.value) })}
              />
            </label>
            <div className="button-row compact-buttons">
              <button className="icon-button" type="button" onClick={() => moveLayer(layers, setLayers, index, -1)} aria-label={`Move ${layer.title} up`}>
                Up
              </button>
              <button className="icon-button" type="button" onClick={() => moveLayer(layers, setLayers, index, 1)} aria-label={`Move ${layer.title} down`}>
                Down
              </button>
              <button className="button button-secondary" type="button" onClick={() => updateLayer(layers, setLayers, index, { visibility: false })}>
                Hide
              </button>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

function RouteStyleControls({ layers, setLayers }: { layers: ComposerLayerEdit[]; setLayers: (layers: ComposerLayerEdit[]) => void }) {
  const routeLayers = layers.map((layer, index) => ({ layer, index })).filter(({ layer }) => isRouteLayer(layer));
  if (!routeLayers.length) return null;
  return (
    <section className="composer-route-controls">
      <p className="eyebrow">Route style</p>
      {routeLayers.map(({ layer, index }) => (
        <div className="definition-box" key={`${layer.layer_key}-route-style`}>
          <strong>{layer.title}</strong>
          <label className="toggle-line">
            <input
              checked={layer.visibility}
              type="checkbox"
              onChange={(event) => updateLayer(layers, setLayers, index, { visibility: event.target.checked })}
            />
            Route visible
          </label>
          <label className="field-stack">
            <span>Line thickness {layer.line_thickness || 3.2}px</span>
            <input
              min="1.5"
              max="6"
              step="0.1"
              type="range"
              value={layer.line_thickness || 3.2}
              onChange={(event) => updateLayer(layers, setLayers, index, { line_thickness: Number(event.target.value) })}
            />
          </label>
          <label className="field-stack">
            <span>Line style</span>
            <select
              value={layer.line_style || "solid"}
              onChange={(event) => updateLayer(layers, setLayers, index, { line_style: event.target.value === "dashed" ? "dashed" : "solid" })}
            >
              <option value="solid">Solid</option>
              <option value="dashed">Dashed</option>
            </select>
          </label>
        </div>
      ))}
    </section>
  );
}

function SymbolControls({ layers, setLayers }: { layers: ComposerLayerEdit[]; setLayers: (layers: ComposerLayerEdit[]) => void }) {
  const symbolLayers = layers
    .map((layer, index) => ({ layer, index }))
    .filter(({ layer }) => `${layer.layer_key} ${layer.title} ${layer.role || ""}`.toLowerCase().includes("origin") || `${layer.layer_key} ${layer.title} ${layer.role || ""}`.toLowerCase().includes("target"));
  if (!symbolLayers.length) return null;
  return (
    <section className="composer-symbol-controls">
      <p className="eyebrow">Symbol overlays</p>
      {symbolLayers.map(({ layer, index }) => (
        <label className="toggle-line" key={`${layer.layer_key}-symbol`}>
          <input
            checked={layer.visibility}
            type="checkbox"
            onChange={(event) => updateLayer(layers, setLayers, index, { visibility: event.target.checked })}
          />
          {layer.title}
        </label>
      ))}
    </section>
  );
}

export function AdjustStep({
  layers,
  loading,
  mapSubtitle,
  mapTitle,
  notes,
  onApply,
  onGoToPreview,
  onReset,
  previewPacketId,
  response,
  setLayers,
  setMapSubtitle,
  setMapTitle,
  setNotes,
}: AdjustStepProps) {
  if (!response?.can_preview || !previewPacketId) {
    return (
      <section className="panel empty-state">
        <h3>Preview required</h3>
        <p>Generate a preview-ready draft before adjusting map layers.</p>
      </section>
    );
  }

  return (
    <section className="composer-adjust-layout">
      <div className="composer-adjust-map-column">
        <ComposerMapPreview response={response} packetId={previewPacketId} showLayerPanel={false} />
      </div>
      <aside className="panel composer-adjust-controls-panel">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Adjust</p>
            <h3>Map controls</h3>
            <p className="muted">Original request: {response.raw_prompt || response.prompt}</p>
          </div>
          <StatusChip tone="success">Live preview</StatusChip>
        </div>

        <label className="field-stack">
          <span>Map title</span>
          <input value={mapTitle || composerDisplayTitle(response)} onChange={(event) => setMapTitle(event.target.value)} />
        </label>
        <label className="field-stack">
          <span>Subtitle</span>
          <input value={mapSubtitle || composerDisplaySubtitle(response)} onChange={(event) => setMapSubtitle(event.target.value)} />
        </label>
        <RouteStyleControls layers={layers} setLayers={setLayers} />
        <SymbolControls layers={layers} setLayers={setLayers} />
        <LayerAdjustmentControls layers={layers} setLayers={setLayers} />
        <label className="field-stack">
          <span>Reviewer notes</span>
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Optional draft review notes" />
        </label>
        <div className="button-row composer-adjust-action-bar">
          <button className="button" type="button" onClick={onApply} disabled={loading || !layers.length}>
            {loading ? "Applying..." : "Apply Adjustments"}
          </button>
          <button className="button button-secondary" type="button" onClick={onReset} disabled={loading}>
            Reset adjustments
          </button>
          <button className="button button-secondary" type="button" onClick={onGoToPreview}>
            Preview Adjusted Map
          </button>
        </div>
      </aside>
    </section>
  );
}
