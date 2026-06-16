import { Suspense } from "react";

import { MapComposerClient } from "@/components/map-composer-client";
import { SectionHeader } from "@/components/section-header";

export default function MapComposerPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Simple workflow"
        title="Map Composer"
        description="Prompt, preview, adjust, and print/export a local draft map without moving through the advanced workflow pages."
      />
      <Suspense fallback={<div className="panel">Loading Map Composer...</div>}>
        <MapComposerClient />
      </Suspense>
    </div>
  );
}
