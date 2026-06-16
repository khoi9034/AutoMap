import { AnalysisClient } from "@/components/analysis-client";
import { SectionHeader } from "@/components/section-header";

export default function AnalysisPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Analysis"
        title="Safe bounded spatial execution"
        description="Plan and run supported local analysis with count-first safeguards, output caps, and ignored GeoJSON artifacts."
      />
      <AnalysisClient />
    </>
  );
}
