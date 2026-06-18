import { ReportCenterClient } from "@/components/report-center-client";
import { SectionHeader } from "@/components/section-header";
import Link from "next/link";

export default function ReportsPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Reports"
        title="Report and Export Center"
        description="Turn local AutoMap workflow packets into shareable HTML, Markdown, JSON, and CSV exports for GIS review."
      />
      <section className="notice notice-info">
        <strong>Need a staff report map figure?</strong>
        <p>County exhibit packages are generated from Map Composer sessions and include source tables, warnings, and draft-only metadata.</p>
        <Link className="button button-secondary" href="/reports/exhibits">
          Open County Exhibits
        </Link>
      </section>
      <ReportCenterClient />
    </div>
  );
}
