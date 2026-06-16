import { LearningCenterClient } from "@/components/learning-center-client";
import { SectionHeader } from "@/components/section-header";

export default function LearningPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Developer / GIS Analyst Tools"
        title="Feedback Learning and Approved Pattern Library"
        description="Reuse approved local workflow decisions as reviewable defaults for future county GIS requests."
      />
      <LearningCenterClient />
    </div>
  );
}
