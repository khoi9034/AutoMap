import { ExhibitReportCenterClient } from "@/components/exhibit-report-center-client";
import { SectionHeader } from "@/components/section-header";

export default function ExhibitReportsPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Reports"
        title="County Exhibits"
        description="Browse local staff-report-style map exhibit packages generated from Map Composer sessions."
      />
      <ExhibitReportCenterClient />
    </div>
  );
}
