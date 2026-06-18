export function ExhibitWarningSummary({ warnings }: { warnings: string[] }) {
  return (
    <section className="exhibit-warning-summary">
      <h2>Warnings and limitations</h2>
      {warnings.length ? (
        <ul>
          {warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : (
        <p>No warnings recorded.</p>
      )}
    </section>
  );
}
