import Link from "next/link";

import { StatusChip } from "@/components/status-chip";
import { STATIC_DEMO_PROMPT } from "@/lib/static-demo";

const cards = [
  {
    title: "Natural-language map requests",
    body: "Turn plain-language planning and proximity prompts into draft GIS map previews.",
  },
  {
    title: "Cabarrus County data scope",
    body: "Live address and parcel workflows currently support Cabarrus County, NC only.",
  },
  {
    title: "Live demo with safe fallback",
    body: "AutoMap tries the live workflow first, with a static demo available only if the backend is warming up.",
  },
];

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
              Open Live Map Composer
            </Link>
            <Link className="button button-secondary" href={demoHref}>
              View Static Demo
            </Link>
            <Link className="button button-secondary" href="/system-status">
              View System Status
            </Link>
          </div>
          <div className="chip-row">
            <StatusChip tone="success">Scope: Cabarrus County, NC</StatusChip>
            <StatusChip tone="success">Live-first workflow</StatusChip>
            <StatusChip tone="success">Real publish disabled</StatusChip>
          </div>
        </div>
      </section>

      <section className="landing-grid landing-card-grid">
        {cards.map((card) => (
          <article className="panel" key={card.title}>
            <h3>{card.title}</h3>
            <p className="muted">{card.body}</p>
          </article>
        ))}
      </section>
    </div>
  );
}
