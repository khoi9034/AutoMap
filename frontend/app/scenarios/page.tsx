import { ScenarioBuilder } from "@/components/scenario-builder";
import { SectionHeader } from "@/components/section-header";

export default function ScenariosPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Scenarios"
        title="Planning scenario and suitability intelligence"
        description="Build transparent growth, constraint, and transportation planning frameworks without treating scores as official recommendations."
      />
      <ScenarioBuilder />
    </div>
  );
}
