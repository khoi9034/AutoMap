"use client";

import type { TableRecipe } from "@/types/automap";

export function TablePreviewGrid({ recipe }: { recipe: TableRecipe | null }) {
  const rows = recipe?.preview_rows || [];
  const fields = (recipe?.selected_fields || []).map((field) => field.name).filter(Boolean) as string[];
  if (!recipe) return null;
  return (
    <section className="panel">
      <p className="eyebrow">Preview rows</p>
      <h3>returnGeometry=false preview</h3>
      {rows.length ? (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                {fields.map((field) => (
                  <th key={field}>{field}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={`preview-${index}`}>
                  {fields.map((field) => (
                    <td key={field}>{String(row[field] ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No preview rows are available yet. AutoMap still selected fields and safety limits without downloading geometry.</p>
      )}
    </section>
  );
}
