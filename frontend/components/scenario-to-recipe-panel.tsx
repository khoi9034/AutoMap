"use client";

import Link from "next/link";
import { useState } from "react";

import { scenarioToRecipe, scenarioVariantToRecipe } from "@/lib/api";
import type { PlanningScenario, ScenarioToRecipeResult, ScenarioVariant } from "@/types/automap";

type ScenarioToRecipePanelProps = {
  scenario?: PlanningScenario | null;
  variant?: ScenarioVariant | null;
  onRecipeCreated?: (result: ScenarioToRecipeResult) => void;
};

export function ScenarioToRecipePanel({ scenario, variant, onRecipeCreated }: ScenarioToRecipePanelProps) {
  const [result, setResult] = useState<ScenarioToRecipeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function convert() {
    if (!scenario?.scenario_id && !variant?.variant_id) {
      setError("Select a scenario or variant first.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = variant?.variant_id
        ? await scenarioVariantToRecipe(variant.variant_id)
        : await scenarioToRecipe(String(scenario?.scenario_id));
      setResult(response);
      onRecipeCreated?.(response);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Scenario-to-recipe conversion failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Scenario to recipe</h3>
          <p className="muted">Convert the reviewed planning framework into a draft map recipe workflow input.</p>
        </div>
      </div>
      <p>
        Scenario scores are planning-support drafts, not official recommendations. Conversion preserves source coverage,
        missing data, and proxy warnings.
      </p>
      <button className="button" type="button" onClick={convert} disabled={loading || (!scenario && !variant)}>
        {loading ? "Converting..." : "Convert to Recipe"}
      </button>
      {result?.recipe ? (
        <div className="notice notice-success">
          <strong>Draft recipe ready</strong>
          <p>{result.recipe.map_title}</p>
          <Link className="text-link" href="/recipe-review">
            Continue to Recipe Review
          </Link>
        </div>
      ) : null}
      {error ? <p className="inline-error">{error}</p> : null}
    </section>
  );
}
