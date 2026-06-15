"use client";

import { useSearchParams } from "next/navigation";
import { useMemo, useState } from "react";

import { samplePrompts } from "@/components/navigation";
import { StatusChip } from "@/components/status-chip";
import { makeRecipe, makeReviewPacket } from "@/lib/api";
import type { MapRecipe } from "@/types/automap";

type RecipeResponse = {
  prompt: string;
  recipe: MapRecipe;
  data_gaps: unknown[];
};

function textList(values: unknown[] | undefined): string {
  if (!values?.length) {
    return "None detected";
  }
  return values.map((value) => (typeof value === "string" ? value : JSON.stringify(value))).join(", ");
}

export function MapRequestClient() {
  const searchParams = useSearchParams();
  const initialPrompt = useMemo(() => searchParams.get("prompt") || samplePrompts[0], [searchParams]);
  const [prompt, setPrompt] = useState(initialPrompt);
  const [result, setResult] = useState<RecipeResponse | null>(null);
  const [reviewPacket, setReviewPacket] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onGenerate() {
    setLoading(true);
    setError(null);
    setReviewPacket(null);
    try {
      const response = await makeRecipe(prompt);
      setResult(response);
      window.localStorage.setItem("automap:lastPrompt", prompt);
      window.localStorage.setItem("automap:lastRecipe", JSON.stringify(response.recipe));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Recipe request failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onCreatePacket() {
    setLoading(true);
    setError(null);
    try {
      const response = await makeReviewPacket(prompt);
      setReviewPacket(response);
      window.localStorage.setItem("automap:lastReviewPacket", JSON.stringify(response));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Review packet request failed.");
    } finally {
      setLoading(false);
    }
  }

  const recipe = result?.recipe;
  const parsed = recipe?.parsed_request;

  return (
    <div className="page-stack">
      <section className="panel prompt-box">
        <label htmlFor="map-prompt">
          <strong>Map request</strong>
        </label>
        <textarea
          id="map-prompt"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="What map do you need?"
        />
        <div className="sample-grid">
          {samplePrompts.map((sample) => (
            <button className="sample-button" key={sample} type="button" onClick={() => setPrompt(sample)}>
              {sample}
            </button>
          ))}
        </div>
        <div className="button-row">
          <button className="button" type="button" onClick={onGenerate} disabled={loading || !prompt.trim()}>
            {loading ? "Working..." : "Generate Recipe"}
          </button>
          {recipe ? (
            <button className="button button-secondary" type="button" onClick={onCreatePacket} disabled={loading}>
              Continue to Review Packet
            </button>
          ) : null}
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      {recipe ? (
        <>
          <section className="stats-grid">
            <div className="panel">
              <h3>Parsed geography</h3>
              <p>{textList(parsed?.geography_terms as unknown[] | undefined)}</p>
            </div>
            <div className="panel">
              <h3>Parsed topics</h3>
              <p>{textList(parsed?.topics)}</p>
            </div>
            <div className="panel">
              <h3>Confidence</h3>
              <p>{Math.round((recipe.confidence_score || 0) * 100)}%</p>
            </div>
            <div className="panel">
              <h3>Review</h3>
              <StatusChip tone={recipe.needs_review ? "warning" : "success"}>
                {recipe.needs_review ? "Needs review" : "Ready for packet"}
              </StatusChip>
            </div>
          </section>

          <section className="panel">
            <h3>Selected layers</h3>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Layer</th>
                    <th>Category</th>
                    <th>Role</th>
                    <th>Source</th>
                    <th>Confidence</th>
                  </tr>
                </thead>
                <tbody>
                  {(recipe.selected_layers || []).map((layer) => (
                    <tr key={layer.layer_key || layer.layer_name}>
                      <td>{layer.layer_name}</td>
                      <td>{layer.category}</td>
                      <td>{layer.role}</td>
                      <td>{layer.source_status}</td>
                      <td>{Math.round((layer.confidence_score || 0) * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="stats-grid">
            <div className="panel">
              <h3>Warnings</h3>
              <p>{textList(recipe.review_reasons)}</p>
            </div>
            <div className="panel">
              <h3>Missing data</h3>
              <p>{textList(recipe.missing_data_needed)}</p>
            </div>
          </section>
        </>
      ) : null}

      {reviewPacket ? (
        <section className="panel">
          <h3>Review packet created</h3>
          <p>
            <strong>Packet:</strong> {String(reviewPacket.packet_path || "")}
          </p>
          <p>
            <strong>Preview:</strong> {String(reviewPacket.preview_url || "")}
          </p>
        </section>
      ) : null}
    </div>
  );
}
