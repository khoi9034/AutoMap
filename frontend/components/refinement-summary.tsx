"use client";

import type { JsonValue } from "@/types/automap";

type RefinementSummaryProps = {
  changes?: Record<string, JsonValue>;
};

function asList(value: JsonValue | undefined): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item));
}

function SummaryList({ label, values }: { label: string; values: string[] }) {
  return (
    <div className="panel panel-compact">
      <h4>{label}</h4>
      {values.length ? (
        <ul className="review-list">
          {values.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      ) : (
        <p className="muted">None</p>
      )}
    </div>
  );
}

export function RefinementSummary({ changes }: RefinementSummaryProps) {
  return (
    <section className="panel">
      <h3>Refinement summary</h3>
      <div className="stats-grid">
        <SummaryList label="Layers added" values={asList(changes?.layers_added)} />
        <SummaryList label="Layers removed" values={asList(changes?.layers_removed)} />
        <SummaryList label="Filters improved" values={asList(changes?.filters_improved)} />
        <SummaryList label="Warnings resolved" values={asList(changes?.warnings_resolved)} />
        <SummaryList label="Warnings remaining" values={asList(changes?.warnings_remaining)} />
        <SummaryList label="Applied refinements" values={asList(changes?.applied_refinements)} />
      </div>
    </section>
  );
}
