import { StatusChip } from "@/components/status-chip";

type RouteWarningPanelProps = {
  routeStatus?: string;
  warnings?: string[];
};

export function RouteWarningPanel({ routeStatus, warnings = [] }: RouteWarningPanelProps) {
  return (
    <section className="notice notice-warning">
      <div className="panel-title-row">
        <strong>Route draft safety</strong>
        <StatusChip tone="warning">{routeStatus || "straight_line_reference"}</StatusChip>
      </div>
      <p>
        AutoMap prefers a bounded road-following draft when verified street centerlines can be queried safely. Otherwise
        it falls back to a straight-line reference and does not call paid or external routing APIs.
      </p>
      {warnings.length ? (
        <ul className="warning-list">
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
