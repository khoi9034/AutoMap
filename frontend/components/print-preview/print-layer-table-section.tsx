import type { ComposerMapState, ComposerResponse, DerivedOverlay, PreviewLayer } from "@/types/automap";

type PrintLayerTableSectionProps = {
  mapState?: ComposerMapState | null;
  response?: ComposerResponse | null;
};

type LayerRow = {
  name: string;
  source: string;
  status: string;
  role: string;
  visibility: string;
};

function contextLayers(mapState?: ComposerMapState | null, response?: ComposerResponse | null): PreviewLayer[] {
  const preview = mapState?.preview_config || response?.preview_config || {};
  return preview.context_layers || preview.operational_layers || [];
}

function layerRows(mapState?: ComposerMapState | null, response?: ComposerResponse | null): LayerRow[] {
  const hiddenKeys = new Set((mapState?.hidden_layers || []).map((layer) => String(layer.layer_key || layer.id || "")));
  const derivedRows = (mapState?.derived_overlays || response?.preview_config?.derived_overlays || []).map((layer: DerivedOverlay) => ({
    name: layer.title || layer.id || "Local derived output",
    source: layer.path || layer.url || "Local derived output",
    status: "derived local",
    role: layer.role || layer.geometry_role || "derived",
    visibility: layer.visible === false || layer.default_visible === false ? "Hidden" : "Visible",
  }));
  const contextRows = contextLayers(mapState, response).map((layer) => {
    const key = String(layer.layer_key || layer.id || "");
    return {
      name: layer.title || layer.layer_key || "Context layer",
      source: layer.layer_url || layer.url || layer.service_url || "Layer catalog",
      status: layer.source_status || "reference",
      role: layer.role || layer.display_role || "context",
      visibility: layer.visibility === false || layer.default_visible === false || hiddenKeys.has(key) ? "Hidden" : "Visible",
    };
  });
  return [...derivedRows, ...contextRows];
}

export function PrintLayerTableSection({ mapState, response }: PrintLayerTableSectionProps) {
  const rows = layerRows(mapState, response);
  return (
    <section className="print-preview-sheet print-preview-section print-preview-appendix">
      <h2>Layer Source Table</h2>
      <table className="print-preview-table">
        <thead>
          <tr>
            <th>Display name</th>
            <th>Source</th>
            <th>Status</th>
            <th>Role</th>
            <th>Visibility</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={`${row.name}-${row.source}`}>
              <td>{row.name}</td>
              <td>{row.source}</td>
              <td>{row.status}</td>
              <td>{row.role}</td>
              <td>{row.visibility}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
