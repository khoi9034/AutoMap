"use client";

import { useEffect, useState } from "react";

import { ScenarioFactorTable } from "@/components/scenario-factor-table";
import { ScenarioReviewQuestions } from "@/components/scenario-review-questions";
import { ScenarioScorecard } from "@/components/scenario-scorecard";
import { ScenarioSourceCoverage } from "@/components/scenario-source-coverage";
import { ScenarioToRecipePanel } from "@/components/scenario-to-recipe-panel";
import { ScenarioVariantCard } from "@/components/scenario-variant-card";
import { ScenarioWeightEditor } from "@/components/scenario-weight-editor";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { generateScenarioReport, listScenarios, makeScenario, scenarioToRecipe } from "@/lib/api";
import type { MapRecipe, PlanningScenario, ScenarioReport, ScenarioVariant } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

const SAMPLE_SCENARIOS = [
  "Map commercial growth opportunities near high traffic roads but avoid floodplain.",
  "Show development pressure near schools and flood zones in Concord.",
  "Find areas suitable for residential growth but avoid flood risk.",
  "Show planned road projects near development pressure areas.",
];

export function ScenarioBuilder() {
  const [prompt, setPrompt] = useState(SAMPLE_SCENARIOS[0]);
  const [scenario, setScenario] = useState<PlanningScenario | null>(null);
  const [scenarios, setScenarios] = useState<PlanningScenario[]>([]);
  const [report, setReport] = useState<ScenarioReport | null>(null);
  const [recipe, setRecipe] = useState<MapRecipe | null>(null);
  const [variant, setVariant] = useState<ScenarioVariant | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  async function refreshScenarios() {
    const response = await listScenarios();
    setScenarios(response.scenarios || []);
  }

  useEffect(() => {
    refreshScenarios().catch(() => {
      // Keep page usable when backend is offline.
    });
  }, []);

  async function generateScenario(selectedPrompt = prompt) {
    if (!selectedPrompt.trim()) {
      setToast({ tone: "warning", message: "Enter a scenario prompt first." });
      return;
    }
    setLoading("scenario");
    setError(null);
    setReport(null);
    setRecipe(null);
    try {
      const response = await makeScenario(selectedPrompt);
      setScenario(response.scenario);
      setVariant(null);
      await refreshScenarios();
      setToast({ tone: "success", message: "Scenario framework generated." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Scenario generation failed.");
      setToast({ tone: "danger", message: "Scenario generation failed." });
    } finally {
      setLoading(null);
    }
  }

  async function buildRecipeFromScenario() {
    if (!scenario?.scenario_id) {
      setError("Generate or select a scenario first.");
      return;
    }
    setLoading("recipe");
    setError(null);
    try {
      const response = await scenarioToRecipe(scenario.scenario_id, variant?.variant_id);
      setRecipe(response.recipe || null);
      setToast({ tone: "success", message: "Draft map recipe generated from scenario workbench context." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Recipe generation failed.");
    } finally {
      setLoading(null);
    }
  }

  async function buildScenarioReport() {
    if (!scenario?.scenario_id) {
      setToast({ tone: "warning", message: "Generate or select a scenario first." });
      return;
    }
    setLoading("report");
    setError(null);
    try {
      const generated = await generateScenarioReport(scenario.scenario_id);
      setReport(generated);
      setToast({ tone: "success", message: "Scenario report generated under outputs/scenario_reports." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Scenario report generation failed.");
      setToast({ tone: "danger", message: "Scenario report generation failed." });
    } finally {
      setLoading(null);
    }
  }

  function selectStoredScenario(item: PlanningScenario) {
    const full = (item.scenario_json as PlanningScenario | undefined) || item;
    setScenario(full);
    setPrompt(full.raw_prompt || prompt);
    setReport(null);
    setRecipe(null);
    setVariant(null);
  }

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Planning framework only</strong>
        <p>
          Scenarios are transparent local review frameworks. Suitability scores are not official recommendations, and no
          parcel scoring runs unless a separate bounded analysis passes safety checks.
        </p>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Scenario prompt</h3>
                <p className="muted">Describe a growth, suitability, constraint, or transportation planning question.</p>
              </div>
              <StatusChip tone="warning">Draft only</StatusChip>
            </div>
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={5} />
            <div className="button-row">
              <button className="button" type="button" onClick={() => generateScenario()} disabled={loading === "scenario"}>
                {loading === "scenario" ? "Generating..." : "Generate Scenario"}
              </button>
              <button className="button button-secondary" type="button" onClick={buildRecipeFromScenario} disabled={!scenario || loading === "recipe"}>
                {loading === "recipe" ? "Creating..." : "Create Map Recipe"}
              </button>
              <button className="button button-secondary" type="button" onClick={buildScenarioReport} disabled={!scenario || loading === "report"}>
                {loading === "report" ? "Generating..." : "Generate Scenario Report"}
              </button>
              <a className="button button-secondary" href="/scenario-workbench">
                Open Workbench
              </a>
            </div>
            <div className="sample-grid">
              {SAMPLE_SCENARIOS.map((sample) => (
                <button
                  className="sample-card"
                  type="button"
                  key={sample}
                  onClick={() => {
                    setPrompt(sample);
                    void generateScenario(sample);
                  }}
                >
                  {sample}
                </button>
              ))}
            </div>
          </section>

          {scenario ? (
            <section className="panel">
              <div className="panel-title-row">
                <div>
                  <h3>{scenario.scenario_title}</h3>
                  <p className="muted">{scenario.planning_goal}</p>
                </div>
                <StatusChip>{scenario.status || "draft"}</StatusChip>
              </div>
              <p>{scenario.official_use_disclaimer}</p>
              <div className="stat-grid">
                <div>
                  <span>Positive factors</span>
                  <strong>{scenario.positive_factors?.length || 0}</strong>
                </div>
                <div>
                  <span>Negative factors</span>
                  <strong>{scenario.negative_factors?.length || 0}</strong>
                </div>
                <div>
                  <span>Source warnings</span>
                  <strong>{scenario.source_coverage?.warnings?.length || 0}</strong>
                </div>
              </div>
            </section>
          ) : null}

          <ScenarioFactorTable factors={scenario?.scoring_framework || []} />
          <ScenarioWeightEditor
            scenario={scenario}
            onVariantCreated={(created) => {
              setVariant(created);
              setToast({ tone: "success", message: "Scenario variant saved." });
            }}
          />
          <ScenarioReviewQuestions questions={scenario?.review_questions || []} assumptions={scenario?.assumptions || []} />
          <ScenarioSourceCoverage scenario={scenario} />
          <ScenarioToRecipePanel
            scenario={scenario}
            variant={variant}
            onRecipeCreated={(result) => setRecipe(result.recipe || null)}
          />
        </div>

        <aside className="dashboard-side">
          <ScenarioScorecard scenario={scenario} />
          <ScenarioVariantCard variant={variant} />
          <section className="panel">
            <h3>Latest scenarios</h3>
            <div className="mini-list">
              {scenarios.slice(0, 8).map((item) => (
                <button className="small-button" type="button" key={item.scenario_id} onClick={() => selectStoredScenario(item)}>
                  {item.scenario_title || item.scenario_id}
                </button>
              ))}
              {!scenarios.length ? <p className="muted">No stored scenarios yet.</p> : null}
            </div>
          </section>
          {report ? (
            <section className="panel">
              <h3>Scenario report</h3>
              <p className="muted">{report.report_folder}</p>
              <div className="mini-list">
                {(report.files || []).map((file) => (
                  <a key={file.path || file.name} href={file.url || "#"} target="_blank" rel="noreferrer">
                    {file.name}
                  </a>
                ))}
              </div>
            </section>
          ) : null}
          {recipe ? (
            <section className="panel">
              <h3>Draft recipe created</h3>
              <p className="muted">{recipe.map_title}</p>
              <StatusChip tone={recipe.needs_review ? "warning" : "success"}>{recipe.needs_review ? "Needs review" : "Ready for review"}</StatusChip>
            </section>
          ) : null}
        </aside>
      </section>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Scenario issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
      <ToastMessage toast={toast} />
    </div>
  );
}
