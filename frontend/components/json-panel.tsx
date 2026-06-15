type JsonPanelProps = {
  title: string;
  value: unknown;
};

export function JsonPanel({ title, value }: JsonPanelProps) {
  return (
    <div className="panel">
      <h3>{title}</h3>
      <pre className="json-panel">{JSON.stringify(value, null, 2)}</pre>
    </div>
  );
}
