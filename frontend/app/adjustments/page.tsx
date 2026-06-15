import { AdjustmentsClient } from "@/components/adjustments-client";
import { SectionHeader } from "@/components/section-header";

export default function AdjustmentsPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Adjustments"
        title="Human adjustment loop"
        description="Edit YAML to adjust title, layer order, opacity, visibility, filters, notes, and warnings without mutating the original packet."
      />
      <AdjustmentsClient />
    </>
  );
}
