import Link from "next/link";

import { StatusChip } from "@/components/status-chip";
import { STATIC_DEMO_PROMPT } from "@/lib/static-demo";

const capabilities = [
  "Address-to-nearest-facility maps",
  "Floodplain and zoning context",
  "Parcel table previews",
  "Print/export map exhibits",
];

const stack = ["Next.js", "FastAPI", "PostGIS", "ArcGIS REST", "Render", "Vercel"];

export default function LandingPage() {
  const demoHref = `/map-composer?prompt=${encodeURIComponent(STATIC_DEMO_PROMPT)}&demo=1`;

  return (
    <div className="page-stack landing-page">
      <section className="landing-hero landing-hero-compact">
        <div>
          <p className="eyebrow">AutoMap</p>
          <h1>County GIS Request Engine</h1>
          <p>Turn plain-language county GIS requests into draft maps, tables, and review-ready outputs.</p>
          <div className="button-row">
            <Link className="button" href="/map-composer">
              Open Live Demo
            </Link>
            <Link className="button button-secondary" href="/map-composer#presets">
              View Presets
            </Link>
            <Link className="button button-secondary" href="/methodology">
              View Methodology
            </Link>
            <Link className="button button-secondary" href="/system-status">
              View System Status
            </Link>
          </div>
          <div className="chip-row">
            <StatusChip tone="success">Scope: Cabarrus County, NC</StatusChip>
            <StatusChip tone="success">Live workflow first</StatusChip>
            <StatusChip tone="success">Real publish disabled</StatusChip>
          </div>
        </div>
      </section>

      <section className="portfolio-summary-grid">
        <article className="panel">
          <p className="eyebrow">What it does</p>
          <h3>Draft GIS outputs from plain English</h3>
          <p className="muted">AutoMap turns planning questions into layer choices, map previews, table drafts, and print-ready exhibits.</p>
        </article>
        <article className="panel">
          <p className="eyebrow">Live demo scope</p>
          <h3>Cabarrus County, NC</h3>
          <p className="muted">Live address and parcel workflows are county-scoped so the demo stays honest about available public GIS data.</p>
        </article>
        <article className="panel">
          <p className="eyebrow">Example capabilities</p>
          <ul className="compact-list">
            {capabilities.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="panel">
          <p className="eyebrow">Tech stack</p>
          <div className="chip-row">
            {stack.map((item) => (
              <StatusChip key={item}>{item}</StatusChip>
            ))}
          </div>
        </article>
        <article className="panel">
          <p className="eyebrow">Safety notes</p>
          <h3>Draft-only portfolio demo</h3>
          <p className="muted">No real ArcGIS publishing, no owner/name lookup, no paid geocoding, and no claim that draft routes are official navigation.</p>
        </article>
        <article className="panel">
          <p className="eyebrow">Fallback</p>
          <h3>Demo remains viewable</h3>
          <p className="muted">If the free backend is warming up, the live workflow stays primary and a static Cabarrus demo is available as backup.</p>
          <Link className="button button-secondary" href={demoHref}>
            View Static Demo
          </Link>
        </article>
      </section>
    </div>
  );
}
