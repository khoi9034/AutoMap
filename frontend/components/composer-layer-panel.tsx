"use client";

import { StatusChip } from "@/components/status-chip";
import type { DerivedOverlay, PreviewLayer } from "@/types/automap";

function layerUrl(layer: PreviewLayer): string {
  if (layer.layer_url || layer.url) return layer.layer_url || layer.url || "";
  if (layer.service_url && typeof layer.layer_id === "number") return `${layer.service_url.replace(/\/$/, "")}/${layer.layer_id}`;
  return layer.service_url || "";
}

export function ComposerLayerPanel({
  derivedOverlays = [],
  contextLayers = [],
}: {
  derivedOverlays?: DerivedOverlay[];
  contextLayers?: PreviewLayer[];
}) {
  return (
    <section className="panel composer-derived-layer-panel">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Preview layers</p>
          <h3>Result overlays and context</h3>
        </div>
        <StatusChip tone="success">Local preview only</StatusChip>
      </div>

      <div className="composer-layer-groups">
        <div>
          <h4>Derived result overlays</h4>
          <p className="muted">Origin Address, nearest facility, route draft or straight-line reference, and Selected Parcel only when the parcel is truly resolved.</p>
          {derivedOverlays.length ? (
            <div className="composer-mini-layer-list">
              {derivedOverlays.map((overlay) => {
                const routeLabel = overlay.route_label || overlay.role || "derived overlay";
                return (
                  <article className="composer-mini-layer" key={overlay.id || overlay.title}>
                    <div>
                      <strong>{overlay.title || overlay.id}</strong>
                      <span>{routeLabel}</span>
                    </div>
                    <StatusChip tone="warning">Local derived output</StatusChip>
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="muted">No local derived overlays were returned for this draft.</p>
          )}
        </div>

        <div>
          <h4>Context layers</h4>
          {contextLayers.length ? (
            <div className="composer-mini-layer-list">
              {contextLayers.slice(0, 8).map((layer) => {
                const url = layerUrl(layer);
                const visible = layer.default_visible ?? layer.visibility ?? true;
                return (
                  <article className="composer-mini-layer" key={layer.id || layer.layer_key || layer.title}>
                    <div>
                      <strong>{layer.title || layer.layer_key}</strong>
                      <span>{visible ? layer.role || layer.preview_type || "reference context" : "hidden by default"}</span>
                    </div>
                    {!visible ? (
                      <StatusChip tone="warning">Hidden context</StatusChip>
                    ) : url ? (
                      <a className="text-link" href={url} target="_blank" rel="noreferrer">
                        REST context
                      </a>
                    ) : (
                      <span className="muted">No REST URL</span>
                    )}
                  </article>
                );
              })}
            </div>
          ) : (
            <p className="muted">No REST context layers were returned for this preview.</p>
          )}
        </div>
      </div>
    </section>
  );
}
