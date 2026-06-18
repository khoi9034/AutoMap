import { Suspense } from "react";

import { SectionHeader } from "@/components/section-header";
import { TableCenterClient } from "@/components/table-center-client";

export default function TablesPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Tables"
        title="Table and Data Export Center"
        description="Plan bounded attribute tables from verified catalog layers, preview rows without geometry, and export local CSV/JSON/Markdown packages."
      />
      <Suspense fallback={<section className="panel">Loading Table Center...</section>}>
        <TableCenterClient />
      </Suspense>
    </div>
  );
}
