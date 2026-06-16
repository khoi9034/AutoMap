import { CatalogSearchClient } from "@/components/catalog-search-client";
import { SectionHeader } from "@/components/section-header";

export default function LayerCatalogPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Developer / GIS Analyst Tools"
        title="Search verified GIS layers"
        description="Layer selection uses the trusted AutoMap PostGIS catalog. New OpenData sources remain preferred when verified."
      />
      <CatalogSearchClient />
    </>
  );
}
