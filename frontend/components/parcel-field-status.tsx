import { StatusChip } from "@/components/status-chip";
import type { ParcelFieldProfileResponse } from "@/types/automap";

type ParcelFieldStatusProps = {
  profile?: ParcelFieldProfileResponse | null;
  loading?: boolean;
  onProfile: () => void;
};

function roleSummary(fieldsByRole?: Record<string, string[]>): string {
  if (!fieldsByRole) {
    return "not profiled";
  }
  const entries = Object.entries(fieldsByRole).filter(([, fields]) => fields.length > 0);
  return entries.length ? entries.map(([role, fields]) => `${role}: ${fields.join(", ")}`).join(" | ") : "no verified roles";
}

export function ParcelFieldStatus({ profile, loading, onProfile }: ParcelFieldStatusProps) {
  const parcelMap = profile?.parcel_field_map;
  const addressMap = profile?.address_field_map;
  return (
    <section className="panel">
      <div className="panel-title-row">
        <div>
          <h3>Verified field profile</h3>
          <p className="muted">AutoMap maps parcel and address roles from catalog metadata before matching.</p>
        </div>
        <StatusChip tone={parcelMap?.layer_key ? "success" : "warning"}>
          {parcelMap?.layer_key ? "profiled" : "needs profile"}
        </StatusChip>
      </div>
      <div className="stack-small">
        <p>
          <strong>Tax Parcels:</strong> {parcelMap?.layer_name || "not loaded"}
        </p>
        <p className="muted">{roleSummary(parcelMap?.fields_by_role)}</p>
        <p>
          <strong>Addresses:</strong> {addressMap?.layer_name || "not loaded"}
        </p>
        <p className="muted">{roleSummary(addressMap?.fields_by_role)}</p>
      </div>
      <button className="button button-secondary" type="button" onClick={onProfile} disabled={loading}>
        {loading ? "Profiling..." : "Profile Parcel Fields"}
      </button>
    </section>
  );
}
