"use client";

import { API_BASE_URL } from "@/lib/api";
import { StatusChip } from "@/components/status-chip";
import type { AnalysisRefinementSession } from "@/types/automap";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function fileHref(pathOrUrl: unknown): string {
  if (typeof pathOrUrl !== "string" || !pathOrUrl) {
    return "";
  }
  if (pathOrUrl.startsWith("http")) {
    return pathOrUrl;
  }
  return `${API_BASE_URL}/local-file?path=${encodeURIComponent(pathOrUrl)}`;
}

export function RefinementResultPanel({ session }: { session: AnalysisRefinementSession }) {
  const result = asRecord(session.refined_result);
  const summary = asRecord(result.summary);
  const batchPlan = asRecord(result.batch_plan);
  const files = asRecord(result.files);
  const outputFolder = typeof result.output_folder === "string" ? result.output_folder : "";
  const geometryDownloaded = Boolean(summary.geometry_downloaded || batchPlan.geometry_downloaded || result.geometry_downloaded);

  if (!Object.keys(result).length) {
    return (
      <div className="empty-state compact-empty">
        <h3>No refinement result yet</h3>
        <p>Select and execute a supported refinement option to create local refinement outputs.</p>
      </div>
    );
  }

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Refinement result</h3>
          <p className="muted">{outputFolder || "local refinement output"}</p>
        </div>
        <StatusChip tone={geometryDownloaded ? "warning" : "success"}>
          {geometryDownloaded ? "Geometry downloaded" : "No geometry download"}
        </StatusChip>
      </div>
      <div className="metric-grid">
        <div>
          <span className="metric-label">Mode</span>
          <strong>{String(result.mode || "refinement")}</strong>
        </div>
        <div>
          <span className="metric-label">Status</span>
          <strong>{String(result.status || session.status || "unknown")}</strong>
        </div>
        <div>
          <span className="metric-label">Optimized count</span>
          <strong>{String(summary.optimized_count ?? session.optimized_count ?? "n/a")}</strong>
        </div>
      </div>
      {Object.keys(files).length ? (
        <div className="button-row">
          {Object.entries(files).map(([label, path]) =>
            typeof path === "string" ? (
              <a className="button button-secondary" href={fileHref(path)} target="_blank" rel="noreferrer" key={label}>
                Open {label.replaceAll("_", " ")}
              </a>
            ) : null,
          )}
        </div>
      ) : null}
    </section>
  );
}
