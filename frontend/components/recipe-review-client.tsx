"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { makeReviewPacket, makeWebmapDraft } from "@/lib/api";
import {
  loadWorkflowState,
  mergeWorkflowState,
  packetIdFromPath,
  primaryReviewPacketPath,
} from "@/lib/workflow-store";
import type { MapRecipe } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

export function RecipeReviewClient() {
  const [prompt, setPrompt] = useState("");
  const [recipe, setRecipe] = useState<MapRecipe | null>(null);
  const [webmapResult, setWebmapResult] = useState<Record<string, unknown> | null>(null);
  const [packetResult, setPacketResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  useEffect(() => {
    const workflow = loadWorkflowState();
    setPrompt(workflow.rawPrompt || window.localStorage.getItem("automap:lastPrompt") || "");
    if (workflow.recipe) {
      setRecipe(workflow.recipe);
    } else {
      const storedRecipe = window.localStorage.getItem("automap:lastRecipe");
      if (storedRecipe) {
        setRecipe(JSON.parse(storedRecipe) as MapRecipe);
      }
    }
    if (workflow.webmapDraft) {
      setWebmapResult(workflow.webmapDraft);
    }
    if (workflow.reviewPacket) {
      setPacketResult(workflow.reviewPacket);
    }
    mergeWorkflowState({ activeStep: "recipe" });
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
        mergeWorkflowState({ webmapDraft: response, activeStep: "webmap" });
        setToast({ tone: "success", message: "WebMap draft generated and saved to workflow state." });
        window.localStorage.setItem("automap:lastWebmapDraft", JSON.stringify(response));
      } else {
        const response = await makeReviewPacket(prompt);
        setPacketResult(response);
        const packetPath = typeof response.packet_path === "string" ? response.packet_path : "";
        mergeWorkflowState({
          reviewPacket: response,
          selectedPacketPath: packetPath,
          selectedPacketId: packetIdFromPath(packetPath),
          activeStep: "review_packet",
        });
        setToast({ tone: "success", message: "Review packet created. Preview and adjustments are ready." });
        window.localStorage.setItem("automap:lastReviewPacket", JSON.stringify(response));
        if (typeof response.packet_path === "string") {
          window.localStorage.setItem("automap:lastPacketPath", response.packet_path);
        }
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
        <Link className="button" href="/map-request">
          Start Map Request
        </Link>
      </section>
    );
  }

  const workflow = loadWorkflowState();
  const reviewPacketPath = primaryReviewPacketPath(workflow) || (typeof packetResult?.packet_path === "string" ? packetResult.packet_path : "");

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
              Open Map Preview
            </a>
          ) : null}
          {reviewPacketPath ? (
            <Link className="button button-secondary" href="/adjustments">
              Go to Adjustments
            </Link>
          ) : null}
        </div>
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast} />
      </section>

      <section className="panel">
        <h3>Selected layers</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Layer</th>
                <th>Role</th>
                <th>New vs legacy</th>
                <th>Priority</th>
                <th>Confidence</th>
                <th>URL</th>
              </tr>
            </thead>
            <tbody>
              {(recipe.selected_layers || []).map((layer) => (
                <tr key={layer.layer_key || layer.layer_name}>
                  <td>{layer.layer_name}</td>
                  <td>{layer.role}</td>
                  <td>
                    <StatusChip tone={layer.source_priority === 1 ? "success" : "warning"}>
                      {layer.source_status || "unknown"}
                    </StatusChip>
                  </td>
                  <td>{layer.source_priority}</td>
                  <td>{Math.round((layer.confidence_score || 0) * 100)}%</td>
                  <td className="url-cell">{layer.layer_url}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="stats-grid">
        <JsonPanel title="Filter plan and expressions" value={recipe.filter_plan || recipe.filters || {}} />
        <JsonPanel title="Definition expressions" value={recipe.filter_plan || {}} />
        <JsonPanel title="Spatial operations" value={recipe.spatial_operations || []} />
        <JsonPanel title="Warnings and missing data" value={{ review_reasons: recipe.review_reasons, missing_data_needed: recipe.missing_data_needed }} />
      </section>

      {webmapResult ? <JsonPanel title="WebMap draft result" value={webmapResult} /> : null}
      {packetResult ? (
        <section className="panel">
          <h3>Review packet created</h3>
          <p className="path-text">{reviewPacketPath}</p>
          <div className="button-row">
            <Link className="button" href="/map-preview">
              Preview Map
            </Link>
            <Link className="button button-secondary" href="/adjustments">
              Create Adjustment Template
            </Link>
            <Link className="button button-secondary" href="/adjustments">
              Go to Adjustments
            </Link>
          </div>
        </section>
      ) : null}
      {packetResult ? <JsonPanel title="Review packet result" value={packetResult} /> : null}
    </div>
  );
}
