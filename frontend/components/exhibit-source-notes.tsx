export function ExhibitSourceNotes({ notes }: { notes?: string[] }) {
  const rows = notes?.length
    ? notes
    : [
        "Source layers and local derived outputs are documented in the layer source table.",
        "Local derived outputs remain on this workstation and are not uploaded or published.",
        "Proxy or reference layers are context only unless reviewed by GIS staff.",
      ];

  return (
    <section className="exhibit-source-notes">
      <h2>Source notes</h2>
      <ul>
        {rows.map((note) => (
          <li key={note}>{note}</li>
        ))}
      </ul>
    </section>
  );
}
