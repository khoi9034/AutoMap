"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { samplePrompts } from "@/components/navigation";
import { StatusChip } from "@/components/status-chip";
import { API_BASE_URL, executeAnalysis, listAnalysisRuns, planAnalysis } from "@/lib/api";
import { loadWorkflowState, mergeWorkflowState } from "@/lib/workflow-store";
import type { AnalysisRun } from "@/types/automap";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function localFileHref(pathOrUrl: unknown): string {
  if (typeof pathOrUrl !== "string" || !pathOrUrl) {
    return "";
  }
  if (pathOrUrl.startsWith("http")) {
    return pathOrUrl;
  }
  if (pathOrUrl.startsWith("/")) {
    return `${API_BASE_URL}${pathOrUrl}`;
  }
  return `${API_BASE_URL}/local-file?path=${encodeURIComponent(pathOrUrl)}`;
}

function runTitle(run: AnalysisRun): string {
  return `${run.operation_type || "analysis"} - ${run.status || "unknown"}`;
}

export function AnalysisClient() {
  const workflow = useMemo(() => loadWorkflowState(), []);
  const [prompt, setPrompt] = useState(
    workflow.rawPrompt || "Show parcels in Concord that are in the 100-year floodplain.",
  );
  const [plan, setPlan] = useState<Record<string, unknown> | null>(
    workflow.analysisPlan ? asRecord(workflow.analysisPlan) : null,
  );
  const [result, setResult] = useState<AnalysisRun | null>(
    workflow.analysisRun ? (asRecord(workflow.analysisRun) as AnalysisRun) : null,
  );
  const [runs, setRuns] = useState<AnalysisRun[]>([]);
  const [loading, setLoading] = useState<"plan" | "execute" | "runs" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading("runs");
    listAnalysisRuns()
      .then((response) => setRuns(response.analysis_runs || []))
      .catch(() => setRuns([]))
      .finally(() => setLoading(null));
  }, []);

  const executable = Boolean(plan?.executable);
  const blockedReasons = (plan?.blocked_reasons as string[] | undefined) || [];
  const outputLink = localFileHref(result?.output_geojson_path || asRecord(result?.derived_layer).url);

  async function onPlan() {
    setError(null);
    setLoading("plan");
    try {
      const response = await planAnalysis(prompt);
      setPlan(response.analysis_plan);
      mergeWorkflowState({
        rawPrompt: prompt,
        analysisPlan: response.analysis_plan,
        activeStep: "analysis",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis planning failed.");
    } finally {
      setLoading(null);
    }
  }

  async function onExecute() {
    setError(null);
    setLoading("execute");
    try {
      const response = await executeAnalysis(prompt);
      setResult(response.analysis_result);
      mergeWorkflowState({
        rawPrompt: prompt,
        analysisRun: response.analysis_result as Record<string, unknown>,
        activeStep: "analysis",
      });
      const refreshed = await listAnalysisRuns();
      setRuns(refreshed.analysis_runs || []);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis execution failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Safe local analysis only</strong>
        <p>
          AutoMap counts first, blocks oversized requests, writes local GeoJSON outputs, and does not publish or upload
          derived results.
        </p>
      </section>

      <section className="panel prompt-box">
        <div className="panel-title-row">
          <div>
            <h3>Analysis request</h3>
            <p className="muted">v2.0 fully supports parcel selection by bounded flood/geography intersection.</p>
          </div>
          <div className="chip-row">
            <StatusChip tone="success">No Portal login</StatusChip>
            <StatusChip tone="success">No real publish</StatusChip>
          </div>
        </div>
        <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} aria-label="Analysis prompt" />
        <div className="sample-row">
          {samplePrompts.slice(0, 4).map((sample) => (
            <button className="pill-button" type="button" key={sample} onClick={() => setPrompt(sample)}>
              {sample}
            </button>
          ))}
        </div>
        <div className="button-row">
          <button className="button" type="button" onClick={onPlan} disabled={loading !== null || !prompt.trim()}>
            {loading === "plan" ? "Planning..." : "Plan Analysis"}
          </button>
          <button
            className="button button-secondary"
            type="button"
            onClick={onExecute}
            disabled={loading !== null || !prompt.trim() || (plan !== null && !executable)}
          >
            {loading === "execute" ? "Executing..." : "Execute Analysis"}
          </button>
        </div>
        {error ? (
          <div className="inline-error" role="alert">
            <strong>Analysis error</strong>
            <p>{error}</p>
          </div>
        ) : null}
      </section>

      {plan ? (
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <h3>Feasibility</h3>
              <p className="muted">{String(plan.operation_type || "unsupported_operation")}</p>
            </div>
            <StatusChip tone={executable ? "success" : "warning"}>
              {executable ? "Executable" : "Blocked / review needed"}
            </StatusChip>
          </div>
          {blockedReasons.length ? (
            <ul className="warning-list">
              {blockedReasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
          <div className="metric-grid">
            <div>
              <span className="metric-label">Max features</span>
              <strong>{String(plan.max_features || "2000")}</strong>
            </div>
            <div>
              <span className="metric-label">Hard max</span>
              <strong>{String(plan.hard_max_features || "5000")}</strong>
            </div>
            <div>
              <span className="metric-label">Steps</span>
              <strong>{((plan.recommended_execution_plan as string[] | undefined) || []).length}</strong>
            </div>
          </div>
          <ol className="plain-list">
            {((plan.recommended_execution_plan as string[] | undefined) || []).map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </section>
      ) : null}

      {result ? (
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <h3>Execution result</h3>
              <p className="muted">{result.analysis_run_id || "analysis run"}</p>
            </div>
            <StatusChip tone={result.status === "completed" ? "success" : "warning"}>
              {result.status || "unknown"}
            </StatusChip>
          </div>
          <div className="metric-grid">
            <div>
              <span className="metric-label">Output count</span>
              <strong>{result.output_count ?? 0}</strong>
            </div>
            <div>
              <span className="metric-label">Operation</span>
              <strong>{result.operation_type || "analysis"}</strong>
            </div>
            <div>
              <span className="metric-label">GeoJSON</span>
              {outputLink ? (
                <a className="text-link" href={outputLink} target="_blank" rel="noreferrer">
                  Open output
                </a>
              ) : (
                <strong>not generated</strong>
              )}
            </div>
          </div>
          <div className="button-row">
            <Link className="button button-secondary" href="/map-preview">
              Add result to map preview
            </Link>
          </div>
        </section>
      ) : null}

      <section className="dashboard-grid">
        <JsonPanel title="Analysis plan JSON" value={plan || { status: "not planned" }} />
        <JsonPanel title="Analysis receipt JSON" value={result?.analysis_receipt || { status: "not executed" }} />
      </section>

      <section className="panel">
        <div className="panel-title-row">
          <h3>Recent analysis runs</h3>
          <StatusChip tone="success">Local outputs</StatusChip>
        </div>
        {runs.length ? (
          <div className="mini-list">
            {runs.slice(0, 8).map((run) => (
              <div key={run.analysis_run_id}>
                <strong>{runTitle(run)}</strong>
                <span>{run.analysis_run_id} - output {run.output_count ?? 0}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state compact-empty">
            <h3>No analysis runs yet</h3>
            <p>Plan or execute a supported request to populate the local analysis history.</p>
          </div>
        )}
      </section>
    </div>
  );
}
