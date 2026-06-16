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
        <StatusChip tone="warning">{routeStatus || "network_route_not_available"}</StatusChip>
      </div>
      <p>
        Road-network routing requires an approved routing/network service. AutoMap v3.1 only creates a straight-line
        reference and does not call paid or external routing APIs.
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
