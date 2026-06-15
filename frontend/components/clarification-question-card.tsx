"use client";

import type { ClarificationQuestionModel, JsonValue } from "@/types/automap";

type ClarificationQuestionCardProps = {
  question: ClarificationQuestionModel;
  value: JsonValue | undefined;
  onChange: (questionId: string, value: JsonValue, label?: string) => void;
};

function optionLabel(value: JsonValue | undefined, question: ClarificationQuestionModel): string {
  const values = Array.isArray(value) ? value : [value];
  return (question.options || [])
    .filter((option) => values.some((item) => JSON.stringify(item) === JSON.stringify(option.value)))
    .map((option) => option.label || String(option.value))
    .join(", ");
}

function stringValue(value: JsonValue | undefined): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

function suggestionLabel(question: ClarificationQuestionModel): string {
  if (question.answer_label) {
    return String(question.answer_label);
  }
  if (question.suggested_default !== undefined) {
    return stringValue(question.suggested_default);
  }
  return "";
}

export function ClarificationQuestionCard({ question, value, onChange }: ClarificationQuestionCardProps) {
  const questionId = question.question_id || "";
  const type = question.question_type || "text";
  const selectedValues = Array.isArray(value) ? value : [];

  function updateSingle(nextValue: JsonValue) {
    onChange(questionId, nextValue, optionLabel(nextValue, question));
  }

  function updateMulti(nextValue: JsonValue, checked: boolean) {
    const existing = new Set(selectedValues.map((item) => JSON.stringify(item)));
    const key = JSON.stringify(nextValue);
    if (checked) {
      existing.add(key);
    } else {
      existing.delete(key);
    }
    const nextValues = Array.from(existing).map((item) => JSON.parse(item) as JsonValue);
    onChange(questionId, nextValues, optionLabel(nextValues, question));
  }

  return (
    <article className="panel clarification-card">
      <div className="panel-title-row">
        <div>
          <h3>{question.question_text}</h3>
          {question.help_text ? <p className="muted">{question.help_text}</p> : null}
        </div>
        <span className="chip chip-warning">{question.blocking_level || "review_needed"}</span>
      </div>

      {question.suggested_default !== undefined ? (
        <div className="notice notice-info compact-notice">
          <strong>Suggested from approved patterns</strong>
          <p>
            {suggestionLabel(question)}
            {question.default_confidence ? ` (${Math.round(question.default_confidence * 100)}% confidence)` : ""}
          </p>
          {question.explanation ? <p>{question.explanation}</p> : null}
          <button
            className="small-button"
            type="button"
            onClick={() => onChange(questionId, question.suggested_default ?? "", suggestionLabel(question))}
          >
            Use suggestion
          </button>
        </div>
      ) : null}

      {type === "single_choice" || type === "distance" || type === "date_range" || type === "year" ? (
        <div className="choice-grid">
          {(question.options || []).map((option) => (
            <label className="choice-option" key={String(option.value)}>
              <input
                type="radio"
                name={questionId}
                checked={JSON.stringify(value ?? question.default_answer) === JSON.stringify(option.value)}
                onChange={() => updateSingle(option.value ?? "")}
              />
              <span>{option.label || String(option.value)}</span>
            </label>
          ))}
        </div>
      ) : null}

      {type === "multi_choice" ? (
        <div className="choice-grid">
          {(question.options || []).map((option) => (
            <label className="choice-option" key={String(option.value)}>
              <input
                type="checkbox"
                checked={selectedValues.some((item) => JSON.stringify(item) === JSON.stringify(option.value))}
                onChange={(event) => updateMulti(option.value ?? "", event.target.checked)}
              />
              <span>{option.label || String(option.value)}</span>
            </label>
          ))}
        </div>
      ) : null}

      {type === "text" || type === "number" ? (
        <input
          className="text-input"
          type={type === "number" ? "number" : "text"}
          value={stringValue(value)}
          onChange={(event) => onChange(questionId, event.target.value)}
        />
      ) : null}
    </article>
  );
}
