import { SourceCoveragePanel } from "@/components/source-coverage-panel";
import { StatusChip } from "@/components/status-chip";
import type { MapRecipe, ParcelSet } from "@/types/automap";

type ParcelContextSummaryProps = {
  parcelSet?: ParcelSet | null;
  recipe?: MapRecipe | null;
};

export function ParcelContextSummary({ parcelSet, recipe }: ParcelContextSummaryProps) {
  const context = recipe?.parcel_context;
  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Parcel context summary</h3>
          <p className="muted">Selected parcel context remains a local review draft.</p>
        </div>
        <StatusChip tone={recipe?.needs_review ? "warning" : recipe ? "success" : "default"}>
          {recipe ? "context recipe" : parcelSet?.match_status || "waiting"}
        </StatusChip>
      </div>
      <div className="stat-grid">
        <div>
          <span>Parcel set</span>
          <strong>{parcelSet?.parcel_set_id || context?.parcel_set_id || "none"}</strong>
        </div>
        <div>
          <span>Matched</span>
          <strong>{context?.matched_count ?? parcelSet?.matched_parcels?.length ?? 0}</strong>
        </div>
        <div>
          <span>Unmatched</span>
          <strong>{context?.unmatched_identifiers?.length ?? parcelSet?.unmatched_identifiers?.length ?? 0}</strong>
        </div>
        <div>
          <span>Layers</span>
          <strong>{recipe?.selected_layers?.length || 0}</strong>
        </div>
      </div>
      {recipe?.selected_layers?.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Layer</th>
                <th>Category</th>
                <th>Source role</th>
              </tr>
            </thead>
            <tbody>
              {recipe.selected_layers.map((layer) => (
                <tr key={layer.layer_key || layer.layer_name}>
                  <td>{layer.display_title || layer.layer_name}</td>
                  <td>{layer.category}</td>
                  <td>{layer.source_role || layer.source_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">Create a parcel context recipe to see selected layers.</p>
      )}
      {recipe?.source_coverage ? <SourceCoveragePanel coverage={recipe.source_coverage} /> : null}
    </section>
  );
}
