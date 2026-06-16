import { StatusChip } from "@/components/status-chip";
import type { ParcelMatchSummary } from "@/types/automap";

type ParcelCandidateTableProps = {
  candidates?: ParcelMatchSummary[];
};

export function ParcelCandidateTable({ candidates = [] }: ParcelCandidateTableProps) {
  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Ambiguous candidates</h3>
          <p className="muted">AutoMap shows candidates when an address or identifier is not unique.</p>
        </div>
        <StatusChip tone={candidates.length ? "warning" : "default"}>{candidates.length}</StatusChip>
      </div>
      {candidates.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Identifier</th>
                <th>PIN / Parcel</th>
                <th>Address</th>
                <th>Review</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate, index) => (
                <tr key={`${candidate.pin14 || candidate.pin || candidate.parcel_id || "candidate"}-${index}`}>
                  <td>{candidate.input_identifier?.value || candidate.count || "candidate"}</td>
                  <td>{candidate.pin14 || candidate.pin || candidate.parcel_id || candidate.object_id || "-"}</td>
                  <td>{candidate.address || "-"}</td>
                  <td>{candidate.needs_review ? "needs review" : "candidate"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="muted">No ambiguous candidates returned.</p>
      )}
    </section>
  );
}
