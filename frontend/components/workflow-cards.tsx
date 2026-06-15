import { workflowSteps } from "@/components/navigation";

export function WorkflowCards() {
  return (
    <div className="workflow-grid">
      {workflowSteps.map((step, index) => (
        <div className="workflow-card" key={step}>
          <span>{index + 1}</span>
          <h3>{step}</h3>
          <p>{step === "Dry-Run Publish" ? "Portal actions stay dry-run in the frontend." : "Review before advancing."}</p>
        </div>
      ))}
    </div>
  );
}
