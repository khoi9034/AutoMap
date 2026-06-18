import type { ReactNode } from "react";

export function ExhibitMapFrame({ children }: { children: ReactNode }) {
  return (
    <section className="exhibit-map-frame" aria-label="GIS exhibit map frame">
      {children}
    </section>
  );
}
