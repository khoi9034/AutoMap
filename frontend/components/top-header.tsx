import type { SystemStatus } from "@/types/automap";

type TopHeaderProps = {
  status: SystemStatus;
};

export function TopHeader({ status }: TopHeaderProps) {
  return (
    <header className="top-header">
      <div>
        <p className="eyebrow">AutoMap: County GIS Request Engine</p>
        <h2>Planning map workflow console</h2>
      </div>
      <div className="header-actions">
        <span className="chip">FE {status.ports?.frontend || 3010}</span>
        <span className="chip">API {status.ports?.backend_api || 8010}</span>
        <span className={status.database_connected ? "chip chip-success" : "chip chip-warning"}>
          DB {status.database_connected ? "connected" : "offline"}
        </span>
        <span className={status.real_publish_enabled ? "chip chip-warning" : "chip chip-success"}>
          Real publish {status.real_publish_enabled ? "enabled" : "disabled"}
        </span>
      </div>
    </header>
  );
}
