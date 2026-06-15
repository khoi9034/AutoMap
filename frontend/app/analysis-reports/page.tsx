import { AnalysisReportsClient } from "@/components/analysis-reports-client";
import { SectionHeader } from "@/components/section-header";

export default function AnalysisReportsPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Analysis Reports"
        title="Summary analytics and report exports"
        description="Convert safe count-first analysis and refinement outputs into local HTML, Markdown, JSON, and CSV planning review packages."
      />
      <AnalysisReportsClient />
    </div>
  );
}
