import type { AnalysisGroupedSummary } from "@/types/automap";

type AnalysisSummaryTableProps = {
  rows?: AnalysisGroupedSummary[];
};

function countRows(row: AnalysisGroupedSummary): string {
  if (!row.rows?.length) {
    return "0";
  }
  return row.rows.length.toLocaleString();
}

export function AnalysisSummaryTable({ rows = [] }: AnalysisSummaryTableProps) {
  if (!rows.length) {
    return (
      <div className="empty-state compact-empty">
        <h3>No grouped summaries</h3>
        <p>AutoMap records unsupported grouped statistics without failing the report.</p>
      </div>
    );
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Field</th>
            <th>Status</th>
            <th>Groups</th>
            <th>Geometry</th>
            <th>Note</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${row.layer_key}-${row.field_name}-${index}`}>
              <td>
                <strong>{row.field_alias || row.field_name || "Field unavailable"}</strong>
                <p className="path-text">{row.field_name || row.layer_key}</p>
              </td>
              <td>{row.status || "unknown"}</td>
              <td>{countRows(row)}</td>
              <td>{row.return_geometry === false ? "count/statistics only" : "not recorded"}</td>
              <td>{row.reason || row.request_method || "ArcGIS REST statistics summary"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
