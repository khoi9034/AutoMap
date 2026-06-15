import { StatusChip } from "@/components/status-chip";
import type { ClarificationDefault } from "@/types/automap";

type ClarificationDefaultCardProps = {
  item: ClarificationDefault;
};

export function ClarificationDefaultCard({ item }: ClarificationDefaultCardProps) {
  return (
    <article className="panel panel-compact">
      <div className="panel-title-row">
        <div>
          <h4>{item.question_text || item.default_key}</h4>
          <p className="muted">{item.answer_label || JSON.stringify(item.default_answer)}</p>
        </div>
        <StatusChip tone={item.is_active === false ? "warning" : "success"}>
          {Math.round((item.confidence_score || 0) * 100)}%
        </StatusChip>
      </div>
      <dl className="status-list">
        <div>
          <dt>Intent</dt>
          <dd>{item.intent || "general"}</dd>
        </div>
        <div>
          <dt>Topic</dt>
          <dd>{item.topic || "general"}</dd>
        </div>
        <div>
          <dt>Source</dt>
          <dd>{item.source_pattern_key || "approved pattern"}</dd>
        </div>
      </dl>
    </article>
  );
}
