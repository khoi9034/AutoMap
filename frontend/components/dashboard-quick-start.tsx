"use client";

import Link from "next/link";
import { useState } from "react";

import { samplePrompts } from "@/components/navigation";
import { StatusChip } from "@/components/status-chip";
import { makeRecipe } from "@/lib/api";
import type { MapRecipe } from "@/types/automap";

function formatPercent(value: number | undefined): string {
  return `${Math.round((value || 0) * 100)}%`;
}

export function DashboardQuickStart() {
  const [prompt, setPrompt] = useState(samplePrompts[0]);
  const [recipe, setRecipe] = useState<MapRecipe | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function generateRecipe() {
    setLoading(true);
    setError(null);
    try {
      const response = await makeRecipe(prompt);
      setRecipe(response.recipe);
      window.localStorage.setItem("automap:lastPrompt", prompt);
      window.localStorage.setItem("automap:lastRecipe", JSON.stringify(response.recipe));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Recipe request failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel prompt-box">
      <div className="panel-title-row">
        <div>
          <h3>Quick map request</h3>
          <p className="muted">Generate a draft recipe from verified catalog layers.</p>
        </div>
        <StatusChip tone="success">Draft only</StatusChip>
      </div>
      <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} aria-label="Quick map request prompt" />
      <div className="sample-grid">
        {samplePrompts.map((sample) => (
          <button className="sample-button" key={sample} type="button" onClick={() => setPrompt(sample)}>
            {sample}
          </button>
        ))}
      </div>
      <div className="button-row">
        <button className="button" type="button" onClick={generateRecipe} disabled={loading || !prompt.trim()}>
          {loading ? "Generating..." : "Generate Recipe"}
        </button>
        {recipe ? (
          <Link className="button button-secondary" href="/recipe-review">
            Continue to Recipe Review
          </Link>
        ) : null}
      </div>
      {error ? <p className="error-text">{error}</p> : null}
      {recipe ? (
        <div className="result-strip">
          <div>
            <span>Recipe</span>
            <strong>{recipe.map_title || "Untitled draft"}</strong>
          </div>
          <div>
            <span>Layers</span>
            <strong>{recipe.selected_layers?.length || 0}</strong>
          </div>
          <div>
            <span>Confidence</span>
            <strong>{formatPercent(recipe.confidence_score)}</strong>
          </div>
          <div>
            <span>Review</span>
            <strong>{recipe.needs_review ? "Required" : "Ready"}</strong>
          </div>
        </div>
      ) : null}
    </section>
  );
}
