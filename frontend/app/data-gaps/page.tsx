import { DataGapResolverClient } from "@/components/data-gap-resolver-client";
import { SectionHeader } from "@/components/section-header";
import { StatusChip } from "@/components/status-chip";
import { getDataGaps } from "@/lib/api";
import type { DataGap } from "@/types/automap";

function toneForGapStatus(status?: string): "default" | "success" | "warning" | "danger" {
  if (status === "resolved") {
    return "success";
  }
  if (status === "rejected" || status === "failed") {
    return "danger";
  }
  if (status === "partially_supported" || status === "needs_review" || status === "open") {
    return "warning";
  }
  return "default";
}

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
        title="Missing approved source registry"
        description="These are not AutoMap failures. They are missing approved data sources needed for better map automation."
      />
      {error ? (
        <div className="inline-error" role="alert">
          <strong>Backend unavailable</strong>
          <p>{error}</p>
        </div>
      ) : null}

      <DataGapResolverClient initialRows={rows} />

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h3>All tracked gaps</h3>
            <p className="muted">Rows come from the local AutoMap data gap registry and contain no secrets.</p>
          </div>
          <StatusChip tone={rows.length ? "warning" : "success"}>{rows.length} rows</StatusChip>
        </div>
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
                    <StatusChip tone={toneForGapStatus(row.status)}>{row.status}</StatusChip>
                  </td>
                  <td>{row.reason}</td>
                  <td>{row.suggested_source || "Needs source confirmation"}</td>
                  <td>{row.created_at || ""}</td>
                </tr>
              ))}
              {!rows.length ? (
                <tr>
                  <td colSpan={7}>No data gap rows were returned by the backend.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
