"use client";

import { StatusChip } from "@/components/status-chip";
import type { AnalysisRefinementOption } from "@/types/automap";

function toneForSafety(level?: string) {
  if (level === "safe") {
    return "success" as const;
  }
  if (level === "blocked") {
    return "danger" as const;
  }
  return "warning" as const;
}

export function RefinementOptionCard({
  option,
  selected,
  onSelect,
}: {
  option: AnalysisRefinementOption;
  selected?: boolean;
  onSelect?: (option: AnalysisRefinementOption) => void;
}) {
  return (
    <div className={`mini-card ${selected ? "selected-card" : ""}`}>
      <div className="panel-title-row">
        <div>
          <h3>{option.label || option.option_id || "Refinement option"}</h3>
          <p className="muted">{option.description}</p>
        </div>
        <div className="chip-row">
          {option.recommended ? <StatusChip tone="success">Recommended</StatusChip> : null}
          <StatusChip tone={toneForSafety(option.safety_level)}>{option.safety_level || "review"}</StatusChip>
        </div>
      </div>
      <div className="metric-grid">
        <div>
          <span className="metric-label">Estimated count</span>
          <strong>{typeof option.estimated_count === "number" ? option.estimated_count.toLocaleString() : "n/a"}</strong>
        </div>
        <div>
          <span className="metric-label">Output</span>
          <strong>{option.expected_output || "review guidance"}</strong>
        </div>
      </div>
      {option.required_user_input?.length ? (
        <ul className="plain-list">
          {option.required_user_input.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}
      {option.tradeoffs?.length ? (
        <div className="inline-warning">
          <strong>Tradeoffs</strong>
          <ul className="plain-list">
            {option.tradeoffs.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {onSelect ? (
        <button className="button button-secondary" type="button" onClick={() => onSelect(option)}>
          Select option
        </button>
      ) : null}
    </div>
  );
}
