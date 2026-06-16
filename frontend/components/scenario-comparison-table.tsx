import type { ScenarioComparison } from "@/types/automap";

type ScenarioComparisonTableProps = {
  comparison?: ScenarioComparison | null;
};

function weightEntries(value: unknown): Array<[string, unknown]> {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return [];
  }
  return Object.entries(value as Record<string, unknown>);
}

export function ScenarioComparisonTable({ comparison }: ScenarioComparisonTableProps) {
  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Scenario comparison</h3>
          <p className="muted">Compare factor weights, layer differences, source coverage, and missing data.</p>
        </div>
      </div>
      {!comparison ? (
        <p className="muted">Select at least two scenarios or variants to compare.</p>
      ) : (
        <>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Factor</th>
                  <th>Weights</th>
                </tr>
              </thead>
              <tbody>
                {(comparison.factor_differences || []).map((row) => (
                  <tr key={String(row.factor_key)}>
                    <td>{String(row.factor_key)}</td>
                    <td>
                      {weightEntries(row.weights).map(([key, value]) => (
                        <span className="chip" key={key}>
                          {key}: {String(value)}
                        </span>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(comparison.recommended_review_focus || []).length ? (
            <div className="notice notice-warning">
              <strong>Recommended review focus</strong>
              <ul className="plain-list">
                {(comparison.recommended_review_focus || []).map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      )}
    </section>
  );
}
