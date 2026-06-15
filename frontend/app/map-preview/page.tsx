import { MapPreviewClient } from "@/components/map-preview-client";
import { SectionHeader } from "@/components/section-header";

export default function MapPreviewPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Map Preview"
        title="Preview local draft WebMap JSON"
        description="The preview uses backend packet metadata and existing local preview routes. It is not an ArcGIS publish action."
      />
      <MapPreviewClient />
    </>
  );
}
