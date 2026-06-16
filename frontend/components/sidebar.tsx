import Link from "next/link";

import { navigationItems } from "@/components/navigation";

export function Sidebar() {
  const grouped = ["Main", "Support"].map((group) => ({
    group,
    items: navigationItems.filter((item) => (item.group || "Main") === group),
  }));

  return (
    <aside className="sidebar">
      <div className="brand-block">
        <div className="brand-mark">AM</div>
        <div>
          <p className="eyebrow">County GIS</p>
          <h1>AutoMap</h1>
        </div>
      </div>
      <nav className="nav-list" aria-label="AutoMap workflow navigation">
        {grouped.map((section) => (
          <div className="nav-section" key={section.group}>
            <p className="nav-section-label">{section.group}</p>
            {section.items.map((item) => (
              <Link key={item.href} href={item.href} className="nav-link">
                {item.label}
              </Link>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
