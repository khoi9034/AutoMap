export function PrintSourceNotesSection() {
  return (
    <section className="print-preview-sheet print-preview-section">
      <h2>Source Notes</h2>
      <ul className="print-preview-list">
        <li>Visible context layers come from the verified AutoMap layer catalog.</li>
        <li>Local derived overlays remain on this machine and are not uploaded or published.</li>
        <li>Proxy sources are context only unless separately reviewed.</li>
        <li>No database URLs, secrets, or CFS references are included in export outputs.</li>
      </ul>
    </section>
  );
}
