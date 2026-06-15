"use client";

import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { StatusChip } from "@/components/status-chip";
import { makeReviewPacket, makeWebmapDraft } from "@/lib/api";
import type { MapRecipe } from "@/types/automap";

export function RecipeReviewClient() {
  const [prompt, setPrompt] = useState("");
  const [recipe, setRecipe] = useState<MapRecipe | null>(null);
  const [webmapResult, setWebmapResult] = useState<Record<string, unknown> | null>(null);
  const [packetResult, setPacketResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const storedPrompt = window.localStorage.getItem("automap:lastPrompt") || "";
    const storedRecipe = window.localStorage.getItem("automap:lastRecipe");
    setPrompt(storedPrompt);
    if (storedRecipe) {
      setRecipe(JSON.parse(storedRecipe) as MapRecipe);
    }
  }, []);

  async function runAction(kind: "webmap" | "packet") {
    if (!prompt) {
      setError("Generate a recipe from the Map Request page first.");
      return;
    }
    setLoading(kind);
    setError(null);
    try {
      if (kind === "webmap") {
        const response = await makeWebmapDraft(prompt);
        setWebmapResult(response);
        window.localStorage.setItem("automap:lastWebmapDraft", JSON.stringify(response));
      } else {
        const response = await makeReviewPacket(prompt);
        setPacketResult(response);
        window.localStorage.setItem("automap:lastReviewPacket", JSON.stringify(response));
      }
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Workflow action failed.");
    } finally {
      setLoading(null);
    }
  }

  if (!recipe) {
    return (
      <section className="panel">
        <h3>No recipe loaded</h3>
        <p className="muted">Generate a recipe on the Map Request page to populate this review workspace.</p>
      </section>
    );
  }

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="chip-row">
          <StatusChip tone={recipe.needs_review ? "warning" : "success"}>
            {recipe.needs_review ? "Needs review" : "Recipe ready"}
          </StatusChip>
          <StatusChip>{Math.round((recipe.confidence_score || 0) * 100)}% confidence</StatusChip>
        </div>
        <h3>{recipe.map_title}</h3>
        <p className="muted">{recipe.user_intent}</p>
        <div className="button-row">
          <button className="button" type="button" onClick={() => runAction("webmap")} disabled={!!loading}>
            {loading === "webmap" ? "Generating..." : "Generate WebMap Draft"}
          </button>
          <button className="button button-secondary" type="button" onClick={() => runAction("packet")} disabled={!!loading}>
            {loading === "packet" ? "Generating..." : "Generate Review Packet"}
          </button>
          {packetResult?.preview_url ? (
            <a className="button button-secondary" href="/map-preview">
              Preview Map
            </a>
          ) : null}
        </div>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="panel">
        <h3>Selected layers</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Layer</th>
                <th>Role</th>
                <th>Source</th>
                <th>Priority</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {(recipe.selected_layers || []).map((layer) => (
                <tr key={layer.layer_key || layer.layer_name}>
                  <td>{layer.layer_name}</td>
                  <td>{layer.role}</td>
                  <td>{layer.source_status}</td>
                  <td>{layer.source_priority}</td>
                  <td>{layer.layer_url}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="stats-grid">
        <JsonPanel title="Filter plan and expressions" value={recipe.filter_plan || recipe.filters || {}} />
        <JsonPanel title="Spatial operations" value={recipe.spatial_operations || []} />
        <JsonPanel title="Warnings and missing data" value={{ review_reasons: recipe.review_reasons, missing_data_needed: recipe.missing_data_needed }} />
      </section>

      {webmapResult ? <JsonPanel title="WebMap draft result" value={webmapResult} /> : null}
      {packetResult ? <JsonPanel title="Review packet result" value={packetResult} /> : null}
    </div>
  );
}
