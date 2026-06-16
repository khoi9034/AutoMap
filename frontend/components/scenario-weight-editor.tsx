"use client";

import { useEffect, useMemo, useState } from "react";

import { createScenarioVariant } from "@/lib/api";
import type { PlanningScenario, ScenarioVariant } from "@/types/automap";

type ScenarioWeightEditorProps = {
  scenario?: PlanningScenario | null;
  onVariantCreated?: (variant: ScenarioVariant) => void;
};

function factorKey(value: unknown): string {
  return String(value || "");
}

export function ScenarioWeightEditor({ scenario, onVariantCreated }: ScenarioWeightEditorProps) {
  const factors = useMemo(() => scenario?.scoring_framework || [], [scenario]);
  const [variantName, setVariantName] = useState("Road access priority");
  const [assumptions, setAssumptions] = useState("Weights are draft review assumptions.\nProxy layers remain context only.");
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [enabled, setEnabled] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const nextWeights: Record<string, number> = {};
    const nextEnabled: Record<string, boolean> = {};
    for (const factor of factors) {
      const key = factorKey(factor.factor_key);
      nextWeights[key] = Number(factor.suggested_weight || 0);
      nextEnabled[key] = true;
    }
    setWeights(nextWeights);
    setEnabled(nextEnabled);
  }, [factors]);

  async function saveVariant() {
    if (!scenario?.scenario_id) {
      setError("Generate or select a scenario first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await createScenarioVariant(scenario.scenario_id, {
        variant_name: variantName,
        variant_description: "Reviewer-tuned scenario weights from the local workbench.",
        weight_overrides: weights,
        disabled_factors: Object.entries(enabled)
          .filter(([, value]) => !value)
          .map(([key]) => key),
        reviewer_assumptions: assumptions
          .split("\n")
          .map((item) => item.trim())
          .filter(Boolean),
      });
      onVariantCreated?.(response.variant);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Variant creation failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Weight tuning</h3>
          <p className="muted">Tune draft weights for review. Scores are planning-support drafts, not official recommendations.</p>
        </div>
      </div>
      {!scenario ? (
        <p className="muted">Generate or select a scenario to edit factor weights.</p>
      ) : (
        <>
          <label className="field-label">
            Variant name
            <input value={variantName} onChange={(event) => setVariantName(event.target.value)} />
          </label>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Enabled</th>
                  <th>Factor</th>
                  <th>Type</th>
                  <th>Suggested</th>
                  <th>Reviewer weight</th>
                  <th>Direction</th>
                </tr>
              </thead>
              <tbody>
                {factors.map((factor) => {
                  const key = factorKey(factor.factor_key);
                  return (
                    <tr key={key || factor.factor_label}>
                      <td>
                        <input
                          aria-label={`Enable ${factor.factor_label || key}`}
                          type="checkbox"
                          checked={enabled[key] ?? true}
                          onChange={(event) => setEnabled((current) => ({ ...current, [key]: event.target.checked }))}
                        />
                      </td>
                      <td>
                        <strong>{factor.factor_label || key}</strong>
                        <p className="path-text">{factor.notes}</p>
                      </td>
                      <td>{factor.factor_type}</td>
                      <td>{factor.suggested_weight ?? 0}</td>
                      <td>
                        <input
                          aria-label={`Weight ${factor.factor_label || key}`}
                          type="number"
                          step="0.01"
                          value={weights[key] ?? 0}
                          onChange={(event) =>
                            setWeights((current) => ({ ...current, [key]: Number(event.target.value || 0) }))
                          }
                        />
                      </td>
                      <td>{factor.direction}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <label className="field-label">
            Reviewer assumptions
            <textarea value={assumptions} rows={4} onChange={(event) => setAssumptions(event.target.value)} />
          </label>
          <div className="notice notice-warning">
            <strong>Safety rules</strong>
            <p>
              Proxy sources remain context only unless reviewed. Missing official permit data remains unresolved. No
              geometry scoring is executed from this editor.
            </p>
          </div>
          <button className="button" type="button" onClick={saveVariant} disabled={loading}>
            {loading ? "Saving..." : "Save Variant"}
          </button>
          {error ? <p className="inline-error">{error}</p> : null}
        </>
      )}
    </section>
  );
}
