import { PublishCenterClient } from "@/components/publish-center-client";
import { SectionHeader } from "@/components/section-header";

export default function PublishCenterPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Publish Center"
        title="Dry-run publish and smoke-test center"
        description="The frontend only runs dry-run publish checks and smoke-test dry-runs. Real private publishing remains CLI-only."
      />
      <PublishCenterClient />
    </>
  );
}
