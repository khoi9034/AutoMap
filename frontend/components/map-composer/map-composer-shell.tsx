"use client";

import type { ReactNode } from "react";

import { ComposerStepTabs } from "./composer-step-tabs";
import type { ComposerStepDisabled, ComposerStepId, ComposerStepStatuses } from "./types";

type MapComposerShellProps = {
  activeStep: ComposerStepId;
  children: ReactNode;
  disabled?: ComposerStepDisabled;
  onStepChange: (step: ComposerStepId) => void;
  statuses: ComposerStepStatuses;
};

export function MapComposerShell({ activeStep, children, disabled, onStepChange, statuses }: MapComposerShellProps) {
  return (
    <div className="map-composer-shell">
      <ComposerStepTabs activeStep={activeStep} disabled={disabled} onStepChange={onStepChange} statuses={statuses} />
      <div className={`composer-step-body composer-step-body-${activeStep}`}>{children}</div>
    </div>
  );
}
