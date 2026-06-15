import Link from "next/link";

import { navigationItems } from "@/components/navigation";

export function Sidebar() {
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
        {navigationItems.map((item) => (
          <Link key={item.href} href={item.href} className="nav-link">
            {item.label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
