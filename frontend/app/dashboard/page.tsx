import { DashboardQuickStart } from "@/components/dashboard-quick-start";
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
        <StatCard label="Value profiles" value={status.profiles?.value_profile_count} />
        <StatCard label="Data gaps" value={status.data_gap_count} />
        <StatCard label="Review packets" value={status.packets?.review_packet_count} />
        <StatCard label="Adjusted packets" value={status.packets?.adjusted_packet_count} />
        <StatCard label="Approved packets" value={status.packets?.approved_packet_count} />
        <StatCard label="Real publish enabled" value={status.real_publish_enabled ? "true" : "false"} />
      </section>

      <DashboardQuickStart />
    </div>
  );
}
