import { StatusChip } from "@/components/status-chip";
import type { ProximityResult } from "@/types/automap";

type ProximityMapPanelProps = {
  result: ProximityResult | null;
};

export function ProximityMapPanel({ result }: ProximityMapPanelProps) {
  return (
    <section className="panel map-preview-shell">
      <div className="panel-title-row">
        <div>
          <h3>Map preview layers</h3>
          <p className="muted">Origin, target, and straight-line layer metadata for local preview/review.</p>
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
            <strong>{result.route_label || (result.route_mode === "road_following_draft" ? "Road-following draft" : "Straight-line reference")}</strong>
            <span>{result.line_geojson_path || "No line output yet"}</span>
          </div>
          {result.route_mode !== "road_following_draft" ? (
            <p className="muted">Not a road route. This is a straight-line reference only unless a bounded road-following draft succeeds.</p>
          ) : null}
        </div>
      ) : (
        <p className="muted">No proximity result selected yet.</p>
      )}
    </section>
  );
}
