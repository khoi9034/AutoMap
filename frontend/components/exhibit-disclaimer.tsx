export function ExhibitDisclaimer({ text }: { text?: string }) {
  return (
    <div className="exhibit-disclaimer">
      <strong>DRAFT - For GIS review only</strong>
      <p>{text || "This map exhibit is a local AutoMap draft. It is not an official county map and nothing is published."}</p>
    </div>
  );
}
