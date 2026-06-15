import { StatusChip } from "@/components/status-chip";
import type { AnalysisReportSummary } from "@/types/automap";

type AnalysisReportCardProps = {
  report: AnalysisReportSummary;
  onPreview?: (reportId: string) => void;
};

export function AnalysisReportCard({ report, onPreview }: AnalysisReportCardProps) {
  const data = report.summary_json || {};
  const geometryAvoided = data.geometry_downloaded === false;
  const formats = data.supported_export_formats || ["html", "markdown", "json", "csv"];

  return (
    <article className="panel">
      <div className="panel-title-row">
        <div>
          <h3>{report.report_title || data.report_title || report.report_id}</h3>
          <p className="muted">{report.report_folder || "outputs/analysis_reports"}</p>
        </div>
        <StatusChip tone={geometryAvoided ? "success" : "warning"}>
          {geometryAvoided ? "No geometry download" : "Geometry status review"}
        </StatusChip>
      </div>
      <div className="metric-grid">
        <div>
          <span className="metric-label">Broad count</span>
          <strong>{data.broad_count ?? "n/a"}</strong>
        </div>
        <div>
          <span className="metric-label">Optimized count</span>
          <strong>{data.optimized_count ?? "n/a"}</strong>
        </div>
        <div>
          <span className="metric-label">Safety limit</span>
          <strong>{data.safety_limit ?? "n/a"}</strong>
        </div>
        <div>
          <span className="metric-label">Formats</span>
          <strong>{formats.join(", ")}</strong>
        </div>
      </div>
      {report.report_id && onPreview ? (
        <button className="button button-secondary" type="button" onClick={() => onPreview(report.report_id || "")}>
          Preview Report
        </button>
      ) : null}
    </article>
  );
}
