import type { ParcelReport } from "@/types/automap";

type ParcelReportCardProps = {
  report?: ParcelReport | null;
};

export function ParcelReportCard({ report }: ParcelReportCardProps) {
  return (
    <section className="panel report-card">
      <h3>Parcel report</h3>
      {!report ? (
        <p className="muted">Generate a parcel report after creating a parcel set.</p>
      ) : (
        <>
          <p className="muted">{report.report_folder}</p>
          <div className="report-link-grid">
            {(report.files || []).map((file) => (
              <a key={file.path || file.name} href={file.url || "#"} target="_blank" rel="noreferrer">
                {file.name}
              </a>
            ))}
          </div>
          <p className="muted">Published: {String(report.published || false)}</p>
        </>
      )}
    </section>
  );
}
