"use client";

import { useState } from "react";

import { AnalysisReportCard } from "@/components/analysis-report-card";
import { RefinementOptionCard } from "@/components/refinement-option-card";
import { RefinementResultPanel } from "@/components/refinement-result-panel";
import { StatusChip } from "@/components/status-chip";
import {
  createAnalysisRefinement,
  executeAnalysisRefinement,
  generateAnalysisReportFromRefinement,
  selectAnalysisRefinement,
} from "@/lib/api";
import type { AnalysisRefinementOption, AnalysisRefinementSession, AnalysisReportSummary, AnalysisRun } from "@/types/automap";

function firstBlockedReason(result: AnalysisRun): string {
  return result.blocked_reasons?.[0] || "Analysis exceeded safety limits.";
}

export function AnalysisRefinementPanel({ analysisRun }: { analysisRun: AnalysisRun }) {
  const [session, setSession] = useState<AnalysisRefinementSession | null>(null);
  const [selectedOption, setSelectedOption] = useState<AnalysisRefinementOption | null>(null);
  const [report, setReport] = useState<AnalysisReportSummary | null>(null);
  const [paramsJson, setParamsJson] = useState("{}");
  const [loading, setLoading] = useState<"create" | "select" | "execute" | "report" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const blocked = analysisRun.status === "blocked";
  const optimized = analysisRun.analysis_receipt?.optimized_query_plan as Record<string, unknown> | undefined;
  const hasRefinementResult = Boolean(
    session?.refined_result &&
      typeof session.refined_result === "object" &&
      Object.keys(session.refined_result as Record<string, unknown>).length,
  );
  const optimizedCount = Number(optimized?.optimized_candidate_count ?? analysisRun.analysis_receipt?.optimized_candidate_count ?? 0);
  const broadCount = Number(optimized?.broad_count ?? analysisRun.analysis_receipt?.broad_count ?? 0);
  const safetyLimit = Number(
    (optimized?.safety_limits as Record<string, unknown> | undefined)?.max_download_features_per_layer ??
      (analysisRun.analysis_receipt?.max_feature_limits as Record<string, unknown> | undefined)?.run_max_features ??
      2000,
  );

  async function onCreate() {
    if (!analysisRun.analysis_run_id) {
      setError("Analysis run id is missing.");
      return;
    }
    setError(null);
    setLoading("create");
    try {
      const response = await createAnalysisRefinement(analysisRun.analysis_run_id);
      setSession(response.refinement_session);
      const recommended = response.refinement_session.options?.find((option) => option.recommended);
      if (recommended) {
        setSelectedOption(recommended);
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to create refinement options.");
    } finally {
      setLoading(null);
    }
  }

  async function onSelect() {
    if (!session?.session_id || !selectedOption?.option_id) {
      setError("Choose a refinement option first.");
      return;
    }
    let parameters: Record<string, unknown>;
    try {
      parameters = JSON.parse(paramsJson) as Record<string, unknown>;
    } catch {
      setError("Parameters must be valid JSON.");
      return;
    }
    setError(null);
    setLoading("select");
    try {
      const response = await selectAnalysisRefinement(session.session_id, selectedOption.option_id, parameters);
      setSession(response.refinement_session);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to select refinement option.");
    } finally {
      setLoading(null);
    }
  }

  async function onExecute() {
    if (!session?.session_id) {
      setError("Create and select a refinement session first.");
      return;
    }
    setError(null);
    setLoading("execute");
    try {
      const response = await executeAnalysisRefinement(session.session_id);
      setSession(response.refinement_session);
      setReport(null);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to execute refinement.");
    } finally {
      setLoading(null);
    }
  }

  async function onGenerateReport() {
    if (!session?.session_id) {
      setError("Create and execute a refinement session first.");
      return;
    }
    setError(null);
    setLoading("report");
    try {
      setReport(await generateAnalysisReportFromRefinement(session.session_id));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to generate analysis report.");
    } finally {
      setLoading(null);
    }
  }

  if (!blocked) {
    return null;
  }

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Refine Analysis</h3>
          <p className="muted">
            Blocked analysis is not a failure. AutoMap can guide a safer summary, batch, filter, or smaller-area path.
          </p>
        </div>
        <StatusChip tone="warning">Blocked count exceeds limit</StatusChip>
      </div>

      <div className="metric-grid">
        <div>
          <span className="metric-label">Broad count</span>
          <strong>{broadCount ? broadCount.toLocaleString() : "n/a"}</strong>
        </div>
        <div>
          <span className="metric-label">Optimized count</span>
          <strong>{optimizedCount ? optimizedCount.toLocaleString() : "n/a"}</strong>
        </div>
        <div>
          <span className="metric-label">Safety limit</span>
          <strong>{safetyLimit.toLocaleString()}</strong>
        </div>
      </div>

      <div className="inline-warning">
        <strong>Block reason</strong>
        <p>{firstBlockedReason(analysisRun)}</p>
      </div>

      {!session ? (
        <button className="button" type="button" onClick={onCreate} disabled={loading !== null}>
          {loading === "create" ? "Creating options..." : "Create Refinement Options"}
        </button>
      ) : (
        <div className="page-stack">
          <div className="dashboard-grid">
            {session.options?.map((option) => (
              <RefinementOptionCard
                key={option.option_id}
                option={option}
                selected={selectedOption?.option_id === option.option_id}
                onSelect={setSelectedOption}
              />
            ))}
          </div>

          <div className="prompt-box">
            <label htmlFor="refinement-params">Parameters JSON</label>
            <textarea
              id="refinement-params"
              value={paramsJson}
              onChange={(event) => setParamsJson(event.target.value)}
              aria-label="Refinement parameters JSON"
            />
            <div className="button-row">
              <button className="button button-secondary" type="button" onClick={onSelect} disabled={loading !== null}>
                {loading === "select" ? "Selecting..." : `Select ${selectedOption?.option_id || "option"}`}
              </button>
              <button className="button" type="button" onClick={onExecute} disabled={loading !== null}>
                {loading === "execute" ? "Executing..." : "Execute Refinement"}
              </button>
            </div>
          </div>

          <RefinementResultPanel session={session} />
          {hasRefinementResult ? (
            <div className="button-row">
              <button className="button button-secondary" type="button" onClick={onGenerateReport} disabled={loading !== null}>
                {loading === "report" ? "Generating report..." : "Generate Analysis Report"}
              </button>
            </div>
          ) : null}
          {report ? <AnalysisReportCard report={report} /> : null}
        </div>
      )}

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Refinement error</strong>
          <p>{error}</p>
        </div>
      ) : null}
    </section>
  );
}
