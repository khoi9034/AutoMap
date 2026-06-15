"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  clearWorkflowState,
  loadWorkflowState,
  primaryAdjustedPacketPath,
  primaryApprovedPacketPath,
  primaryReviewPacketPath,
  WORKFLOW_EVENT,
} from "@/lib/workflow-store";
import type { WorkflowState } from "@/types/workflow";

export function WorkflowContextPanel() {
  const [workflow, setWorkflow] = useState<WorkflowState>(() => loadWorkflowState(null));

  useEffect(() => {
    setWorkflow(loadWorkflowState());

    function onWorkflowUpdated() {
      setWorkflow(loadWorkflowState());
    }

    window.addEventListener(WORKFLOW_EVENT, onWorkflowUpdated);
    return () => window.removeEventListener(WORKFLOW_EVENT, onWorkflowUpdated);
  }, []);

  function resetWorkflow() {
    setWorkflow(clearWorkflowState());
  }

  const reviewPacket = primaryReviewPacketPath(workflow);
  const adjustedPacket = primaryAdjustedPacketPath(workflow);
  const approvedPacket = primaryApprovedPacketPath(workflow);

  return (
    <aside className="workflow-context-panel">
      <div className="panel-title-row">
        <h3>Workflow Context</h3>
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
          <dd>{workflow.recipe ? "ready" : "none"}</dd>
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
      <div className="button-row">
        <Link className="button button-secondary" href="/map-request">
          Request
        </Link>
        <Link className="button button-secondary" href="/publish-center">
          Publish Center
        </Link>
      </div>
    </aside>
  );
}
