import { Suspense } from "react";

import { MapComposerClient } from "@/components/map-composer-client";

export default function MapComposerPage() {
  return (
    <div className="page-stack">
      <Suspense fallback={<div className="panel">Loading Map Composer...</div>}>
        <MapComposerClient />
      </Suspense>
    </div>
  );
}
