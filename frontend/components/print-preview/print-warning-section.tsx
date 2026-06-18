import type { ComposerMapState, ComposerResponse } from "@/types/automap";

type PrintWarningSectionProps = {
  mapState?: ComposerMapState | null;
  response?: ComposerResponse | null;
};

export function printWarningItems(mapState?: ComposerMapState | null, response?: ComposerResponse | null): string[] {
  return Array.from(
    new Set(
      [
        ...(mapState?.warnings || []),
        ...(response?.warnings || []),
        ...(response?.preview_blockers || []),
        ...(mapState?.missing_data || []),
        ...(response?.missing_data || []).map((item) => `Missing data: ${item}`),
        "Draft only - not an official county map.",
        "No ArcGIS item was published.",
      ].filter(Boolean),
    ),
  );
}

export function PrintWarningSection({ mapState, response }: PrintWarningSectionProps) {
  const warnings = printWarningItems(mapState, response);
  return (
    <section className="print-preview-sheet print-preview-section">
      <h2>Warnings and Limitations</h2>
      <ul className="print-preview-list">
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
    </section>
  );
}
