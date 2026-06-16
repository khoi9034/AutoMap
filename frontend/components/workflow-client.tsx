"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { ArcGISMapPreview } from "@/components/arcgis-map-preview";
import { JsonPanel } from "@/components/json-panel";
import { samplePrompts } from "@/components/navigation";
import { RequestIntelligencePanel } from "@/components/request-intelligence-panel";
import { SourceCoveragePanel } from "@/components/source-coverage-panel";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { generateReport, makeReviewPacket, runWorkflow } from "@/lib/api";
import {
  mergeWorkflowState,
  packetIdFromPath,
  workflowMissingDataFromRecipe,
  workflowWarningsFromRecipe,
} from "@/lib/workflow-store";
import type { GenerateReportResponse, WorkflowRunResponse } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

const defaultPrompt = "Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads.";

function actionLabel(action?: string): string {
  if (action === "correct_parcel_identifier") return "Correct parcel/PIN/address";
  if (action === "create_preview") return "Create Preview";
  if (action === "run_analysis") return "Run Analysis";
  if (action === "review_recipe") return "Review Recipe";
  return "Generate Report / Print";
}

function identifierText(value: unknown): string {
  if (!value || typeof value !== "object") return String(value || "");
  const item = value as { value?: string; normalized_value?: string; identifier_type?: string };
  return item.value || item.normalized_value || item.identifier_type || JSON.stringify(item);
}

function WorkflowStatusPanel({
  result,
  packetId,
  report,
}: {
  result: WorkflowRunResponse | null;
  packetId: string;
  report: GenerateReportResponse | null;
}) {
  const steps = [
    {
      label: "Generate Recipe",
      status: result ? "completed" : "active",
      note: result?.recipe?.map_title || "Start with a prompt.",
    },
    {
      label: "Preview Map",
      status: packetId ? "completed" : result?.can_preview === false ? "blocked" : result ? "active" : "pending",
      note:
        result?.can_preview === false
          ? result.parcel_context?.reason_if_not_focusable || "Preview waits for a matched parcel."
          : packetId
            ? `Packet ${packetId}`
            : "Create a local review packet.",
    },
    {
      label: "Adjust Draft",
      status: packetId ? "active" : "pending",
      note: "Optional YAML/JSON edits after preview.",
    },
    {
      label: "Run Analysis",
      status: result?.can_analyze ? "active" : "pending",
      note: result?.can_analyze ? "Bounded execution is available." : "Analysis is optional for context maps.",
    },
    {
      label: "Generate Report / Print",
      status: report ? "completed" : packetId ? "active" : "pending",
      note: report?.report_path || "Draft report/export, not official print map.",
    },
  ];

  return (
    <section className="panel workflow-status-panel">
      <p className="eyebrow">Workflow status</p>
      <h3>{actionLabel(result?.next_recommended_action)}</h3>
      <div className="simple-step-list">
        {steps.map((step, index) => (
          <div className={`simple-step simple-step-${step.status}`} key={step.label}>
            <span>{index + 1}</span>
            <div>
              <strong>{step.label}</strong>
              <small>{step.note}</small>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export function WorkflowClient() {
  const [prompt, setPrompt] = useState(defaultPrompt);
  const [result, setResult] = useState<WorkflowRunResponse | null>(null);
  const [packet, setPacket] = useState<Record<string, unknown> | null>(null);
  const [report, setReport] = useState<GenerateReportResponse | null>(null);
  const [loading, setLoading] = useState<"recipe" | "preview" | "report" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  const recipe = result?.recipe;
  const parcelContext = result?.parcel_context || recipe?.parcel_context;
  const packetPath = typeof packet?.packet_path === "string" ? packet.packet_path : "";
  const packetId = useMemo(() => packetIdFromPath(packetPath), [packetPath]);
  const previewBlocked = Boolean(result && result.can_preview === false);
  const canPreview = Boolean(result?.can_preview && recipe);

  async function generateRecipe() {
    setLoading("recipe");
    setError(null);
    setPacket(null);
    setReport(null);
    try {
      const response = await runWorkflow(prompt);
      setResult(response);
      if (response.recipe) {
        mergeWorkflowState({
          rawPrompt: prompt,
          recipe: response.recipe,
          initialRecipe: response.recipe,
          warnings: workflowWarningsFromRecipe(response.recipe),
          missingData: workflowMissingDataFromRecipe(response.recipe),
          activeStep: "recipe",
        });
      }
      setToast({
        tone: response.can_preview === false ? "warning" : "success",
        message: response.can_preview === false ? "Recipe created, but parcel preview is blocked until the parcel matches." : "Recipe ready for preview.",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Workflow request failed.");
    } finally {
      setLoading(null);
    }
  }

  async function createPreview() {
    if (!canPreview) return;
    setLoading("preview");
    setError(null);
    setReport(null);
    try {
      const response = await makeReviewPacket(prompt);
      setPacket(response);
      const path = typeof response.packet_path === "string" ? response.packet_path : "";
      mergeWorkflowState({
        rawPrompt: prompt,
        reviewPacket: response,
        selectedPacketPath: path,
        selectedPacketId: packetIdFromPath(path),
        activeStep: "preview",
      });
      setToast({ tone: "success", message: "Preview packet created." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Preview packet request failed.");
    } finally {
      setLoading(null);
    }
  }

  async function createReport() {
    if (!packetPath) return;
    setLoading("report");
    setError(null);
    try {
      const response = await generateReport(packetPath);
      setReport(response);
      setToast({ tone: "success", message: "Draft report/export created." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Report generation failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="workflow-page-grid">
      <section className="panel workflow-prompt-panel">
        <p className="eyebrow">Prompt</p>
        <h3>Tell AutoMap what map you need</h3>
        <textarea
          className="textarea"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Make a map of parcel 5528-12-3456 and show zoning, floodplain, and nearby roads."
        />
        <div className="sample-grid">
          {samplePrompts.slice(0, 6).map((sample) => (
            <button className="sample-button" key={sample} type="button" onClick={() => setPrompt(sample)}>
              {sample}
            </button>
          ))}
        </div>
        <div className="button-row">
          <button className="button" type="button" onClick={generateRecipe} disabled={loading !== null || !prompt.trim()}>
            {loading === "recipe" ? "Generating..." : "Generate Recipe"}
          </button>
          <button className="button button-secondary" type="button" onClick={createPreview} disabled={loading !== null || !canPreview}>
            {loading === "preview" ? "Creating..." : "Create Preview"}
          </button>
          <button className="button button-secondary" type="button" onClick={createReport} disabled={loading !== null || !packetPath}>
            {loading === "report" ? "Exporting..." : "Generate Report / Print"}
          </button>
        </div>
        {previewBlocked ? (
          <div className="notice notice-warning">
            <strong>Parcel not matched</strong>
            <p>
              {parcelContext?.reason_if_not_focusable ||
                "AutoMap cannot zoom to or analyze the parcel until a valid parcel/PIN/address is provided."}
            </p>
          </div>
        ) : null}
        {loading ? <p className="muted">AutoMap is checking the catalog, parcel fields, and context layers...</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast} />
      </section>

      <main className="workflow-result-column">
        {!result ? (
          <section className="panel empty-state">
            <h3>Prompt to Recipe to Map Preview to Adjust to Analysis/Report to Print/Export</h3>
            <p>Use this page for the normal guided workflow. Analysis is optional and is not forced for basic parcel context maps.</p>
          </section>
        ) : null}

        {recipe ? (
          <>
            <section className="panel">
              <div className="panel-title-row">
                <div>
                  <p className="eyebrow">Recipe</p>
                  <h3>{recipe.map_title || "AutoMap Draft Recipe"}</h3>
                  <p className="muted">{recipe.user_intent}</p>
                </div>
                <div className="chip-row">
                  <StatusChip tone={previewBlocked ? "danger" : "success"}>
                    {previewBlocked ? "Preview blocked" : "Preview ready"}
                  </StatusChip>
                  <StatusChip tone={result.can_analyze ? "warning" : "default"}>
                    {result.can_analyze ? "Analysis available" : "Analysis optional"}
                  </StatusChip>
                </div>
              </div>
              <div className="result-strip">
                <div>
                  <span>Selected layers</span>
                  <strong>{result.selected_layers?.length || recipe.selected_layers?.length || 0}</strong>
                </div>
                <div>
                  <span>Confidence</span>
                  <strong>{Math.round((recipe.confidence_score || 0) * 100)}%</strong>
                </div>
                <div>
                  <span>Next action</span>
                  <strong>{actionLabel(result.next_recommended_action)}</strong>
                </div>
              </div>
            </section>

            {parcelContext ? (
              <section className={`panel ${previewBlocked ? "notice-warning" : ""}`}>
                <div className="panel-title-row">
                  <div>
                    <p className="eyebrow">Parcel match status</p>
                    <h3>{parcelContext.can_focus_map ? "Parcel focus available" : "Parcel not matched"}</h3>
                    <p className="muted">
                      {parcelContext.reason_if_not_focusable ||
                        "Selected parcel geometry can focus the map with a small parcel buffer extent."}
                    </p>
                  </div>
                  <StatusChip tone={parcelContext.can_focus_map ? "success" : "danger"}>
                    {parcelContext.match_status || "needs_review"}
                  </StatusChip>
                </div>
                <div className="detail-grid">
                  <div>
                    <span className="muted">Matched</span>
                    <strong>{parcelContext.matched_count ?? 0}</strong>
                  </div>
                  <div>
                    <span className="muted">Can focus map</span>
                    <strong>{parcelContext.can_focus_map ? "Yes" : "No"}</strong>
                  </div>
                  <div>
                    <span className="muted">Geometry output</span>
                    <strong>{parcelContext.selected_parcel_geojson_path ? "Created" : "Not created"}</strong>
                  </div>
                </div>
                {parcelContext.unmatched_identifiers?.length ? (
                  <div className="definition-box">
                    <strong>Unmatched identifiers</strong>
                    <p>{parcelContext.unmatched_identifiers.map(identifierText).join(", ")}</p>
                  </div>
                ) : null}
              </section>
            ) : null}

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
                    </tr>
                  </thead>
                  <tbody>
                    {(recipe.selected_layers || []).map((layer) => (
                      <tr key={layer.layer_key || layer.layer_name}>
                        <td>{layer.layer_name}</td>
                        <td>{layer.category}</td>
                        <td>{layer.role}</td>
                        <td>{layer.source_role || layer.source_status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <RequestIntelligencePanel recipe={recipe} />
            <SourceCoveragePanel coverage={recipe.source_coverage} />
          </>
        ) : null}

        {packetId ? (
          <>
            <ArcGISMapPreview packetId={packetId} />
            <section className="panel">
              <h3>Draft export links</h3>
              <p className="muted">Draft report/export, not official print map.</p>
              <div className="button-row">
                <Link className="button" href="/adjustments">
                  Adjust Draft
                </Link>
                <Link className="button button-secondary" href="/map-preview">
                  Open Full Preview Page
                </Link>
                {report?.files?.map((file) => (
                  <a className="button button-secondary" href={file.url || "#"} key={file.name} target="_blank" rel="noreferrer">
                    {file.name}
                  </a>
                ))}
              </div>
            </section>
          </>
        ) : null}

        {result ? <JsonPanel title="Workflow response" value={result} /> : null}
      </main>

      <aside className="workflow-side">
        <WorkflowStatusPanel result={result} packetId={packetId} report={report} />
        <section className="panel">
          <p className="eyebrow">Safety</p>
          <h3>Draft-only workflow</h3>
          <ul className="compact-list">
            <li>No real ArcGIS publish button.</li>
            <li>No ArcGIS login required.</li>
            <li>Parcel preview requires a matched parcel.</li>
            <li>Analysis is optional and bounded.</li>
          </ul>
        </section>
      </aside>
    </div>
  );
}
