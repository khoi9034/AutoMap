import { ScenarioWorkbenchClient } from "@/components/scenario-workbench-client";
import { SectionHeader } from "@/components/section-header";

export default function ScenarioWorkbenchPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Scenario Workbench"
        title="Tune weights, compare variants, and create draft recipes"
        description="Review scenario assumptions interactively while keeping proxy, missing-data, and draft-only warnings visible."
      />
      <ScenarioWorkbenchClient />
    </div>
  );
}
