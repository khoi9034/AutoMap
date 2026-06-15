import { SectionHeader } from "@/components/section-header";
import { StatusChip } from "@/components/status-chip";
import { getDataGaps } from "@/lib/api";
import type { DataGap } from "@/types/automap";

function gapTitle(key: string): string {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export default async function DataGapsPage() {
  let rows: DataGap[] = [];
  let error: string | null = null;
  try {
    rows = (await getDataGaps()).rows || [];
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "Data gaps failed.";
  }
  const knownCurrentGapKeys = ["current_permits", "current_planning_cases", "current_development_pipeline"];
  const knownCurrentGaps = knownCurrentGapKeys.map(
    (gapKey) => rows.find((row) => row.gap_key === gapKey) || ({ gap_key: gapKey } as DataGap),
  );

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

      <section className="notice">
        <strong>How to read this page</strong>
        <p>
          AutoMap only selects layers that exist in the verified catalog. When a topic such as permits or planning
          cases lacks an approved current layer, the request stays transparent and the missing source is tracked here.
        </p>
      </section>

      <section className="data-gap-grid" aria-label="Known current data gaps">
        {knownCurrentGaps.map((gap) => (
          <article className="data-gap-card" key={gap.gap_key}>
            <div className="panel-title-row">
              <div>
                <p className="eyebrow">Known gap</p>
                <h3>{gapTitle(gap.gap_key || "unknown_gap")}</h3>
              </div>
              <StatusChip tone={gap.status === "closed" ? "success" : "warning"}>{gap.status || "open"}</StatusChip>
            </div>
            <dl className="layer-meta">
              <div>
                <dt>Topic</dt>
                <dd>{gap.topic || "development activity"}</dd>
              </div>
              <div>
                <dt>Missing layer type</dt>
                <dd>{gap.missing_layer_type || "approved current layer"}</dd>
              </div>
            </dl>
            <p className="muted">{gap.reason || "Tracked until a verified county source is available."}</p>
          </article>
        ))}
      </section>

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
                    <StatusChip tone={row.status === "open" ? "warning" : "success"}>{row.status}</StatusChip>
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
