import { StatusChip } from "@/components/status-chip";
import { isRoadRouteMode } from "@/lib/map-symbols";
import type { ProximityResult } from "@/types/automap";

type ProximityMapPanelProps = {
  result: ProximityResult | null;
};

export function ProximityMapPanel({ result }: ProximityMapPanelProps) {
  const roadRoute = isRoadRouteMode(result?.route_mode);
  const routeLabel = result?.route_label || (roadRoute ? "Road-following draft route" : "Straight-line fallback");
  return (
    <section className="panel map-preview-shell">
      <div className="panel-title-row">
        <div>
          <h3>Map preview layers</h3>
          <p className="muted">Origin, target, and route layer metadata for local preview/review.</p>
        </div>
        <StatusChip tone="warning">No publish</StatusChip>
      </div>
      {result ? (
        <div className="mini-list">
          <div className="layer-row">
            <strong>Origin</strong>
            <span>{result.origin_type || "parcel/address"}</span>
          </div>
          <div className="layer-row">
            <strong>Target</strong>
            <span>{result.target_name || result.target_type || "needs review"}</span>
          </div>
          <div className="layer-row">
            <strong>{routeLabel}</strong>
            <span>{result.line_geojson_path || "No line output yet"}</span>
          </div>
          {!roadRoute ? (
            <p className="muted">Straight-line fallback only. Road route unavailable unless a bounded road-following draft succeeds.</p>
          ) : null}
        </div>
      ) : (
        <p className="muted">No proximity result selected yet.</p>
      )}
    </section>
  );
}
