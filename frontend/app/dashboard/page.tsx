import Link from "next/link";

import { samplePrompts } from "@/components/navigation";
import { SectionHeader } from "@/components/section-header";
import { StatCard } from "@/components/stat-card";
import { WorkflowCards } from "@/components/workflow-cards";
import { getStatusOrFallback } from "@/lib/api";

export default async function DashboardPage() {
  const status = await getStatusOrFallback();

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Dashboard"
        title="AutoMap operations console"
        description="Create draft map recipes, review verified layers, preview local WebMap JSON, and run dry-run-only publishing checks."
      />

      <WorkflowCards />

      <section className="stats-grid" aria-label="System stats">
        <StatCard label="Catalog records" value={status.catalog?.layer_count} />
        <StatCard label="Verified layers" value={status.catalog?.verified_layer_count} />
        <StatCard label="Field profiles" value={status.profiles?.field_profile_count} />
        <StatCard label="Data gaps" value={status.data_gap_count} />
        <StatCard label="Review packets" value={status.packets?.review_packet_count} />
        <StatCard label="Adjusted packets" value={status.packets?.adjusted_packet_count} />
        <StatCard label="Approved packets" value={status.packets?.approved_packet_count} />
        <StatCard label="Real publish enabled" value={status.real_publish_enabled ? "true" : "false"} />
      </section>

      <section className="panel">
        <h3>What map do you need?</h3>
        <p className="muted">Start from a plain-English request, then review the selected layers before generating packets.</p>
        <div className="button-row">
          <Link className="button" href="/map-request">
            Open Map Request
          </Link>
          <Link className="button button-secondary" href="/system-status">
            View System Status
          </Link>
        </div>
      </section>

      <section className="panel">
        <h3>Sample prompts</h3>
        <div className="sample-grid">
          {samplePrompts.map((prompt) => (
            <Link key={prompt} href={`/map-request?prompt=${encodeURIComponent(prompt)}`} className="sample-button">
              {prompt}
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
