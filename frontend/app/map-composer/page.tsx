import { Suspense } from "react";

import { MapComposerClient } from "@/components/map-composer-client";
import { SectionHeader } from "@/components/section-header";

export default function MapComposerPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Simple workflow"
        title="Map Composer"
        description="Describe the map you need. AutoMap drafts it, previews it, lets you adjust it, then exports a review report."
      />
      <Suspense fallback={<div className="panel">Loading Map Composer...</div>}>
        <MapComposerClient />
      </Suspense>
    </div>
  );
}
