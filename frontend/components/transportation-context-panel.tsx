import { ProxySourceBadge } from "@/components/proxy-source-badge";
import type { SourceCoverage, SourceCoverageEntry } from "@/types/automap";

function transportationEntries(coverage?: SourceCoverage | null): SourceCoverageEntry[] {
  const all = [
    ...((coverage?.reference_sources || []) as SourceCoverageEntry[]),
    ...((coverage?.official_sources || []) as SourceCoverageEntry[]),
  ];
  return all.filter((entry) => ["transportation", "transportation_projects"].includes(entry.category || ""));
}

export function TransportationContextPanel({ coverage }: { coverage?: SourceCoverage | null }) {
  const entries = transportationEntries(coverage);
  return (
    <section className="panel">
      <h3>Transportation context</h3>
      <p className="muted">AADT and STIP are context layers. They are not development pipeline or approval sources.</p>
      <div className="mini-list">
        {entries.length ? (
          entries.map((entry) => (
            <div key={entry.layer_key || entry.source_key}>
              <strong>{entry.display_title || entry.layer_name}</strong>
              <span>{entry.limitation || entry.coverage_geography}</span>
              <div className="chip-row">
                <ProxySourceBadge role={entry.source_role} status={entry.source_status} approval={entry.approval_status} />
              </div>
            </div>
          ))
        ) : (
          <p className="muted">No transportation context layer selected for this recipe.</p>
        )}
      </div>
    </section>
  );
}
