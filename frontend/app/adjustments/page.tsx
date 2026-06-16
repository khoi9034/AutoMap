import { AdjustmentsClient } from "@/components/adjustments-client";
import { SectionHeader } from "@/components/section-header";
import { WorkflowStepper } from "@/components/workflow-stepper";

export default function AdjustmentsPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Internal Review Tools"
        title="Advanced adjustment loop"
        description="Edit YAML to adjust title, layer order, opacity, visibility, filters, notes, and warnings without mutating the original packet."
      />
      <WorkflowStepper activeStep="adjustments" />
      <AdjustmentsClient />
    </>
  );
}
