import Link from "next/link";

import { workflowSteps } from "@/components/navigation";

export function WorkflowCards() {
  return (
    <div className="workflow-grid">
      {workflowSteps.map((step, index) => (
        <Link className="workflow-card" href={step.href} key={step.label}>
          <span>{index + 1}</span>
          <h3>{step.label}</h3>
          <p>{step.description}</p>
        </Link>
      ))}
    </div>
  );
}
