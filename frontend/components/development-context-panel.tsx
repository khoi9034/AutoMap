import { ProxySourceBadge } from "@/components/proxy-source-badge";
import type { SourceCoverage, SourceCoverageEntry } from "@/types/automap";

function developmentEntries(coverage?: SourceCoverage | null): SourceCoverageEntry[] {
  return [
    ...((coverage?.proxy_sources || []) as SourceCoverageEntry[]),
    ...((coverage?.limited_coverage_sources || []) as SourceCoverageEntry[]),
    ...((coverage?.missing_official_sources || []) as SourceCoverageEntry[]),
  ].filter((entry) => {
    const text = `${entry.category || ""} ${entry.gap_key || ""} ${entry.display_title || ""}`.toLowerCase();
    return text.includes("development") || text.includes("permit") || text.includes("planning");
  });
}

export function DevelopmentContextPanel({ coverage }: { coverage?: SourceCoverage | null }) {
  const entries = developmentEntries(coverage);
  return (
    <section className="panel">
      <h3>Development context</h3>
      <p className="muted">Proxy activity and limited municipal planning layers must not be treated as official approvals.</p>
      <div className="mini-list">
        {entries.length ? (
          entries.map((entry) => (
            <div key={entry.layer_key || entry.gap_key || entry.source_key}>
              <strong>{entry.display_title || entry.layer_name || entry.gap_key}</strong>
              <span>{entry.reason || entry.limitation || entry.coverage_geography}</span>
              <div className="chip-row">
                <ProxySourceBadge role={entry.source_role} status={entry.source_status || entry.status} approval={entry.approval_status} />
              </div>
            </div>
          ))
        ) : (
          <p className="muted">No development proxy, limited coverage, or missing official source context recorded.</p>
        )}
      </div>
    </section>
  );
}
