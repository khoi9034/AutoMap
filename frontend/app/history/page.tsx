import { SectionHeader } from "@/components/section-header";
import { StatusChip } from "@/components/status-chip";
import { getHistory } from "@/lib/api";
import type { HistoryRow } from "@/types/automap";

type ApprovalHistoryRow = Record<string, string | number | boolean | null | undefined>;

export default async function HistoryPage() {
  let requestHistory: HistoryRow[] = [];
  let approvalHistory: ApprovalHistoryRow[] = [];
  let error: string | null = null;
  try {
    const response = await getHistory();
    requestHistory = response.request_history || [];
    approvalHistory = (response.approval_history || []) as ApprovalHistoryRow[];
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "History failed.";
  }

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="Internal Review Tools"
        title="Local workflow history"
        description="Recent local recipe, packet, adjustment, approval, and dry-run actions from the AutoMap backend."
      />
      {error ? <p className="error-text">{error}</p> : null}
      <section className="panel">
        <h3>Request history</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Step</th>
                <th>Status</th>
                <th>Title</th>
                <th>Prompt</th>
                <th>Packet path</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {requestHistory.map((row) => (
                <tr key={row.id}>
                  <td>{row.workflow_step}</td>
                  <td>
                    <StatusChip tone={row.status === "blocked" ? "warning" : "success"}>{row.status}</StatusChip>
                  </td>
                  <td>{row.map_title}</td>
                  <td>{row.raw_prompt}</td>
                  <td className="path-text">{row.packet_path || row.adjusted_packet_path || ""}</td>
                  <td>{row.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <h3>Approval history</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Decision</th>
                <th>Final ready</th>
                <th>Reviewer</th>
                <th>Adjusted packet</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {approvalHistory.map((row, index) => (
                <tr key={`${row.approved_packet_path || row.adjusted_packet_path || index}`}>
                  <td>{String(row.decision || "")}</td>
                  <td>
                    <StatusChip tone={row.final_publish_ready ? "success" : "warning"}>
                      {String(row.final_publish_ready ?? false)}
                    </StatusChip>
                  </td>
                  <td>{String(row.reviewer_name || "")}</td>
                  <td className="path-text">{String(row.adjusted_packet_path || "")}</td>
                  <td>{String(row.created_at || "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
