import { ProxySourceBadge } from "@/components/proxy-source-badge";
import { StatusChip } from "@/components/status-chip";
import type { SourceCoverage, SourceCoverageEntry } from "@/types/automap";

type SourceCoveragePanelProps = {
  coverage?: SourceCoverage | null;
};

const GROUPS: Array<{ key: keyof SourceCoverage; title: string; empty: string }> = [
  { key: "official_sources", title: "Official sources", empty: "No official external sources selected." },
  { key: "proxy_sources", title: "Proxy sources", empty: "No proxy sources selected." },
  { key: "limited_coverage_sources", title: "Limited coverage", empty: "No limited-coverage sources selected." },
  { key: "reference_sources", title: "Reference context", empty: "No reference-only sources selected." },
  { key: "missing_official_sources", title: "Missing official data", empty: "No missing official source gaps recorded." },
];

function sourceTitle(entry: SourceCoverageEntry): string {
  return entry.display_title || entry.layer_name || entry.gap_key || entry.source_key || "Source";
}

function renderEntry(entry: SourceCoverageEntry) {
  return (
    <div className="mini-row" key={`${entry.layer_key || entry.gap_key || entry.source_key}-${sourceTitle(entry)}`}>
      <div>
        <strong>{sourceTitle(entry)}</strong>
        <span>{entry.coverage_geography || entry.reason || "Coverage should be confirmed during review."}</span>
      </div>
      <div className="chip-row">
        <ProxySourceBadge role={entry.source_role} status={entry.source_status || entry.status} approval={entry.approval_status} />
        {entry.status ? <StatusChip>{entry.status}</StatusChip> : null}
      </div>
      {entry.limitation || entry.reason ? <p className="muted">{entry.limitation || entry.reason}</p> : null}
    </div>
  );
}

export function SourceCoveragePanel({ coverage }: SourceCoveragePanelProps) {
  if (!coverage) {
    return (
      <section className="panel">
        <h3>Source coverage</h3>
        <p className="muted">Generate a recipe to see official, proxy, reference, and limited-coverage source use.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Source coverage</h3>
          <p className="muted">Proxy and reference layers are review context. They do not resolve official data gaps.</p>
        </div>
        <StatusChip tone={(coverage.warnings || []).length ? "warning" : "success"}>
          {(coverage.warnings || []).length ? `${coverage.warnings?.length} warning(s)` : "No coverage warnings"}
        </StatusChip>
      </div>
      <div className="data-gap-grid">
        {GROUPS.map((group) => {
          const rows = (coverage[group.key] as SourceCoverageEntry[] | undefined) || [];
          return (
            <article className="data-gap-card" key={group.key}>
              <h4>{group.title}</h4>
              <div className="mini-list">{rows.length ? rows.map(renderEntry) : <p className="muted">{group.empty}</p>}</div>
            </article>
          );
        })}
      </div>
      {(coverage.warnings || []).length ? (
        <div className="notice notice-warning">
          <strong>Coverage warnings</strong>
          <ul className="plain-list">
            {(coverage.warnings || []).slice(0, 8).map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
