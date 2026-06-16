import { SectionHeader } from "@/components/section-header";
import { WorkflowClient } from "@/components/workflow-client";

export default function WorkflowPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Guided workflow"
        title="Prompt to parcel-focused preview"
        description="Generate a recipe, create a focused preview when inputs are ready, then adjust, analyze, report, or export without publishing."
      />
      <WorkflowClient />
    </div>
  );
}
