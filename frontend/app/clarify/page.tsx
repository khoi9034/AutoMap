import { ClarificationPanel } from "@/components/clarification-panel";
import { SectionHeader } from "@/components/section-header";
import { WorkflowStepper } from "@/components/workflow-stepper";

export default function ClarifyPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Clarify Request"
        title="Answer GIS review questions before recipe review"
        description="Clarification is local and deterministic. Answers refine the recipe, analysis plan, filters, and warning state without publishing or requiring ArcGIS login."
      />
      <WorkflowStepper activeStep="clarify" />
      <ClarificationPanel />
    </>
  );
}
