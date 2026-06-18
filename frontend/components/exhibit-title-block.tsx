import { ExhibitDisclaimer } from "@/components/exhibit-disclaimer";

type ExhibitTitleBlockProps = {
  title: string;
  subtitle?: string;
  prompt?: string;
  preparedBy?: string;
  generatedAt?: string;
  mapType?: string;
  requestType?: string;
  sessionId?: string;
  disclaimer?: string;
};

function displayMapType(value?: string): string {
  return value ? value.replaceAll("_", " ") : "general reference exhibit";
}

export function ExhibitTitleBlock({
  title,
  subtitle,
  prompt,
  preparedBy = "AutoMap Draft",
  generatedAt,
  mapType,
  requestType,
  sessionId,
  disclaimer,
}: ExhibitTitleBlockProps) {
  return (
    <header className="exhibit-title-block">
      <div className="exhibit-title-main">
        <p className="eyebrow">County GIS exhibit</p>
        <span className="exhibit-draft-badge">DRAFT - For GIS review only</span>
        <h1>{title}</h1>
        {subtitle ? <p className="exhibit-subtitle">{subtitle}</p> : null}
        {prompt ? <p className="exhibit-prompt">{prompt}</p> : null}
      </div>
      <ExhibitDisclaimer text={disclaimer} />
      <dl className="exhibit-title-meta">
        <div>
          <dt>Prepared by</dt>
          <dd>{preparedBy}</dd>
        </div>
        <div>
          <dt>Generated</dt>
          <dd>{generatedAt || "Not recorded"}</dd>
        </div>
        <div>
          <dt>Map type</dt>
          <dd>{displayMapType(mapType)}</dd>
        </div>
        <div>
          <dt>Request</dt>
          <dd>{requestType || "general_map"}</dd>
        </div>
        {sessionId ? (
          <div>
            <dt>Session</dt>
            <dd>{sessionId}</dd>
          </div>
        ) : null}
      </dl>
    </header>
  );
}
