"use client";

export type SimpleComposerStepStatus = "pending" | "active" | "complete" | "blocked";

type SimpleMapComposerStepperProps = {
  statuses: {
    request: SimpleComposerStepStatus;
    preview: SimpleComposerStepStatus;
    adjust: SimpleComposerStepStatus;
    export: SimpleComposerStepStatus;
  };
  notes?: {
    request?: string;
    preview?: string;
    adjust?: string;
    export?: string;
  };
};

const SIMPLE_COMPOSER_STEPS = [
  { id: "request", label: "Request" },
  { id: "preview", label: "Preview" },
  { id: "adjust", label: "Adjust" },
  { id: "export", label: "Print / Export" },
] as const;

export function SimpleMapComposerStepper({ statuses, notes }: SimpleMapComposerStepperProps) {
  return (
    <section className="simple-map-composer-stepper" aria-label="Map Composer progress">
      {SIMPLE_COMPOSER_STEPS.map((step, index) => {
        const status = statuses[step.id];
        const note = notes?.[step.id];
        return (
          <div className={`simple-composer-step simple-composer-step-${status}`} key={step.id}>
            <span className="simple-composer-step-number">{index + 1}</span>
            <div>
              <strong>{step.label}</strong>
              <em>{status}</em>
              {note ? <small>{note}</small> : null}
            </div>
          </div>
        );
      })}
    </section>
  );
}
