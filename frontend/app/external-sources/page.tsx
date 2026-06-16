import { ExternalSourcesClient } from "@/components/external-sources-client";
import { SectionHeader } from "@/components/section-header";

export default function ExternalSourcesPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Developer / GIS Analyst Tools"
        title="Candidate REST source connector registry"
        description="Review approved, candidate, and proxy REST sources before they can help resolve AutoMap data gaps."
      />
      <ExternalSourcesClient />
    </div>
  );
}
