import { Suspense } from "react";

import { MapRequestClient } from "@/components/map-request-client";
import { SectionHeader } from "@/components/section-header";

export default function MapRequestPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Map Request"
        title="Convert a plain-English GIS request into a draft recipe"
        description="The backend selects only verified AutoMap catalog layers. No external LLM API, no geometry ingestion, and no publishing occur here."
      />
      <Suspense fallback={<div className="panel">Loading prompt form...</div>}>
        <MapRequestClient />
      </Suspense>
    </>
  );
}
