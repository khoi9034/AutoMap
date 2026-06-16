import { StatusChip } from "@/components/status-chip";
import type { ScenarioFactor } from "@/types/automap";

type ScenarioFactorTableProps = {
  factors?: ScenarioFactor[];
};

function toneForFactor(type?: string): "default" | "success" | "warning" | "danger" {
  if (type === "opportunity") {
    return "success";
  }
  if (type === "constraint") {
    return "danger";
  }
  if (type === "proxy") {
    return "warning";
  }
  return "default";
}

export function ScenarioFactorTable({ factors = [] }: ScenarioFactorTableProps) {
  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Scoring framework</h3>
          <p className="muted">Transparent draft weights for review. These are not official suitability decisions.</p>
        </div>
        <StatusChip>{factors.length} factors</StatusChip>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Factor</th>
              <th>Type</th>
              <th>Weight</th>
              <th>Direction</th>
              <th>Method</th>
              <th>Layers</th>
              <th>Review</th>
            </tr>
          </thead>
          <tbody>
            {factors.map((factor) => (
              <tr key={factor.factor_key || factor.factor_label}>
                <td>
                  <strong>{factor.factor_label || factor.factor_key}</strong>
                  {factor.notes ? <p className="path-text">{factor.notes}</p> : null}
                </td>
                <td>
                  <StatusChip tone={toneForFactor(factor.factor_type)}>{factor.factor_type || "context"}</StatusChip>
                </td>
                <td>{factor.suggested_weight ?? 0}</td>
                <td>{factor.direction}</td>
                <td>{factor.scoring_method}</td>
                <td>{(factor.layer_keys || []).join(", ") || "n/a"}</td>
                <td>{factor.needs_review ? "Yes" : "No"}</td>
              </tr>
            ))}
            {!factors.length ? (
              <tr>
                <td colSpan={7}>Generate a scenario to see the scoring framework.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
