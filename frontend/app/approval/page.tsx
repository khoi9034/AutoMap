import { ApprovalClient } from "@/components/approval-client";
import { SectionHeader } from "@/components/section-header";
import { WorkflowStepper } from "@/components/workflow-stepper";

export default function ApprovalPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Internal Review Tools"
        title="Local reviewer approval gate"
        description="Approval records draft readiness only. It does not publish and does not create ArcGIS items."
      />
      <WorkflowStepper activeStep="approval" />
      <ApprovalClient />
    </>
  );
}
