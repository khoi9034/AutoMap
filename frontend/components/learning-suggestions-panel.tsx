import { StatusChip } from "@/components/status-chip";
import type { LearnedContext } from "@/types/automap";

type LearningSuggestionsPanelProps = {
  learnedContext?: LearnedContext | null;
};

function itemText(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (value && typeof value === "object" && "layer_key" in value) {
    return String((value as { layer_key?: unknown }).layer_key || "");
  }
  if (value && typeof value === "object" && "answer_label" in value) {
    return String((value as { answer_label?: unknown }).answer_label || "");
  }
  return JSON.stringify(value);
}

export function LearningSuggestionsPanel({ learnedContext }: LearningSuggestionsPanelProps) {
  if (!learnedContext || !(learnedContext.similar_patterns || []).length) {
    return (
      <section className="panel">
        <div className="panel-title-row">
          <div>
            <h3>Learned suggestions</h3>
            <p className="muted">No similar approved pattern has been learned yet.</p>
          </div>
          <StatusChip>Reviewable</StatusChip>
        </div>
      </section>
    );
  }

  return (
    <section className="panel learning-suggestions">
      <div className="panel-title-row">
        <div>
          <h3>Learned suggestions</h3>
          <p className="muted">{learnedContext.review_note}</p>
        </div>
        <StatusChip tone="success">Suggested from approved patterns</StatusChip>
      </div>
      <div className="stats-grid">
        <div className="panel panel-compact">
          <h4>Similar patterns</h4>
          <ul className="review-list">
            {(learnedContext.similar_patterns || []).slice(0, 4).map((pattern) => (
              <li key={String(pattern.pattern_key)}>{String(pattern.pattern_key)} ({String(pattern.similarity_score)})</li>
            ))}
          </ul>
        </div>
        <div className="panel panel-compact">
          <h4>Suggested defaults</h4>
          <ul className="review-list">
            {(learnedContext.suggested_defaults || []).slice(0, 4).map((item, index) => (
              <li key={`${itemText(item)}-${index}`}>{itemText(item)}</li>
            ))}
          </ul>
        </div>
        <div className="panel panel-compact">
          <h4>Preferred layers</h4>
          <ul className="review-list">
            {(learnedContext.preferred_layers || []).slice(0, 5).map((item, index) => (
              <li key={`${itemText(item)}-${index}`}>{itemText(item)}</li>
            ))}
          </ul>
        </div>
        <div className="panel panel-compact">
          <h4>Learned assumptions</h4>
          <ul className="review-list">
            {(learnedContext.learned_assumptions || []).slice(0, 5).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
