import { StatusChip } from "@/components/status-chip";
import type { ProximityResult } from "@/types/automap";

type ProximityResultCardProps = {
  result: ProximityResult | null;
};

export function ProximityResultCard({ result }: ProximityResultCardProps) {
  if (!result) {
    return (
      <section className="panel empty-state">
        <h3>Proximity result</h3>
        <p>Run a nearest-facility or route-draft request to see matched origin, nearest target, distance, warnings, and local output links.</p>
      </section>
    );
  }

  const distance =
    result.distance_value === null || result.distance_value === undefined
      ? "Not available"
      : `${result.distance_value} ${result.distance_unit || "miles"}`;

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Proximity result</h3>
          <p className="muted">{result.target_type || "proximity"} from {result.origin_input || "origin"}</p>
        </div>
        <StatusChip tone={result.status === "ok" ? "success" : "warning"}>{result.status || "needs_review"}</StatusChip>
      </div>
      <div className="detail-grid">
        <div>
          <span className="field-label">Nearest/selected target</span>
          <strong>{result.target_name || result.target_type || "Needs review"}</strong>
        </div>
        <div>
          <span className="field-label">Distance</span>
          <strong>{distance}</strong>
        </div>
        <div>
          <span className="field-label">Line type</span>
          <strong>{result.line_type || "straight-line"}</strong>
        </div>
        <div>
          <span className="field-label">Route status</span>
          <strong>{result.route_status || "straight_line_supported"}</strong>
        </div>
      </div>
      {result.line_geojson_path ? (
        <p className="muted">
          Local line output: <code>{result.line_geojson_path}</code>
        </p>
      ) : null}
      {result.output_folder ? (
        <p className="muted">
          Report folder: <code>{result.output_folder}</code>
        </p>
      ) : null}
      {result.warnings?.length ? (
        <ul className="warning-list">
          {result.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
