import { SectionHeader } from "@/components/section-header";
import { RecipeReviewClient } from "@/components/recipe-review-client";

export default function RecipeReviewPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Recipe Review"
        title="Review selected layers, filters, operations, and gaps"
        description="Confirm the recipe before creating local WebMap JSON or a review packet. New verified OpenData layers remain preferred over legacy metadata."
      />
      <RecipeReviewClient />
    </>
  );
}
