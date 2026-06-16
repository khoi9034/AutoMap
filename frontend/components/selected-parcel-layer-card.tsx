import { StatusChip } from "@/components/status-chip";
import type { ParcelSet, SelectedParcelGeometryResult } from "@/types/automap";

type SelectedParcelLayerCardProps = {
  parcelSet?: ParcelSet | null;
  geometryResult?: SelectedParcelGeometryResult | null;
  loading?: boolean;
  onFetch: () => void;
};

export function SelectedParcelLayerCard({ parcelSet, geometryResult, loading, onFetch }: SelectedParcelLayerCardProps) {
  const outputPath = geometryResult?.geometry_output_path || parcelSet?.geometry_output_path;
  const matchedCount = parcelSet?.matched_count ?? parcelSet?.matched_parcels?.length ?? 0;
  const canFetch = Boolean(parcelSet?.parcel_set_id && matchedCount > 0);
  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Selected parcel layer</h3>
          <p className="muted">Fetches local GeoJSON only after the matched parcel count is safely bounded.</p>
        </div>
        <StatusChip tone={outputPath ? "success" : canFetch ? "warning" : "default"}>
          {outputPath ? "GeoJSON ready" : canFetch ? "ready to fetch" : "waiting"}
        </StatusChip>
      </div>
      <div className="stat-grid">
        <div>
          <span>Matched</span>
          <strong>{matchedCount}</strong>
        </div>
        <div>
          <span>Geometry</span>
          <strong>{outputPath ? "local output" : "not fetched"}</strong>
        </div>
      </div>
      {outputPath ? (
        <p className="muted">
          Derived local selected parcel output: <code>{outputPath}</code>
        </p>
      ) : null}
      {geometryResult?.warnings?.length ? (
        <ul className="warning-list">
          {geometryResult.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
      <button className="button button-secondary" type="button" onClick={onFetch} disabled={!canFetch || loading}>
        {loading ? "Fetching..." : "Fetch Selected Parcel Geometry"}
      </button>
    </section>
  );
}
