"use client";

import { useEffect, useState } from "react";

import { AnalysisReportCard } from "@/components/analysis-report-card";
import { AnalysisReportPreview } from "@/components/analysis-report-preview";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import {
  generateAnalysisReport,
  generateAnalysisReportFromRefinement,
  getAnalysisReport,
  listAnalysisRefinements,
  listAnalysisReports,
  listAnalysisRuns,
} from "@/lib/api";
import type { AnalysisRefinementSession, AnalysisReportSummary, AnalysisRun } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

function displayCount(value: unknown): string {
  return typeof value === "number" ? value.toLocaleString() : String(value ?? "n/a");
}

export function AnalysisReportsClient() {
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [refinements, setRefinements] = useState<AnalysisRefinementSession[]>([]);
  const [reports, setReports] = useState<AnalysisReportSummary[]>([]);
  const [selectedReport, setSelectedReport] = useState<AnalysisReportSummary | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  async function refreshReports() {
    const response = await listAnalysisReports();
    setReports(response.analysis_reports || []);
  }

  useEffect(() => {
    Promise.all([listAnalysisRuns(), listAnalysisRefinements(), listAnalysisReports()])
      .then(([runResponse, refinementResponse, reportResponse]) => {
        setRuns(runResponse.analysis_runs || []);
        setRefinements(refinementResponse.refinement_sessions || []);
        setReports(reportResponse.analysis_reports || []);
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Analysis Reports failed to load."));
  }, []);

  async function previewReport(reportId: string) {
    if (!reportId) {
      return;
    }
    setLoading(reportId);
    setError(null);
    try {
      setSelectedReport(await getAnalysisReport(reportId));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Report preview failed.");
    } finally {
      setLoading(null);
    }
  }

  async function generateFromRun(runId: string | undefined) {
    if (!runId) {
      setToast({ tone: "warning", message: "Analysis run id is missing." });
      return;
    }
    setLoading(runId);
    setError(null);
    try {
      const generated = await generateAnalysisReport(runId);
      await refreshReports();
      setSelectedReport(generated);
      setToast({ tone: "success", message: "Analysis report generated under outputs/analysis_reports." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis report generation failed.");
      setToast({ tone: "danger", message: "Analysis report generation failed." });
    } finally {
      setLoading(null);
    }
  }

  async function generateFromRefinement(sessionId: string | undefined) {
    if (!sessionId) {
      setToast({ tone: "warning", message: "Refinement session id is missing." });
      return;
    }
    setLoading(sessionId);
    setError(null);
    try {
      const generated = await generateAnalysisReportFromRefinement(sessionId);
      await refreshReports();
      setSelectedReport(generated);
      setToast({ tone: "success", message: "Analysis report generated under outputs/analysis_reports." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis report generation failed.");
      setToast({ tone: "danger", message: "Analysis report generation failed." });
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Summary reports only</strong>
        <p>
          v2.3 reports use analysis receipts and safe count/statistics queries with returnGeometry=false. They do not
          publish, upload, or create official GIS layers.
        </p>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Latest analysis runs</h3>
                <p className="muted">Generate a report from a stored analysis run or blocked result.</p>
              </div>
              <StatusChip>{runs.length} runs</StatusChip>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Run</th>
                    <th>Status</th>
                    <th>Output</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.slice(0, 8).map((run) => (
                    <tr key={run.analysis_run_id}>
                      <td>
                        <strong>{run.analysis_run_id}</strong>
                        <p className="path-text">{run.raw_prompt}</p>
                      </td>
                      <td>{run.status || "unknown"}</td>
                      <td>{displayCount(run.output_count)}</td>
                      <td>
                        <button
                          className="button button-secondary"
                          type="button"
                          onClick={() => generateFromRun(run.analysis_run_id)}
                          disabled={loading === run.analysis_run_id}
                        >
                          {loading === run.analysis_run_id ? "Generating..." : "Generate Report"}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!runs.length ? (
                    <tr>
                      <td colSpan={4}>No analysis runs found.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Latest refinement sessions</h3>
                <p className="muted">Summary-only refinements are ideal candidates for v2.3 reports.</p>
              </div>
              <StatusChip>{refinements.length} refinements</StatusChip>
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Session</th>
                    <th>Selected option</th>
                    <th>Optimized count</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {refinements.slice(0, 8).map((session) => (
                    <tr key={session.session_id}>
                      <td>
                        <strong>{session.session_id}</strong>
                        <p className="path-text">{session.raw_prompt}</p>
                      </td>
                      <td>{String((session.selected_option as Record<string, unknown> | undefined)?.option_id || "not selected")}</td>
                      <td>{displayCount(session.optimized_count)}</td>
                      <td>
                        <button
                          className="button button-secondary"
                          type="button"
                          onClick={() => generateFromRefinement(session.session_id)}
                          disabled={loading === session.session_id}
                        >
                          {loading === session.session_id ? "Generating..." : "Generate Report"}
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!refinements.length ? (
                    <tr>
                      <td colSpan={4}>No refinement sessions found.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <aside className="dashboard-side">
          <section className="panel safety-card">
            <h3>Supported v2.3 formats</h3>
            <ul className="check-list">
              <li>HTML report</li>
              <li>Markdown report</li>
              <li>JSON report data</li>
              <li>JSON summary tables</li>
              <li>CSV layer summary</li>
              <li>JSON warning summary</li>
            </ul>
            <p className="muted">PDF is intentionally skipped until a reliable local export path is added.</p>
          </section>
          <section className="panel">
            <h3>Latest generated reports</h3>
            <div className="mini-list">
              {reports.slice(0, 6).map((report) => (
                <div key={report.report_id}>
                  <strong>{report.report_title || report.report_id}</strong>
                  <button className="small-button" type="button" onClick={() => previewReport(report.report_id || "")}>
                    Preview
                  </button>
                </div>
              ))}
              {!reports.length ? <p className="muted">No analysis reports generated yet.</p> : null}
            </div>
          </section>
        </aside>
      </section>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Analysis Reports issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
      <ToastMessage toast={toast} />

      <section className="report-grid">
        {reports.slice(0, 6).map((report) => (
          <AnalysisReportCard report={report} onPreview={previewReport} key={report.report_id} />
        ))}
      </section>

      <AnalysisReportPreview report={selectedReport} />
    </div>
  );
}
