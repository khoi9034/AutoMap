"use client";

import type { ComposerStepDisabled, ComposerStepId, ComposerStepStatuses } from "./types";

const STEP_LABELS: Array<{ id: ComposerStepId; label: string; help: string }> = [
  { id: "request", label: "Request", help: "Tell AutoMap what map you need." },
  { id: "preview", label: "Preview", help: "Review the generated map." },
  { id: "adjust", label: "Adjust", help: "Tune layers while the map stays visible." },
  { id: "export", label: "Print / Export", help: "Create local draft outputs." },
];

type ComposerStepTabsProps = {
  activeStep: ComposerStepId;
  disabled?: ComposerStepDisabled;
  onStepChange: (step: ComposerStepId) => void;
  statuses: ComposerStepStatuses;
};

export function ComposerStepTabs({ activeStep, disabled = {}, onStepChange, statuses }: ComposerStepTabsProps) {
  return (
    <nav className="composer-step-tabs" aria-label="Map Composer steps">
      {STEP_LABELS.map((step, index) => {
        const isDisabled = Boolean(disabled[step.id]);
        const isActive = activeStep === step.id;
        const status = statuses[step.id];
        return (
          <button
            className={`composer-step-tab composer-step-tab-${status}${isActive ? " composer-step-tab-active" : ""}`}
            disabled={isDisabled}
            key={step.id}
            type="button"
            onClick={() => onStepChange(step.id)}
          >
            <span>{index + 1}</span>
            <strong>{step.label}</strong>
            <small>{isDisabled ? "Unavailable" : step.help}</small>
          </button>
        );
      })}
    </nav>
  );
}
