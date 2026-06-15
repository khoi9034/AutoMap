import { CatalogSearchClient } from "@/components/catalog-search-client";
import { SectionHeader } from "@/components/section-header";

export default function LayerCatalogPage() {
  return (
    <>
      <SectionHeader
        eyebrow="Layer Catalog"
        title="Search verified GIS layers"
        description="Layer selection uses the trusted AutoMap PostGIS catalog. New OpenData sources remain preferred when verified."
      />
      <CatalogSearchClient />
    </>
  );
}
