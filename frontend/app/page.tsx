import Link from "next/link";

import { ProductionHealthCard } from "@/components/production-health-card";
import { StatusChip } from "@/components/status-chip";
import { STATIC_DEMO_PROMPT } from "@/lib/static-demo";

const projectHighlights = [
  "Plain-English map requests become draft GIS previews.",
  "Address, parcel, proximity, table, report, and exhibit workflows share one safety model.",
  "Vercel frontend proxies safely to Render FastAPI and Supabase PostGIS.",
  "Real ArcGIS publishing stays disabled in the public demo.",
];

const walkthroughSteps = [
  "Request: enter a map or table prompt.",
  "Preview: view a locked draft map with title, legend, scale, and north arrow.",
  "Adjust: pan/zoom only in the adjustment workspace, then lock the final map.",
  "Print / Export: use the locked map state for local draft exhibits and report sections.",
];

export default function LandingPage() {
  const demoHref = `/map-composer?prompt=${encodeURIComponent(STATIC_DEMO_PROMPT)}`;

  return (
    <div className="page-stack landing-page">
      <section className="landing-hero">
        <div>
          <p className="eyebrow">AutoMap portfolio demo</p>
          <h1>County GIS map composer with safe production fallbacks.</h1>
          <p>
            AutoMap turns planning-style prompts into draft map previews, proximity exhibits, reports, and bounded data
            exports. The public demo stays professional even while the free Render backend is waking up.
          </p>
          <div className="button-row">
            <Link className="button" href="/map-composer">
              Open Map Composer
            </Link>
            <Link className="button button-secondary" href={demoHref}>
              View Demo Walkthrough
            </Link>
            <Link className="button button-secondary" href="/system-status">
              View Project Summary
            </Link>
          </div>
          <div className="chip-row">
            <StatusChip tone="success">Draft-only public demo</StatusChip>
            <StatusChip tone="success">Real publish disabled</StatusChip>
            <StatusChip tone="success">Static fallback available</StatusChip>
          </div>
        </div>
        <ProductionHealthCard />
      </section>

      <section className="landing-grid">
        <article className="panel">
          <p className="eyebrow">What AutoMap does</p>
          <h3>GIS request intake to exhibit-ready draft</h3>
          <ul className="check-list">
            {projectHighlights.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="panel">
          <p className="eyebrow">Demo prompt</p>
          <h3>Nearest Fire Station from 793 Bartram Ave</h3>
          <p className="muted">
            The live workflow matches the address, finds a nearest facility, draws the route/reference line, and prepares
            a draft map layout. If the backend is cold, the static demo explains the same workflow without showing a
            broken page.
          </p>
          <Link className="text-link" href={demoHref}>
            Open the demo prompt in Map Composer
          </Link>
        </article>
      </section>

      <section className="panel">
        <div className="panel-title-row">
          <div>
            <p className="eyebrow">Workflow walkthrough</p>
            <h3>Designed to look stable during portfolio review</h3>
          </div>
          <StatusChip tone="success">Recruiter-safe</StatusChip>
        </div>
        <div className="simple-step-list landing-step-list">
          {walkthroughSteps.map((step, index) => (
            <div className="simple-step" key={step}>
              <span>{index + 1}</span>
              <div>
                <strong>{step.split(":")[0]}</strong>
                <small>{step.split(":").slice(1).join(":").trim()}</small>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
