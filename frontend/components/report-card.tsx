import { API_BASE_URL } from "@/lib/api";
import type { ReportFileLink, ReportSummary } from "@/types/automap";

import { StatusChip } from "./status-chip";

type ReportCardProps = {
  report: ReportSummary;
  onPreview?: (reportId: string) => void;
};

function fileEntries(files: ReportSummary["files"]): ReportFileLink[] {
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

function displayDate(value: string | undefined): string {
  if (!value) {
    return "Not recorded";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ReportCard({ report, onPreview }: ReportCardProps) {
  const files = fileEntries(report.files);
  const valid = report.validation?.is_valid ?? true;

  return (
    <article className="report-card">
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">{report.packet_type || "report"}</p>
          <h3>{report.report_title || report.generated_map_title || report.report_id}</h3>
          <p className="muted">{report.workflow_status || "local export"} - {displayDate(report.updated_at)}</p>
        </div>
        <StatusChip tone={valid ? "success" : "warning"}>{valid ? "valid" : "needs review"}</StatusChip>
      </div>
      <p className="path-text">{report.report_path || report.source_packet_path || report.packet_path}</p>
      <div className="report-link-grid">
        {files.map((file) => (
          <a className="small-button" href={backendUrl(file.url)} key={file.name || file.url} target="_blank" rel="noreferrer">
            {file.name || "report file"}
          </a>
        ))}
        {!files.length ? <span className="muted">No report files listed yet.</span> : null}
      </div>
      {report.report_id && onPreview ? (
        <button className="button button-secondary" type="button" onClick={() => onPreview(report.report_id || "")}>
          Preview Report
        </button>
      ) : null}
    </article>
  );
}
