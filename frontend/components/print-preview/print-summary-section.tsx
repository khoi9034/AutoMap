type SummaryItem = {
  label: string;
  value: string;
};

type PrintSummarySectionProps = {
  title: string;
  items: SummaryItem[];
  note?: string;
};

export function PrintSummarySection({ title, items, note }: PrintSummarySectionProps) {
  return (
    <section className="print-preview-sheet print-preview-section">
      <h2>{title}</h2>
      {note ? <p className="muted">{note}</p> : null}
      <dl className="print-preview-summary-grid">
        {items.map((item) => (
          <div key={`${title}-${item.label}`}>
            <dt>{item.label}</dt>
            <dd>{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
