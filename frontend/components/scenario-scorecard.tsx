import { StatusChip } from "@/components/status-chip";
import type { PlanningScenario } from "@/types/automap";

type ScenarioScorecardProps = {
  scenario?: PlanningScenario | null;
};

function executionTone(status?: string): "default" | "success" | "warning" | "danger" {
  if (status === "executed_small_sample") {
    return "success";
  }
  if (status === "blocked_by_count") {
    return "danger";
  }
  if (status === "executable_if_refined" || status === "scoring_plan_only") {
    return "warning";
  }
  return "default";
}

export function ScenarioScorecard({ scenario }: ScenarioScorecardProps) {
  return (
    <section className="panel safety-card">
      <h3>Scenario scorecard</h3>
      {scenario ? (
        <div className="stat-list">
          <div>
            <span>Scenario type</span>
            <strong>{scenario.scenario_type}</strong>
          </div>
          <div>
            <span>Confidence</span>
            <strong>{typeof scenario.confidence_score === "number" ? `${Math.round(scenario.confidence_score * 100)}%` : "n/a"}</strong>
          </div>
          <div>
            <span>Execution</span>
            <StatusChip tone={executionTone(scenario.execution_status)}>{scenario.execution_status || "not planned"}</StatusChip>
          </div>
          <div>
            <span>Missing data</span>
            <strong>{(scenario.missing_data || []).join(", ") || "None recorded"}</strong>
          </div>
        </div>
      ) : (
        <p className="muted">Generate a scenario to see the type, confidence, execution status, and missing data.</p>
      )}
    </section>
  );
}
