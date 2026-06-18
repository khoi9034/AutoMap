"use client";

import { StatusChip } from "@/components/status-chip";
import type { TableRecipe } from "@/types/automap";

export function TableRecipeCard({ recipe }: { recipe: TableRecipe | null }) {
  if (!recipe) return null;
  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Table recipe</p>
          <h3>{recipe.table_title || "AutoMap Table"}</h3>
          <p className="muted">{recipe.table_intent || "table_request"}</p>
        </div>
        <StatusChip tone={recipe.export_ready ? "success" : "warning"}>{recipe.safety_status || "needs_review"}</StatusChip>
      </div>
      <div className="result-strip">
        <div>
          <span>Estimated rows</span>
          <strong>{recipe.estimated_count ?? "Unknown"}</strong>
        </div>
        <div>
          <span>Fields</span>
          <strong>{recipe.selected_fields?.length || 0}</strong>
        </div>
        <div>
          <span>Layers</span>
          <strong>{recipe.source_layers?.length || 0}</strong>
        </div>
      </div>
      <h4>Source layers</h4>
      <ul className="compact-list">
        {(recipe.source_layers || []).map((layer) => (
          <li key={String(layer.layer_key)}>
            <strong>{String(layer.layer_name || layer.layer_key)}</strong>
            <span>{String(layer.source_status || "reference")}</span>
          </li>
        ))}
      </ul>
      <h4>Selected fields</h4>
      <p className="muted">{(recipe.selected_fields || []).map((field) => field.alias || field.name).join(", ") || "No verified fields selected."}</p>
      {recipe.missing_data_needed?.length ? <p className="muted">Missing data: {recipe.missing_data_needed.join(", ")}</p> : null}
    </section>
  );
}
