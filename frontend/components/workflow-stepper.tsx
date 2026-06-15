"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  getWorkflowStepStates,
  loadWorkflowState,
  mergeWorkflowState,
  WORKFLOW_EVENT,
} from "@/lib/workflow-store";
import type { WorkflowState, WorkflowStepId } from "@/types/workflow";

type WorkflowStepperProps = {
  activeStep?: WorkflowStepId;
};

export function WorkflowStepper({ activeStep }: WorkflowStepperProps) {
  const [workflow, setWorkflow] = useState<WorkflowState>(() => loadWorkflowState(null));

  useEffect(() => {
    const next = activeStep ? mergeWorkflowState({ activeStep }) : loadWorkflowState();
    setWorkflow(next);

    function onWorkflowUpdated() {
      setWorkflow(loadWorkflowState());
    }

    window.addEventListener(WORKFLOW_EVENT, onWorkflowUpdated);
    return () => window.removeEventListener(WORKFLOW_EVENT, onWorkflowUpdated);
  }, [activeStep]);

  return (
    <section className="workflow-stepper" aria-label="AutoMap workflow progress">
      {getWorkflowStepStates(workflow).map((step, index) => (
        <Link className={`workflow-step workflow-step-${step.status}`} href={step.href} key={step.id} title={step.reason || step.label}>
          <span>{index + 1}</span>
          <strong>{step.label}</strong>
          <em>{step.status}</em>
        </Link>
      ))}
    </section>
  );
}
