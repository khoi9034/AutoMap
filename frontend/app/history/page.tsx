import { SectionHeader } from "@/components/section-header";
import { getHistory } from "@/lib/api";
import type { HistoryRow } from "@/types/automap";

export default async function HistoryPage() {
  let requestHistory: HistoryRow[] = [];
  let approvalHistory: unknown[] = [];
  let error: string | null = null;
  try {
    const response = await getHistory();
    requestHistory = response.request_history || [];
    approvalHistory = response.approval_history || [];
  } catch (exc) {
    error = exc instanceof Error ? exc.message : "History failed.";
  }

  return (
    <div className="page-stack">
      <SectionHeader
        eyebrow="History"
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
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {requestHistory.map((row) => (
                <tr key={row.id}>
                  <td>{row.workflow_step}</td>
                  <td>{row.status}</td>
                  <td>{row.map_title}</td>
                  <td>{row.raw_prompt}</td>
                  <td>{row.created_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="panel">
        <h3>Approval history</h3>
        <pre className="json-panel">{JSON.stringify(approvalHistory, null, 2)}</pre>
      </section>
    </div>
  );
}
