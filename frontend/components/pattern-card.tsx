import { StatusChip } from "@/components/status-chip";
import type { ApprovedPattern } from "@/types/automap";

type PatternCardProps = {
  pattern: ApprovedPattern;
  onSelect?: (pattern: ApprovedPattern) => void;
};

export function PatternCard({ pattern, onSelect }: PatternCardProps) {
  return (
    <article className="panel pattern-card">
      <div className="panel-title-row">
        <div>
          <h3>{pattern.primary_intent?.replaceAll("_", " ") || "Approved pattern"}</h3>
          <p className="muted">{pattern.raw_prompt || pattern.pattern_key}</p>
        </div>
        <StatusChip tone={pattern.final_publish_ready ? "success" : "warning"}>
          {pattern.final_publish_ready ? "Approved" : "Review"}
        </StatusChip>
      </div>
      <dl className="status-list">
        <div>
          <dt>Pattern</dt>
          <dd>{pattern.pattern_key}</dd>
        </div>
        <div>
          <dt>Topics</dt>
          <dd>{(pattern.topics || []).join(", ") || "None"}</dd>
        </div>
        <div>
          <dt>Preferred layers</dt>
          <dd>{pattern.preferred_layer_keys?.length || 0}</dd>
        </div>
        <div>
          <dt>Clarifications</dt>
          <dd>{pattern.clarification_answers?.length || 0}</dd>
        </div>
      </dl>
      {onSelect ? (
        <button className="button button-secondary" type="button" onClick={() => onSelect(pattern)}>
          View Pattern
        </button>
      ) : null}
    </article>
  );
}
