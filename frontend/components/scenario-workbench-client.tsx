"use client";

import { useEffect, useState } from "react";

import { ScenarioComparisonTable } from "@/components/scenario-comparison-table";
import { ScenarioToRecipePanel } from "@/components/scenario-to-recipe-panel";
import { ScenarioVariantCard } from "@/components/scenario-variant-card";
import { ScenarioWeightEditor } from "@/components/scenario-weight-editor";
import { StatusChip } from "@/components/status-chip";
import { compareScenarios, listScenarioVariants, listScenarios } from "@/lib/api";
import type { PlanningScenario, ScenarioComparison, ScenarioToRecipeResult, ScenarioVariant } from "@/types/automap";

export function ScenarioWorkbenchClient() {
  const [scenarios, setScenarios] = useState<PlanningScenario[]>([]);
  const [scenario, setScenario] = useState<PlanningScenario | null>(null);
  const [variants, setVariants] = useState<ScenarioVariant[]>([]);
  const [activeVariant, setActiveVariant] = useState<ScenarioVariant | null>(null);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [recipeResult, setRecipeResult] = useState<ScenarioToRecipeResult | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refreshScenarios() {
    const response = await listScenarios();
    const rows = response.scenarios || [];
    setScenarios(rows);
    if (!scenario && rows.length) {
      const selected = (rows[0].scenario_json as PlanningScenario | undefined) || rows[0];
      setScenario(selected);
    }
  }

  async function refreshVariants(selectedScenario = scenario) {
    if (!selectedScenario?.scenario_id) {
      setVariants([]);
      return;
    }
    const response = await listScenarioVariants(selectedScenario.scenario_id);
    const rows = (response.variants || []).map((item) => (item.variant_json as ScenarioVariant | undefined) || item);
    setVariants(rows);
    if (!activeVariant && rows.length) {
      setActiveVariant(rows[0]);
    }
  }

  useEffect(() => {
    refreshScenarios().catch(() => setError("Could not load scenarios from the backend."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    refreshVariants().catch(() => setError("Could not load variants for the selected scenario."));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenario?.scenario_id]);

  function selectScenario(item: PlanningScenario) {
    const full = (item.scenario_json as PlanningScenario | undefined) || item;
    setScenario(full);
    setActiveVariant(null);
    setComparison(null);
    setRecipeResult(null);
  }

  async function compareCurrent() {
    if (!scenario?.scenario_id || variants.length < 1) {
      setError("Select a scenario with at least one variant before comparing.");
      return;
    }
    setLoading("compare");
    setError(null);
    try {
      const selectedVariantIds = variants.slice(0, 2).map((variant) => String(variant.variant_id));
      const response = await compareScenarios({
        scenario_ids: [scenario.scenario_id],
        variant_ids: selectedVariantIds,
      });
      setComparison(response);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Comparison failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Scenario scores are planning-support drafts, not official recommendations.</strong>
        <p>
          Proxy sources are context only unless reviewed. Missing official permit data remains unresolved. No geometry
          scoring is executed unless analysis safety allows it.
        </p>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Open scenario</h3>
                <p className="muted">Choose an existing planning scenario to tune in the workbench.</p>
              </div>
              <StatusChip>{scenarios.length} scenarios</StatusChip>
            </div>
            <div className="sample-grid">
              {scenarios.slice(0, 8).map((item) => (
                <button className="sample-card" type="button" key={item.scenario_id} onClick={() => selectScenario(item)}>
                  {item.scenario_title || item.scenario_id}
                </button>
              ))}
              {!scenarios.length ? <p className="muted">No scenarios are stored yet. Create one on the Scenarios page.</p> : null}
            </div>
          </section>

          <ScenarioWeightEditor
            scenario={scenario}
            onVariantCreated={(variant) => {
              setActiveVariant(variant);
              void refreshVariants(scenario);
            }}
          />

          <ScenarioComparisonTable comparison={comparison} />
          <ScenarioToRecipePanel scenario={scenario} variant={activeVariant} onRecipeCreated={setRecipeResult} />
        </div>

        <aside className="dashboard-side">
          <section className="panel">
            <h3>Active scenario</h3>
            {scenario ? (
              <div className="stat-list">
                <div>
                  <span>Title</span>
                  <strong>{scenario.scenario_title}</strong>
                </div>
                <div>
                  <span>Type</span>
                  <strong>{scenario.scenario_type}</strong>
                </div>
                <div>
                  <span>Missing data</span>
                  <strong>{(scenario.missing_data || []).join(", ") || "None recorded"}</strong>
                </div>
              </div>
            ) : (
              <p className="muted">Select a scenario to begin.</p>
            )}
          </section>

          <section className="panel">
            <div className="panel-title-row">
              <h3>Variants</h3>
              <button className="small-button" type="button" onClick={compareCurrent} disabled={loading === "compare" || variants.length < 1}>
                {loading === "compare" ? "Comparing..." : "Compare"}
              </button>
            </div>
            <div className="mini-list">
              {variants.map((variant) => (
                <button className="small-button" type="button" key={variant.variant_id} onClick={() => setActiveVariant(variant)}>
                  {variant.variant_name || variant.variant_id}
                </button>
              ))}
              {!variants.length ? <p className="muted">No variants yet.</p> : null}
            </div>
          </section>

          <ScenarioVariantCard variant={activeVariant} />

          {recipeResult?.recipe ? (
            <section className="panel">
              <h3>Converted recipe</h3>
              <p className="muted">{recipeResult.recipe.map_title}</p>
              <StatusChip tone="warning">Needs review</StatusChip>
            </section>
          ) : null}
        </aside>
      </section>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Scenario workbench issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
    </div>
  );
}
