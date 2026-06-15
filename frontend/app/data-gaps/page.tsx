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

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Data Gaps"
        title="Current missing data registry"
        description="These gaps are tracked for review and sourcing; AutoMap does not fake unavailable layers."
      />
      {error ? <p className="error-text">{error}</p> : null}
      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Gap</th>
                <th>Topic</th>
                <th>Status</th>
                <th>Reason</th>
                <th>Suggested source</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.gap_key}>
                  <td>{row.gap_key}</td>
                  <td>{row.topic}</td>
                  <td>
                    <StatusChip tone={row.status === "open" ? "warning" : "success"}>{row.status}</StatusChip>
                  </td>
                  <td>{row.reason}</td>
                  <td>{row.suggested_source || "Needs source confirmation"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
