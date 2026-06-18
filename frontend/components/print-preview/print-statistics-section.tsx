import type { ComposerMapState, ComposerResponse } from "@/types/automap";

type PrintStatisticsSectionProps = {
  mapState?: ComposerMapState | null;
  response?: ComposerResponse | null;
};

function countWarnings(mapState?: ComposerMapState | null, response?: ComposerResponse | null): number {
  return new Set([...(mapState?.warnings || []), ...(response?.warnings || []), ...(response?.missing_data || [])]).size;
}

export function PrintStatisticsSection({ mapState, response }: PrintStatisticsSectionProps) {
  const proximity = mapState?.proximity_summary || response?.proximity_result || {};
  const distance =
    typeof proximity.distance_value === "number"
      ? `${proximity.distance_value.toFixed(2)} ${proximity.distance_unit || "miles"}`
      : "Unavailable";
  const rows = [
    ["Visible layers", String(mapState?.visible_layers?.length || response?.selected_layers?.length || 0)],
    ["Hidden layers", String(mapState?.hidden_layers?.length || 0)],
    ["Derived overlays", String(mapState?.derived_overlays?.length || 0)],
    ["Route distance", distance],
    ["Route mode", String(proximity.route_label || proximity.route_mode || "Not applicable")],
    ["Warning count", String(countWarnings(mapState, response))],
    ["Permit statistics", "Unavailable - official current permit source remains unresolved."],
    ["Planning case statistics", "Unavailable unless a verified planning source covers the request geography."],
    ["Development proxy statistics", "Unavailable unless proxy context was requested and safely bounded."],
  ];

  return (
    <section className="print-preview-sheet print-preview-section">
      <h2>Statistics</h2>
      <p className="muted">Statistics reflect the locked draft map state and only use available verified context.</p>
      <table className="print-preview-table">
        <tbody>
          {rows.map(([label, value]) => (
            <tr key={label}>
              <th>{label}</th>
              <td>{value}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
