import { SectionHeader } from "@/components/section-header";
import { WorkflowStepper } from "@/components/workflow-stepper";
import { RecipeReviewClient } from "@/components/recipe-review-client";

export default function RecipeReviewPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Advanced Workflow"
        title="Internal recipe review tools"
        description="Confirm the recipe before creating local WebMap JSON or a review packet. New verified OpenData layers remain preferred over legacy metadata."
      />
      <WorkflowStepper activeStep="recipe" />
      <RecipeReviewClient />
    </>
  );
}
