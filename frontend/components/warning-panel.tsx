import { StatusChip } from "@/components/status-chip";
import type { JsonValue } from "@/types/automap";

type WarningPanelProps = {
  warnings?: JsonValue | string[];
  missingData?: string[];
  blockers?: string[];
};

type WarningGroup = {
  key: string;
  title: string;
  tone: "default" | "success" | "warning" | "danger";
  items: string[];
};

const groupOrder = [
  "missing_data",
  "filter_review",
  "layer_selection",
  "publishing_blockers",
  "historical_data",
  "safety_warnings",
] as const;

function flattenWarnings(value: JsonValue | string[] | undefined, prefix = ""): string[] {
  if (!value) {
    return [];
  }
  if (Array.isArray(value)) {
    return value.flatMap((item) => flattenWarnings(item as JsonValue, prefix));
  }
  if (typeof value === "object") {
    return Object.entries(value).flatMap(([key, item]) =>
      flattenWarnings(item as JsonValue, prefix ? `${prefix}: ${key}` : key),
    );
  }
  const text = String(value);
  return [prefix ? `${prefix}: ${text}` : text];
}

function warningBucket(text: string): (typeof groupOrder)[number] {
  const lower = text.toLowerCase();
  if (lower.includes("missing") || lower.includes("gap")) {
    return "missing_data";
  }
  if (lower.includes("filter") || lower.includes("definition") || lower.includes("expression")) {
    return "filter_review";
  }
  if (lower.includes("layer") || lower.includes("catalog") || lower.includes("source")) {
    return "layer_selection";
  }
  if (lower.includes("publish") || lower.includes("block") || lower.includes("ready")) {
    return "publishing_blockers";
  }
  if (lower.includes("historical") || lower.includes("legacy") || /\b20(0[4-9]|1[0-5])\b/.test(lower)) {
    return "historical_data";
  }
  return "safety_warnings";
}

function buildGroups(warnings: JsonValue | string[] | undefined, missingData: string[] = [], blockers: string[] = []): WarningGroup[] {
  const grouped: Record<(typeof groupOrder)[number], string[]> = {
    missing_data: [...missingData],
    filter_review: [],
    layer_selection: [],
    publishing_blockers: [...blockers],
    historical_data: [],
    safety_warnings: [],
  };

  for (const item of flattenWarnings(warnings)) {
    grouped[warningBucket(item)].push(item);
  }

  const titles: Record<(typeof groupOrder)[number], string> = {
    missing_data: "Missing data",
    filter_review: "Filter review",
    layer_selection: "Layer selection",
    publishing_blockers: "Publishing blockers",
    historical_data: "Historical data",
    safety_warnings: "Safety warnings",
  };

  return groupOrder.map((key) => ({
    key,
    title: titles[key],
    tone: key === "publishing_blockers" && grouped[key].length ? "danger" : grouped[key].length ? "warning" : "success",
    items: Array.from(new Set(grouped[key])),
  }));
}

export function WarningPanel({ warnings, missingData = [], blockers = [] }: WarningPanelProps) {
  const groups = buildGroups(warnings, missingData, blockers);
  const activeCount = groups.reduce((count, group) => count + group.items.length, 0);

  return (
    <section className="panel warning-panel">
      <div className="panel-title-row">
        <div>
          <h3>Warnings and review notes</h3>
          <p className="muted">Grouped by the kind of human review needed before any future publish action.</p>
        </div>
        <StatusChip tone={activeCount ? "warning" : "success"}>
          {activeCount ? `${activeCount} active` : "Clear"}
        </StatusChip>
      </div>
      <div className="warning-grid">
        {groups.map((group) => (
          <article className="warning-group" key={group.key}>
            <div className="warning-group-header">
              <h4>{group.title}</h4>
              <StatusChip tone={group.tone}>{group.items.length || "none"}</StatusChip>
            </div>
            {group.items.length ? (
              <ul className="compact-list">
                {group.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">No current items.</p>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
