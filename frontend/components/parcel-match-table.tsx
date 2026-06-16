import { StatusChip } from "@/components/status-chip";
import type { ParcelParseResult, ParcelSet } from "@/types/automap";

type ParcelMatchTableProps = {
  parseResult?: ParcelParseResult | null;
  parcelSet?: ParcelSet | null;
};

function identifierLabel(value: unknown): string {
  if (!value || typeof value !== "object") {
    return String(value ?? "");
  }
  const item = value as { value?: string; normalized_value?: string; identifier_type?: string };
  return `${item.identifier_type || "identifier"}: ${item.value || item.normalized_value || ""}`;
}

export function ParcelMatchTable({ parseResult, parcelSet }: ParcelMatchTableProps) {
  const parsed = parseResult?.parsed_identifiers || [];
  const addresses = parseResult?.address_candidates || [];
  const matched = parcelSet?.matched_parcels || [];
  const unmatched = parcelSet?.unmatched_identifiers || [];

  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Parsed and matched parcels</h3>
          <p className="muted">Matching starts with returnGeometry=false. Geometry is not downloaded here.</p>
        </div>
        <StatusChip tone={parcelSet?.match_status === "matched" ? "success" : parcelSet ? "warning" : "default"}>
          {parcelSet?.match_status || parseResult?.input_type || "not parsed"}
        </StatusChip>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>Value</th>
              <th>Status</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {[...parsed, ...addresses].map((identifier, index) => (
              <tr key={`${identifier.identifier_type}-${identifier.normalized_value}-${index}`}>
                <td>{identifier.identifier_type}</td>
                <td>{identifier.value || identifier.normalized_value}</td>
                <td>{identifier.needs_review ? "needs review" : "parsed"}</td>
                <td>{identifier.notes?.join("; ") || "Ready for safe matching."}</td>
              </tr>
            ))}
            {matched.map((parcel, index) => (
              <tr key={`match-${index}`}>
                <td>matched</td>
                <td>{parcel.pin14 || parcel.pin || parcel.parcel_id || parcel.object_id || "parcel record"}</td>
                <td>matched</td>
                <td>{parcel.address || parcel.source_layer_key || "Matched from verified Tax Parcels layer."}</td>
              </tr>
            ))}
            {unmatched.map((identifier, index) => (
              <tr key={`unmatched-${index}`}>
                <td>unmatched</td>
                <td>{identifierLabel(identifier)}</td>
                <td>review</td>
                <td>No safe match returned from verified fields.</td>
              </tr>
            ))}
            {!parsed.length && !addresses.length && !matched.length && !unmatched.length ? (
              <tr>
                <td colSpan={4}>No parsed parcel inputs yet.</td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
