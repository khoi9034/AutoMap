import { StatusChip } from "@/components/status-chip";
import type { ScenarioVariant } from "@/types/automap";

type ScenarioVariantCardProps = {
  variant?: ScenarioVariant | null;
  onSelect?: (variant: ScenarioVariant) => void;
};

function safetyTone(level?: string): "default" | "success" | "warning" | "danger" {
  if (level === "safe") {
    return "success";
  }
  if (level === "blocked") {
    return "danger";
  }
  return "warning";
}

export function ScenarioVariantCard({ variant, onSelect }: ScenarioVariantCardProps) {
  if (!variant) {
    return (
      <section className="panel">
        <h3>Scenario variant</h3>
        <p className="muted">Create a variant to review tuned weights and safety warnings.</p>
      </section>
    );
  }

  const weights = variant.factor_weights || [];

  return (
    <article className="mini-card">
      <div className="panel-title-row">
        <div>
          <h3>{variant.variant_name || "Scenario variant"}</h3>
          <p className="muted">{variant.variant_description || variant.variant_id}</p>
        </div>
        <StatusChip tone={safetyTone(variant.safety_level)}>{variant.safety_level || "review_needed"}</StatusChip>
      </div>
      <div className="stat-grid">
        <div>
          <span>Factors</span>
          <strong>{weights.length}</strong>
        </div>
        <div>
          <span>Disabled</span>
          <strong>{variant.disabled_factors?.length || 0}</strong>
        </div>
        <div>
          <span>Warnings</span>
          <strong>{variant.safety_warnings?.length || 0}</strong>
        </div>
      </div>
      <div className="mini-list">
        {weights.slice(0, 5).map((factor) => (
          <div key={factor.factor_key}>
            <strong>{factor.factor_label || factor.factor_key}</strong>
            <span>
              reviewer weight {factor.reviewer_weight ?? 0} · normalized {factor.normalized_percent ?? 0}%
            </span>
          </div>
        ))}
      </div>
      {(variant.safety_warnings || []).length ? (
        <div className="notice notice-warning">
          <strong>Review warnings</strong>
          <ul className="plain-list">
            {(variant.safety_warnings || []).slice(0, 4).map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {onSelect ? (
        <button className="button button-secondary" type="button" onClick={() => onSelect(variant)}>
          Use Variant
        </button>
      ) : null}
    </article>
  );
}
