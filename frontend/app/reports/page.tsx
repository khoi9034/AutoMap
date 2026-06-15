import { ReportCenterClient } from "@/components/report-center-client";
import { SectionHeader } from "@/components/section-header";

export default function ReportsPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Reports"
        title="Report and Export Center"
        description="Turn local AutoMap workflow packets into shareable HTML, Markdown, JSON, and CSV exports for GIS review."
      />
      <ReportCenterClient />
    </div>
  );
}
