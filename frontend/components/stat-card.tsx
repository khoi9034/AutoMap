type StatCardProps = {
  label: string;
  value: string | number | boolean | null | undefined;
  note?: string;
};

export function StatCard({ label, value, note }: StatCardProps) {
  return (
    <div className="stat-card">
      <p>{label}</p>
      <strong>{String(value ?? "0")}</strong>
      {note ? <span>{note}</span> : null}
    </div>
  );
}
