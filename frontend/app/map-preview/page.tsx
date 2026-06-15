import { MapPreviewClient } from "@/components/map-preview-client";
import { SectionHeader } from "@/components/section-header";
import { WorkflowStepper } from "@/components/workflow-stepper";

export default function MapPreviewPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Map Preview"
        title="Preview local draft WebMap JSON"
        description="The preview uses backend packet metadata and existing local preview routes. It is not an ArcGIS publish action."
      />
      <WorkflowStepper activeStep="preview" />
      <MapPreviewClient />
    </>
  );
}
