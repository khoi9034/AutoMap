import { StatusChip } from "@/components/status-chip";
import type { PreviewLayer } from "@/types/automap";

type LayerPanelProps = {
  layers?: PreviewLayer[];
};

function percent(value: number | undefined): string {
  if (typeof value !== "number") {
    return "Not set";
  }
  return `${Math.round(value * 100)}%`;
}

function sourceTone(sourceStatus: string | undefined): "default" | "success" | "warning" {
  const status = (sourceStatus || "").toLowerCase();
  if (status.includes("active")) {
    return "success";
  }
  if (status.includes("legacy") || status.includes("historical")) {
    return "warning";
  }
  return "default";
}

function layerUrl(layer: PreviewLayer): string {
  if (layer.layer_url || layer.url) {
    return layer.layer_url || layer.url || "";
  }
  if (layer.service_url && typeof layer.layer_id === "number") {
    return `${layer.service_url.replace(/\/$/, "")}/${layer.layer_id}`;
  }
  return layer.service_url || "";
}

export function LayerPanel({ layers = [] }: LayerPanelProps) {
  if (!layers.length) {
    return (
      <section className="panel empty-state">
        <h3>Layer panel</h3>
        <p>No operational layers are available for this preview config yet.</p>
      </section>
    );
  }

  return (
    <section className="panel layer-panel">
      <div className="panel-title-row">
        <div>
          <h3>Operational layers</h3>
          <p className="muted">{layers.length} draft layer{layers.length === 1 ? "" : "s"} from the review packet.</p>
        </div>
        <StatusChip tone="success">No publishing</StatusChip>
      </div>
      <div className="layer-list">
        {layers.map((layer, index) => {
          const url = layerUrl(layer);
          const warnings = layer.review_warnings || [];
          return (
            <article className="layer-card" key={layer.id || layer.layer_key || layer.title || index}>
              <div className="layer-card-header">
                <div>
                  <p className="eyebrow">Layer {index + 1}</p>
                  <h4>{layer.title || layer.layer_key || "Untitled layer"}</h4>
                </div>
                <StatusChip tone={sourceTone(layer.source_status)}>
                  {layer.source_status || "source unknown"}
                </StatusChip>
                {layer.derived_local_analysis ? (
                  <StatusChip tone="warning">Derived Local Analysis Result</StatusChip>
                ) : null}
              </div>
              <dl className="layer-meta">
                <div>
                  <dt>Role</dt>
                  <dd>{layer.role || "reference_layer"}</dd>
                </div>
                <div>
                  <dt>Visibility</dt>
                  <dd>{layer.visibility === false ? "Hidden" : "Visible"}</dd>
                </div>
                <div>
                  <dt>Opacity</dt>
                  <dd>{percent(layer.opacity)}</dd>
                </div>
                <div>
                  <dt>Confidence</dt>
                  <dd>{percent(layer.confidence_score)}</dd>
                </div>
              </dl>
              {layer.definition_expression ? (
                <div className="definition-box">
                  <strong>Definition expression</strong>
                  <code>{layer.definition_expression}</code>
                </div>
              ) : (
                <p className="muted">No definition expression override recorded.</p>
              )}
              <div className="layer-card-footer">
                {warnings.length ? (
                  <StatusChip tone="warning">{warnings.length} warning{warnings.length === 1 ? "" : "s"}</StatusChip>
                ) : (
                  <StatusChip tone="success">No layer warnings</StatusChip>
                )}
                {url ? (
                  <a className="text-link" href={url} target="_blank" rel="noreferrer">
                    Open REST layer
                  </a>
                ) : (
                  <span className="muted">No layer URL available</span>
                )}
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
