"use client";

import { JsonPanel } from "@/components/json-panel";
import { StatusChip } from "@/components/status-chip";
import type { AnalysisPlan, ClarifyingQuestion, MapRecipe, RequestIntelligence } from "@/types/automap";

type RequestIntelligencePanelProps = {
  recipe?: MapRecipe | null;
};

function percent(value: number | undefined): string {
  return `${Math.round((value || 0) * 100)}%`;
}

function questionText(question: ClarifyingQuestion | string): string {
  if (typeof question === "string") {
    return question;
  }
  return question.question || "Review question";
}

function questionReason(question: ClarifyingQuestion | string): string | null {
  if (typeof question === "string") {
    return null;
  }
  const examples = question.examples?.length ? ` Examples: ${question.examples.join(", ")}.` : "";
  return question.reason ? `${question.reason}${examples}` : examples || null;
}

function valuesOrNone(values: string[] | undefined): string {
  return values?.length ? values.join(", ") : "None detected";
}

export function RequestIntelligencePanel({ recipe }: RequestIntelligencePanelProps) {
  const intelligence: RequestIntelligence | undefined = recipe?.request_intelligence;
  const analysisPlan: AnalysisPlan | undefined = recipe?.analysis_plan;

  if (!intelligence && !analysisPlan) {
    return (
      <section className="panel">
        <h3>Request intelligence</h3>
        <p className="muted">Generate a recipe to see detected intents, ambiguity flags, and the analysis plan.</p>
      </section>
    );
  }

  const confidenceByIntent = intelligence?.confidence_by_intent || {};
  const intentList = intelligence?.detected_intents || [];
  const reviewQuestions = analysisPlan?.review_questions || intelligence?.clarifying_questions || [];
  const scenarioContext = intelligence?.scenario_context;

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Request intelligence</h3>
          <p className="muted">{intelligence?.reasoning_summary || analysisPlan?.goal}</p>
        </div>
        <StatusChip tone={intelligence?.understood ? "success" : "warning"}>
          {intelligence?.understood ? "Understood" : "Needs review"}
        </StatusChip>
      </div>

      <div className="chip-row">
        {intentList.map((intent) => (
          <StatusChip key={intent} tone={intent === intelligence?.primary_intent ? "success" : undefined}>
            {intent.replaceAll("_", " ")} {confidenceByIntent[intent] !== undefined ? percent(confidenceByIntent[intent]) : ""}
          </StatusChip>
        ))}
        {intelligence?.quality_score !== undefined ? <StatusChip>Quality {percent(intelligence.quality_score)}</StatusChip> : null}
      </div>

      <div className="stats-grid">
        <div className="panel panel-compact">
          <h4>Constraints</h4>
          <p>{valuesOrNone(intelligence?.extracted_constraints)}</p>
        </div>
        <div className="panel panel-compact">
          <h4>Opportunities</h4>
          <p>{valuesOrNone(intelligence?.extracted_opportunities)}</p>
        </div>
        <div className="panel panel-compact">
          <h4>Ambiguity flags</h4>
          <p>{valuesOrNone(intelligence?.ambiguity_flags)}</p>
        </div>
        <div className="panel panel-compact">
          <h4>Unsupported parts</h4>
          <p>{valuesOrNone(intelligence?.unsupported_parts)}</p>
        </div>
      </div>

      {scenarioContext?.scenario_detected ? (
        <div className="notice notice-warning">
          <strong>Scenario workflow recommended</strong>
          <p>
            {scenarioContext.scenario_type?.replaceAll("_", " ")} should be reviewed as a planning framework with
            transparent assumptions and source coverage warnings.
          </p>
          {scenarioContext.recommended_scenario_workflow ? <p>{scenarioContext.recommended_scenario_workflow}</p> : null}
        </div>
      ) : null}

      <div className="stats-grid">
        <JsonPanel title="Analysis plan" value={analysisPlan || {}} />
        <JsonPanel title="Spatial relationships" value={intelligence?.spatial_relationships || []} />
      </div>

      <div className="panel panel-compact">
        <h4>Review questions</h4>
        {reviewQuestions.length ? (
          <ul className="review-list">
            {reviewQuestions.map((question, index) => (
              <li key={`${questionText(question)}-${index}`}>
                <strong>{questionText(question)}</strong>
                {questionReason(question) ? <span className="muted"> {questionReason(question)}</span> : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">No clarifying questions were generated.</p>
        )}
      </div>
    </section>
  );
}
