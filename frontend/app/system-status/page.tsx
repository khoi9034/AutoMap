import { JsonPanel } from "@/components/json-panel";
import { SectionHeader } from "@/components/section-header";
import { StatCard } from "@/components/stat-card";
import { StatusChip } from "@/components/status-chip";
import { getStatusOrFallback } from "@/lib/api";

export default async function SystemStatusPage() {
  const status = await getStatusOrFallback();

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="System Status"
        title="Backend health and publish safety"
        description="Sanitized status from the FastAPI backend. Secrets, database URLs, and credentials are never displayed."
      />
      <section className="stats-grid">
        <StatCard label="AutoMap version" value={status.version} />
        <StatCard label="DB connected" value={status.database_connected ? "true" : "false"} />
        <StatCard label="Catalog records" value={status.catalog?.layer_count} />
        <StatCard label="Verified layers" value={status.catalog?.verified_layer_count} />
        <StatCard label="Field profiles" value={status.profiles?.field_profile_count} />
        <StatCard label="Value profiles" value={status.profiles?.value_profile_count} />
        <StatCard label="Data gaps" value={status.data_gap_count} />
        <StatCard label="External sources" value={status.external_source_count} />
        <StatCard label="Review packets" value={status.packets?.review_packet_count} />
        <StatCard label="Approved packets" value={status.packets?.approved_packet_count} />
        <StatCard label="Analysis runs" value={status.analysis_run_count} />
        <StatCard label="Analysis refinements" value={status.analysis_refinement_count} />
        <StatCard label="Analysis reports" value={status.analysis_report_count} />
        <StatCard label="Frontend port" value={status.ports?.frontend || 3010} />
        <StatCard label="Backend/API port" value={status.ports?.backend_api || 8010} />
      </section>
      <section className="panel">
        <h3>Port separation</h3>
        <div className="chip-row">
          <StatusChip tone="success">AutoMap frontend: {status.ports?.frontend || 3010}</StatusChip>
          <StatusChip tone="success">AutoMap backend/API: {status.ports?.backend_api || 8010}</StatusChip>
          <StatusChip tone="warning">CFS reserved: {(status.ports?.reserved || [3000, 8000]).join(" / ")}</StatusChip>
        </div>
      </section>
      <section className="panel">
        <h3>Publish mode</h3>
        <div className="chip-row">
          <StatusChip tone={status.real_publish_enabled ? "warning" : "success"}>
            real_publish_enabled: {String(status.real_publish_enabled)}
          </StatusChip>
          <StatusChip>profile: {status.arcgis_publish_profile || "dev"}</StatusChip>
        </div>
        <p className="muted">{status.arcgis_publisher_mode}</p>
      </section>
      <JsonPanel title="Full sanitized status" value={status} />
    </div>
  );
}
