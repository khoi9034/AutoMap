"use client";

import { API_BASE_URL } from "@/lib/api";
import type { TableExportResponse, TableRecipe } from "@/types/automap";

function fileUrl(path?: string, url?: string): string {
  if (url) return `${API_BASE_URL}${url}`;
  return path ? `${API_BASE_URL}/local-file?path=${encodeURIComponent(path)}` : "#";
}

type Props = {
  recipe: TableRecipe | null;
  exportResult: TableExportResponse | null;
  loading?: boolean;
  onExport: () => void;
};

export function TableExportCard({ recipe, exportResult, loading, onExport }: Props) {
  if (!recipe) return null;
  return (
    <section className="panel">
      <p className="eyebrow">Local export</p>
      <h3>CSV / JSON / Markdown</h3>
      <p className="muted">Exports stay local under ignored outputs/tables and do not include geometry.</p>
      <div className="button-row">
        <button className="button" type="button" onClick={onExport} disabled={loading || !recipe.export_ready}>
          {loading ? "Exporting..." : "Export Table"}
        </button>
      </div>
      {exportResult?.blocked_reasons?.length ? (
        <ul className="compact-list">
          {exportResult.blocked_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      ) : null}
      {exportResult?.files?.length ? (
        <div className="export-link-grid">
          {exportResult.files.map((file) => (
            <a className="export-link" key={`${file.name}-${file.path}`} href={fileUrl(file.path, file.url)} target="_blank" rel="noreferrer">
              <strong>{file.name}</strong>
              <span>{file.path}</span>
            </a>
          ))}
        </div>
      ) : null}
    </section>
  );
}
