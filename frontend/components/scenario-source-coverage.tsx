import { SourceCoveragePanel } from "@/components/source-coverage-panel";
import type { PlanningScenario } from "@/types/automap";

type ScenarioSourceCoverageProps = {
  scenario?: PlanningScenario | null;
};

export function ScenarioSourceCoverage({ scenario }: ScenarioSourceCoverageProps) {
  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Source roles still apply</strong>
        <p>
          Proxy layers remain context only, reference layers do not resolve development gaps, and missing official data
          stays visible in scenario output.
        </p>
      </section>
      <SourceCoveragePanel coverage={scenario?.source_coverage} />
    </div>
  );
}
