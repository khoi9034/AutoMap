import type { DerivedOverlay, PreviewLayer } from "@/types/automap";

type ExhibitLayerTableProps = {
  contextLayers: PreviewLayer[];
  derivedLayers: DerivedOverlay[];
};

function sourceRole(layer: PreviewLayer | DerivedOverlay, derived = false): string {
  if (derived) return "derived local";
  const status = String((layer as PreviewLayer).source_status || "").toLowerCase();
  const role = String((layer as PreviewLayer).role || "").toLowerCase();
  if (status.includes("proxy") || role.includes("proxy")) return "proxy";
  if (status.includes("reference") || role.includes("reference")) return "reference";
  if (status === "active" || status === "approved" || status === "verified") return "official";
  return "reference";
}

function sourceNote(layer: PreviewLayer | DerivedOverlay, derived = false): string {
  if (derived) return (layer as DerivedOverlay).path || (layer as DerivedOverlay).url || "Local derived output";
  const context = layer as PreviewLayer;
  return context.layer_url || context.url || context.service_url || "Layer catalog record";
}

function limitations(layer: PreviewLayer | DerivedOverlay, derived = false): string {
  if (derived) {
    const overlay = layer as DerivedOverlay;
    return overlay.route_warning || "Local derived output; not uploaded or published.";
  }
  const context = layer as PreviewLayer;
  if (context.review_warnings?.length) return context.review_warnings.join("; ");
  if (context.definition_expression) return `Filtered with definition expression: ${context.definition_expression}`;
  return "Review source currency and symbology before official use.";
}

export function ExhibitLayerTable({ contextLayers, derivedLayers }: ExhibitLayerTableProps) {
  const rows = [
    ...derivedLayers.map((layer) => ({ layer, derived: true })),
    ...contextLayers.map((layer) => ({ layer, derived: false })),
  ];

  return (
    <section className="exhibit-layer-table">
      <h2>Layer source table</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Display name</th>
              <th>Source layer</th>
              <th>Status</th>
              <th>Role</th>
              <th>REST URL or local output note</th>
              <th>Limitations</th>
            </tr>
          </thead>
          <tbody>
            {rows.length ? (
              rows.map(({ layer, derived }, index) => (
                <tr key={`${layer.id || layer.title || index}-${derived ? "derived" : "context"}`}>
                  <td>{layer.title || layer.id || "Map layer"}</td>
                  <td>{derived ? layer.role || "Derived local output" : (layer as PreviewLayer).layer_key || layer.title}</td>
                  <td>{derived ? "derived local" : (layer as PreviewLayer).source_status || "reference"}</td>
                  <td>{sourceRole(layer, derived)}</td>
                  <td>{sourceNote(layer, derived)}</td>
                  <td>{limitations(layer, derived)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={6}>No layer sources recorded.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
