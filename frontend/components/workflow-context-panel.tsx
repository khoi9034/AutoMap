"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import {
  clearWorkflowState,
  getWorkflowStepStates,
  loadWorkflowState,
  primaryAdjustedPacketPath,
  primaryApprovedPacketPath,
  primaryReviewPacketPath,
  WORKFLOW_EVENT,
} from "@/lib/workflow-store";
import type { WorkflowState } from "@/types/workflow";

export function WorkflowContextPanel() {
  const pathname = usePathname();
  const [workflow, setWorkflow] = useState<WorkflowState>(() => loadWorkflowState(null));
  const internalPaths = [
    "/workflow",
    "/map-request",
    "/clarify",
    "/recipe-review",
    "/map-preview",
    "/scenario-workbench",
    "/analysis-reports",
    "/adjustments",
    "/approval",
    "/publish-center",
    "/learning",
    "/layer-catalog",
    "/data-gaps",
    "/external-sources",
    "/history",
    "/system-status",
  ];
  const showInternalContext = internalPaths.some((path) => pathname === path || pathname.startsWith(`${path}/`));

  useEffect(() => {
    if (!showInternalContext) return;
    setWorkflow(loadWorkflowState());

    function onWorkflowUpdated() {
      setWorkflow(loadWorkflowState());
    }

    window.addEventListener(WORKFLOW_EVENT, onWorkflowUpdated);
    return () => window.removeEventListener(WORKFLOW_EVENT, onWorkflowUpdated);
  }, [showInternalContext]);

  if (!showInternalContext) {
    return null;
  }

  function resetWorkflow() {
    setWorkflow(clearWorkflowState());
  }

  const reviewPacket = primaryReviewPacketPath(workflow);
  const adjustedPacket = primaryAdjustedPacketPath(workflow);
  const approvedPacket = primaryApprovedPacketPath(workflow);
  const stepStates = getWorkflowStepStates(workflow);
  const blockedStep = stepStates.find((step) => step.status === "blocked");
  const nextStep =
    blockedStep ||
    stepStates.find((step) => step.status === "active") ||
    stepStates.find((step) => step.status === "pending") ||
    stepStates.at(-1);

  return (
    <aside className="workflow-context-panel">
      <div className="panel-title-row">
        <h3>Internal Workflow Context</h3>
        <button className="small-button" type="button" onClick={resetWorkflow}>
          Reset
        </button>
      </div>
      <dl className="status-list">
        <div>
          <dt>Active step</dt>
          <dd>{workflow.activeStep}</dd>
        </div>
        <div>
          <dt>Prompt</dt>
          <dd>{workflow.rawPrompt ? "set" : "none"}</dd>
        </div>
        <div>
          <dt>Recipe</dt>
          <dd>{workflow.refinedRecipe ? "refined" : workflow.recipe ? "ready" : "none"}</dd>
        </div>
        <div>
          <dt>Clarification</dt>
          <dd>{workflow.clarificationSessionId ? workflow.clarificationSession?.status || "started" : "none"}</dd>
        </div>
        <div>
          <dt>Review packet</dt>
          <dd>{reviewPacket ? "selected" : "none"}</dd>
        </div>
        <div>
          <dt>Adjusted</dt>
          <dd>{adjustedPacket ? "selected" : "none"}</dd>
        </div>
        <div>
          <dt>Approved</dt>
          <dd>{approvedPacket ? "selected" : "none"}</dd>
        </div>
      </dl>
      {workflow.missingData.length ? (
        <div className="notice notice-warning">
          <strong>Missing data</strong>
          <p>{workflow.missingData.join(", ")}</p>
        </div>
      ) : null}
      {nextStep ? (
        <div className={blockedStep ? "notice notice-warning" : "notice"}>
          <strong>{blockedStep ? "Blocked step" : "Next action"}</strong>
          <p>
            {nextStep.label}
            {nextStep.reason ? `: ${nextStep.reason}` : " is ready for review."}
          </p>
        </div>
      ) : null}
      <div className="button-row">
        <Link className="button button-secondary" href={nextStep?.href || "/map-request"}>
          Open Next Step
        </Link>
        <Link className="button button-secondary" href="/publish-center">
          Publish Center
        </Link>
      </div>
    </aside>
  );
}
