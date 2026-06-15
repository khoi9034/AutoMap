import { AnalysisSummaryTable } from "@/components/analysis-summary-table";
import { StatusChip } from "@/components/status-chip";
import type { AnalysisReportSummary } from "@/types/automap";

type AnalysisReportPreviewProps = {
  report: AnalysisReportSummary | null;
};

export function AnalysisReportPreview({ report }: AnalysisReportPreviewProps) {
  if (!report) {
    return (
      <section className="panel">
        <div className="empty-state compact-empty">
          <h3>No analysis report selected</h3>
          <p>Generate or preview a report to inspect its summary, files, warnings, and grouped statistics.</p>
        </div>
      </section>
    );
  }

  const data = report.summary_json || {};
  const warnings = data.warnings || {};

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>{report.report_title || data.report_title || "Analysis report"}</h3>
          <p className="muted">{data.raw_prompt || report.report_folder}</p>
        </div>
        <StatusChip tone={data.geometry_downloaded ? "warning" : "success"}>
          {data.geometry_downloaded ? "Geometry downloaded" : "Summary-only safe"}
        </StatusChip>
      </div>

      <div className="metric-grid">
        <div>
          <span className="metric-label">Status</span>
          <strong>{data.analysis_status || report.report_status || "unknown"}</strong>
        </div>
        <div>
          <span className="metric-label">Operation</span>
          <strong>{data.operation_type || "analysis"}</strong>
        </div>
        <div>
          <span className="metric-label">Strategy</span>
          <strong>{data.strategy_used || "not recorded"}</strong>
        </div>
        <div>
          <span className="metric-label">Refinement</span>
          <strong>{data.selected_refinement_option || "not applicable"}</strong>
        </div>
      </div>

      <div className="button-row">
        {(report.files || []).map((file) =>
          file.url ? (
            <a className="button button-secondary" href={file.url} target="_blank" rel="noreferrer" key={file.name || file.url}>
              Open {file.name || "file"}
            </a>
          ) : null,
        )}
      </div>

      <h3>Grouped summaries</h3>
      <AnalysisSummaryTable rows={data.grouped_summaries || []} />

      <h3>Warnings and missing data</h3>
      <div className="dashboard-grid">
        {Object.entries(warnings).map(([group, rows]) => (
          <div className="inline-warning" key={group}>
            <strong>{group.replaceAll("_", " ")}</strong>
            <ul className="plain-list">
              {(rows || []).map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
              {!rows?.length ? <li>None</li> : null}
            </ul>
          </div>
        ))}
        <div className="inline-warning">
          <strong>Missing data</strong>
          <ul className="plain-list">
            {(data.missing_data || []).map((item) => (
              <li key={item}>{item}</li>
            ))}
            {!data.missing_data?.length ? <li>None recorded</li> : null}
          </ul>
        </div>
      </div>
    </section>
  );
}
