import { JsonPanel } from "@/components/json-panel";
import { ProductionHealthCard } from "@/components/production-health-card";
import { SectionHeader } from "@/components/section-header";
import { StatCard } from "@/components/stat-card";
import { StatusChip } from "@/components/status-chip";
import { getStatusOrFallback } from "@/lib/api";

export default async function SystemStatusPage() {
  const status = await getStatusOrFallback();

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Production readiness"
        title="AutoMap system status"
        description="Recruiter-safe health summary for the Vercel frontend, Render API, Supabase PostGIS, and publish safety."
      />
      <ProductionHealthCard compact />
      <section className="stats-grid">
        <StatCard label="AutoMap version" value={status.version} />
        <StatCard label="Frontend" value="Vercel online" />
        <StatCard label="API" value={status.errors?.length ? "checking" : "Render online"} />
        <StatCard label="Database" value={status.database_connected ? "Supabase online" : "checking"} />
        <StatCard label="Demo fallback" value="available" />
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
        <StatCard label="Planning scenarios" value={status.planning_scenario_count} />
        <StatCard label="Scenario variants" value={status.scenario_variant_count} />
        <StatCard label="Scenario comparisons" value={status.scenario_comparison_count} />
        <StatCard label="Parcel sets" value={status.parcel_set_count} />
        <StatCard label="Parcel contexts" value={status.parcel_context_session_count} />
      </section>
      <section className="panel">
        <h3>Deployment separation</h3>
        <div className="chip-row">
          <StatusChip tone="success">Frontend: Vercel</StatusChip>
          <StatusChip tone="success">API: Render</StatusChip>
          <StatusChip tone={status.database_connected ? "success" : "warning"}>Database: Supabase PostGIS</StatusChip>
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
