"use client";

import type { TableRecipe } from "@/types/automap";

export function TableSafetyWarning({ recipe }: { recipe: TableRecipe | null }) {
  if (!recipe) return null;
  const blocked = recipe.blocked_reasons || [];
  const suggestions = recipe.refinement_suggestions || [];
  if (recipe.export_ready && !blocked.length) {
    return (
      <section className="notice notice-success">
        <strong>Export ready</strong>
        <p>Estimated rows are within AutoMap table safety limits. Exports use returnGeometry=false.</p>
      </section>
    );
  }
  return (
    <section className="notice notice-warning">
      <strong>Export needs review</strong>
      <p>{recipe.safety_status || "AutoMap needs a narrower table request before exporting."}</p>
      {blocked.length ? (
        <ul className="compact-list">
          {blocked.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
      {suggestions.length ? <p className="muted">Try: {suggestions.slice(0, 3).join(" ")}</p> : null}
    </section>
  );
}
