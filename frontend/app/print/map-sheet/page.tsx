import { Suspense } from "react";

import { PrintMapSheetRoute } from "@/components/print/print-map-sheet-route";

export default function PrintMapSheetPage() {
  return (
    <Suspense fallback={<main className="print-only-route">Loading print sheet...</main>}>
      <PrintMapSheetRoute />
    </Suspense>
  );
}
