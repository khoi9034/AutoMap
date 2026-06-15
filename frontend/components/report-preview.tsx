import { WarningPanel } from "@/components/warning-panel";
import type { ReportDetail, ReportFileLink, ReportSummary } from "@/types/automap";

import { API_BASE_URL } from "@/lib/api";
import { StatusChip } from "./status-chip";

type ReportPreviewProps = {
  report: ReportDetail | null;
};

function reportFiles(files: ReportSummary["files"]): ReportFileLink[] {
  if (!files) {
    return [];
  }
  if (Array.isArray(files)) {
    return files;
  }
  return Object.entries(files).map(([name, url]) => ({ name, url }));
}

function backendUrl(url: string | undefined): string {
  if (!url) {
    return "#";
  }
  return url.startsWith("/") ? `${API_BASE_URL}${url}` : url;
}

function percent(value: unknown): string {
  return typeof value === "number" ? `${Math.round(value * 100)}%` : "Not set";
}

export function ReportPreview({ report }: ReportPreviewProps) {
  if (!report?.report_data) {
    return (
      <section className="panel empty-state">
        <h3>No report selected</h3>
        <p>Select a generated report to preview its summary, selected layers, warnings, and export links.</p>
      </section>
    );
  }

  const data = report.report_data;
  const layers = data.selected_layers || [];
  const approval = data.approval || {};
  const files = reportFiles(report.files);

  return (
    <section className="report-preview page-stack">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Report preview</p>
          <h3>{data.generated_map_title || data.report_title}</h3>
          <p className="muted">{data.original_prompt || "No original prompt recorded."}</p>
        </div>
        <div className="chip-row">
          <StatusChip tone="success">Local export</StatusChip>
          <StatusChip tone={data.final_publish_ready ? "success" : "warning"}>
            final_publish_ready: {String(data.final_publish_ready ?? false)}
          </StatusChip>
        </div>
      </div>

      <section className="notice notice-warning">
        <strong>Draft-only report</strong>
        <p>{data.draft_only_disclaimer || "Reports are local exports for review and do not publish to ArcGIS."}</p>
      </section>

      <div className="result-strip">
        <div>
          <span>Workflow</span>
          <strong>{data.workflow_status || "local export"}</strong>
        </div>
        <div>
          <span>Layers</span>
          <strong>{layers.length}</strong>
        </div>
        <div>
          <span>Missing data</span>
          <strong>{data.missing_data?.length || 0}</strong>
        </div>
        <div>
          <span>Dry-run receipt</span>
          <strong>{data.dry_run_publish_receipt ? "present" : "none"}</strong>
        </div>
      </div>

      <section className="panel">
        <h3>Selected layers</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Layer</th>
                <th>Role</th>
                <th>Source</th>
                <th>Confidence</th>
                <th>Definition</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {layers.map((layer) => (
                <tr key={String(layer.layer_key || layer.title || layer.layer_url)}>
                  <td>{String(layer.title || layer.layer_key || "Layer")}</td>
                  <td>{String(layer.role || "")}</td>
                  <td>{String(layer.source_status || "")}</td>
                  <td>{percent(layer.confidence_score)}</td>
                  <td>{String(layer.definition_expression || "None")}</td>
                  <td className="url-cell">{String(layer.layer_url || layer.url || "")}</td>
                </tr>
              ))}
              {!layers.length ? (
                <tr>
                  <td colSpan={6}>No selected layers were recorded.</td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <WarningPanel warnings={data.warnings || {}} missingData={data.missing_data || []} />

      <section className="stats-grid">
        <div className="report-metric">
          <h3>Approval</h3>
          <p>Decision: {String(approval.decision || "not recorded")}</p>
          <p>Final publish ready: {String(data.final_publish_ready ?? false)}</p>
        </div>
        <div className="report-metric">
          <h3>Publish receipts</h3>
          <p>Dry-run publish: {data.dry_run_publish_receipt ? "present" : "none"}</p>
          <p>Portal smoke-test: {data.portal_smoke_test_receipt ? "present" : "none"}</p>
        </div>
      </section>

      <div className="report-link-grid">
        {files.map((file) => (
          <a className="button button-secondary" href={backendUrl(file.url)} key={file.name || file.url} target="_blank" rel="noreferrer">
            Open {file.name || "report file"}
          </a>
        ))}
      </div>
    </section>
  );
}
