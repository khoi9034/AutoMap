import Link from "next/link";

import { DashboardQuickStart } from "@/components/dashboard-quick-start";
import { samplePrompts } from "@/components/navigation";
import { SectionHeader } from "@/components/section-header";
import { StatCard } from "@/components/stat-card";
import { StatusChip } from "@/components/status-chip";
import { WorkflowCards } from "@/components/workflow-cards";
import { getDataGaps, getHistory, getStatusOrFallback, listPackets } from "@/lib/api";
import type { DataGap, HistoryRow, PacketSummary, PacketsResponse } from "@/types/automap";

function shortDate(value: string | undefined): string {
  if (!value) {
    return "Not recorded";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

async function safeDataGaps(): Promise<DataGap[]> {
  try {
    return (await getDataGaps()).rows || [];
  } catch {
    return [];
  }
}

async function safeHistory(): Promise<HistoryRow[]> {
  try {
    return (await getHistory()).request_history || [];
  } catch {
    return [];
  }
}

async function safePackets(): Promise<PacketsResponse> {
  try {
    return await listPackets();
  } catch {
    return {};
  }
}

function packetRows(packets: PacketsResponse): PacketSummary[] {
  return [
    ...(packets.approved_packets || []),
    ...(packets.adjusted_packets || []),
    ...(packets.review_packets || []),
  ].slice(0, 5);
}

export default async function DashboardPage() {
  const [status, dataGaps, history, packets] = await Promise.all([
    getStatusOrFallback(),
    safeDataGaps(),
    safeHistory(),
    safePackets(),
  ]);

  const latestHistory = history.slice(0, 4);
  const latestPackets = packetRows(packets);
  const knownGapKeys = ["current_permits", "current_planning_cases", "current_development_pipeline"];
  const activeKnownGaps = dataGaps.filter((gap) => knownGapKeys.includes(gap.gap_key || ""));

  return (
    <div className="page-stack dashboard-page">
      <section className="dashboard-hero">
        <div>
          <p className="eyebrow">AutoMap: County GIS Request Engine</p>
          <h1>Draft county GIS map requests from verified catalog layers.</h1>
          <p>
            AutoMap turns plain-English planning questions into local recipes, WebMap drafts, review packets,
            adjustment files, approval gates, and dry-run publish receipts.
          </p>
          <div className="chip-row">
            <StatusChip tone="success">Dry-run only</StatusChip>
            <StatusChip tone="success">No ArcGIS login required</StatusChip>
            <StatusChip tone="success">Frontend 3010</StatusChip>
            <StatusChip tone="success">Backend/API 8010</StatusChip>
          </div>
        </div>
        <div className="hero-health-panel">
          <h3>System health</h3>
          <dl className="status-list">
            <div>
              <dt>Backend</dt>
              <dd>{status.database_connected ? "connected" : "check API"}</dd>
            </div>
            <div>
              <dt>Verified layers</dt>
              <dd>{status.catalog?.verified_layer_count ?? 0}</dd>
            </div>
            <div>
              <dt>Real publish</dt>
              <dd>{status.real_publish_enabled ? "enabled" : "disabled"}</dd>
            </div>
            <div>
              <dt>Reserved CFS ports</dt>
              <dd>{(status.ports?.reserved || [3000, 8000]).join(" / ")}</dd>
            </div>
          </dl>
        </div>
      </section>

      <SectionHeader
        eyebrow="Dashboard"
        title="Operations console"
        description="Use this workspace to move from request to local preview, human review, approval, and dry-run-only publishing checks."
      />

      <section className="stats-grid" aria-label="System stats">
        <StatCard label="Catalog records" value={status.catalog?.layer_count} />
        <StatCard label="Verified layers" value={status.catalog?.verified_layer_count} />
        <StatCard label="Field profiles" value={status.profiles?.field_profile_count} />
        <StatCard label="Value profiles" value={status.profiles?.value_profile_count} />
        <StatCard label="Data gaps" value={status.data_gap_count} />
        <StatCard label="Review packets" value={status.packets?.review_packet_count} />
        <StatCard label="Adjusted packets" value={status.packets?.adjusted_packet_count} />
        <StatCard label="Approved packets" value={status.packets?.approved_packet_count} />
        <StatCard label="Analysis reports" value={status.analysis_report_count} />
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <DashboardQuickStart />
          <WorkflowCards />
        </div>
        <aside className="dashboard-side">
          <section className="panel safety-card">
            <div className="panel-title-row">
              <h3>Safety status</h3>
              <StatusChip tone="success">Draft-only UI</StatusChip>
            </div>
            <ul className="check-list">
              <li>Frontend publish actions are dry-run only.</li>
              <li>Real Portal publish remains CLI-only.</li>
              <li>No public or organization sharing is exposed.</li>
              <li>AutoMap ports are 3010 and 8010.</li>
              <li>CFS ports 3000 and 8000 are reserved.</li>
            </ul>
          </section>
          <section className="panel">
            <h3>Data gap summary</h3>
            {activeKnownGaps.length ? (
              <div className="mini-list">
                {activeKnownGaps.map((gap) => (
                  <div key={gap.gap_key}>
                    <strong>{gap.gap_key}</strong>
                    <span>{gap.status || "open"}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="muted">No known current development gap rows were returned by the API.</p>
            )}
            <Link className="text-link" href="/data-gaps">
              Review data gaps
            </Link>
          </section>
        </aside>
      </section>

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h3>Demo scenarios</h3>
            <p className="muted">Start with one of the county GIS request patterns used for local workflow testing.</p>
          </div>
          <StatusChip tone="success">Verified catalog only</StatusChip>
        </div>
        <div className="scenario-grid">
          {samplePrompts.map((prompt) => (
            <Link className="scenario-card" href={`/map-request?prompt=${encodeURIComponent(prompt)}`} key={prompt}>
              <strong>{prompt}</strong>
              <span>Open request workspace</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="dashboard-grid">
        <section className="panel">
          <div className="panel-title-row">
            <h3>Latest workflow activity</h3>
            <Link className="text-link" href="/history">
              View history
            </Link>
          </div>
          {latestHistory.length ? (
            <div className="activity-list">
              {latestHistory.map((row) => (
                <article key={`${row.id}-${row.created_at}`}>
                  <div>
                    <strong>{row.map_title || "Untitled request"}</strong>
                    <p>{row.raw_prompt || "No prompt recorded"}</p>
                  </div>
                  <span>{shortDate(row.created_at)}</span>
                </article>
              ))}
            </div>
          ) : (
            <div className="empty-state compact-empty">
              <h3>No recent workflow history</h3>
              <p>Create a recipe or review packet to populate this list.</p>
            </div>
          )}
        </section>

        <section className="panel">
          <div className="panel-title-row">
            <h3>Latest packets</h3>
            <Link className="text-link" href="/map-preview">
              Open preview
            </Link>
          </div>
          {latestPackets.length ? (
            <div className="mini-list packet-mini-list">
              {latestPackets.map((packet) => (
                <div key={packet.packet_path || packet.packet_id}>
                  <strong>{packet.map_title || packet.packet_id}</strong>
                  <span>{packet.packet_type || "packet"} - {shortDate(packet.updated_at)}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state compact-empty">
              <h3>No packets found</h3>
              <p>Generate a review packet from Recipe Review to enable preview and adjustment steps.</p>
            </div>
          )}
        </section>
      </section>
    </div>
  );
}
