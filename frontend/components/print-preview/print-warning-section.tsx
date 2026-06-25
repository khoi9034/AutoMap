import type { ComposerMapState, ComposerResponse } from "@/types/automap";

type PrintWarningSectionProps = {
  mapState?: ComposerMapState | null;
  response?: ComposerResponse | null;
};

export function printWarningItems(mapState?: ComposerMapState | null, response?: ComposerResponse | null): string[] {
  const routeMode = String(mapState?.proximity_summary?.route_mode || response?.proximity_result?.route_mode || "");
  const roadNetworkRoute = routeMode === "road_network" || routeMode === "road_following_draft";
  const staleStraightLineWarning = (warning: string) => {
    const normalized = warning.toLowerCase();
    return roadNetworkRoute && (normalized.includes("straight-line") || normalized.includes("straight line"));
  };
  const normalizedWarningText = (warning: string) => {
    const normalized = warning.toLowerCase();
    if (normalized.includes("related parcel") && normalized.includes("not resolved")) {
      return "Address matched. Related parcel was not resolved from verified fields, so the origin marker is shown as an address point.";
    }
    return warning;
  };

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
      ]
        .filter((warning): warning is string => Boolean(warning) && !staleStraightLineWarning(String(warning)))
        .map((warning) => normalizedWarningText(String(warning))),
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
