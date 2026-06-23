import { SectionHeader } from "@/components/section-header";
import { StatusChip } from "@/components/status-chip";

const architecture = ["Vercel frontend", "Vercel API proxy", "Render FastAPI", "Supabase PostGIS"];

export default function MethodologyPage() {
  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Methodology"
        title="How AutoMap works"
        description="A recruiter-friendly overview of the architecture, request logic, safety boundaries, and current limits."
      />

      <section className="portfolio-summary-grid">
        <article className="panel">
          <p className="eyebrow">System architecture</p>
          <h3>Production deployment</h3>
          <div className="chip-row">
            {architecture.map((item) => (
              <StatusChip key={item}>{item}</StatusChip>
            ))}
          </div>
          <p className="muted">Browser requests go through the Vercel same-origin proxy before reaching the Render backend and Supabase database.</p>
        </article>

        <article className="panel">
          <p className="eyebrow">Data scope</p>
          <h3>Cabarrus County public GIS</h3>
          <p className="muted">Address, parcel, floodplain, zoning, road, facility, and historical workflows are scoped to verified Cabarrus County, NC sources.</p>
        </article>

        <article className="panel">
          <p className="eyebrow">Request intelligence</p>
          <h3>Prompt to draft output</h3>
          <p className="muted">AutoMap classifies the request, selects verified layers, builds a map/table recipe, renders a draft preview, and preserves the adjusted map state for print/export.</p>
        </article>

        <article className="panel">
          <p className="eyebrow">Safety</p>
          <h3>Draft-only by design</h3>
          <p className="muted">Real ArcGIS publishing is disabled. Routes are draft road-centerline guidance, not official navigation. Owner/name search is not used by default.</p>
        </article>

        <article className="panel">
          <p className="eyebrow">Limitations</p>
          <h3>Prototype boundaries</h3>
          <p className="muted">The live demo is county-scoped, data-dependent, and hosted on free infrastructure that may cold start. Some table joins and historical coverage require review.</p>
        </article>

        <article className="panel">
          <p className="eyebrow">Future work</p>
          <h3>Where it can grow</h3>
          <p className="muted">Next steps include more counties, stronger async jobs, richer table exports, improved route costing, and cleaner data-source administration.</p>
        </article>
      </section>
    </div>
  );
}
