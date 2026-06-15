import type { SystemStatus } from "@/types/automap";

type StatusPanelProps = {
  status: SystemStatus;
};

export function StatusPanel({ status }: StatusPanelProps) {
  return (
    <aside className="status-panel">
      <h3>System Snapshot</h3>
      <dl className="status-list">
        <div>
          <dt>Version</dt>
          <dd>{status.version || "unknown"}</dd>
        </div>
        <div>
          <dt>Catalog records</dt>
          <dd>{status.catalog?.layer_count ?? 0}</dd>
        </div>
        <div>
          <dt>Verified layers</dt>
          <dd>{status.catalog?.verified_layer_count ?? 0}</dd>
        </div>
        <div>
          <dt>Data gaps</dt>
          <dd>{status.data_gap_count ?? 0}</dd>
        </div>
        <div>
          <dt>Approved packets</dt>
          <dd>{status.packets?.approved_packet_count ?? 0}</dd>
        </div>
        <div>
          <dt>Frontend</dt>
          <dd>{status.ports?.frontend || 3010}</dd>
        </div>
        <div>
          <dt>Backend/API</dt>
          <dd>{status.ports?.backend_api || 8010}</dd>
        </div>
      </dl>
      <div className="notice">
        <strong>Safety mode</strong>
        <p>{status.arcgis_publisher_mode || "Dry-run only. Real publish remains CLI-only."}</p>
      </div>
    </aside>
  );
}
