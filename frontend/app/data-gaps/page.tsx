import { SectionHeader } from "@/components/section-header";
import { StatusChip } from "@/components/status-chip";
import { getDataGaps } from "@/lib/api";
import type { DataGap } from "@/types/automap";

export default async function DataGapsPage() {
  let rows: DataGap[] = [];
  let error: string | null = null;
  try {
    rows = (await getDataGaps()).rows || [];
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "Data gaps failed.";
  }
  const knownCurrentGapKeys = ["current_permits", "current_planning_cases", "current_development_pipeline"];
  const knownCurrentGaps = rows.filter((row) => knownCurrentGapKeys.includes(row.gap_key || ""));

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Data Gaps"
        title="Current missing data registry"
        description="These gaps are tracked for review and sourcing; AutoMap does not fake unavailable layers."
      />
      {error ? <p className="error-text">{error}</p> : null}
      <section className="stats-grid">
        {knownCurrentGapKeys.map((gapKey) => {
          const gap = knownCurrentGaps.find((row) => row.gap_key === gapKey);
          return (
            <div className="panel" key={gapKey}>
              <h3>{gapKey}</h3>
              <StatusChip tone={gap?.status === "closed" ? "success" : "warning"}>{gap?.status || "open"}</StatusChip>
              <p className="muted">{gap?.reason || "Tracked as a current data gap until a verified layer is available."}</p>
            </div>
          );
        })}
      </section>
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Gap</th>
                <th>Topic</th>
                <th>Missing layer type</th>
                <th>Status</th>
                <th>Reason</th>
                <th>Suggested source</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.gap_key}>
                  <td>{row.gap_key}</td>
                  <td>{row.topic}</td>
                  <td>{row.missing_layer_type}</td>
                  <td>
                    <StatusChip tone={row.status === "open" ? "warning" : "success"}>{row.status}</StatusChip>
                  </td>
                  <td>{row.reason}</td>
                  <td>{row.suggested_source || "Needs source confirmation"}</td>
                  <td>{row.created_at || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
