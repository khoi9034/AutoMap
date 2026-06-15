"use client";

import { useEffect, useMemo, useState } from "react";

import { ReportCard } from "@/components/report-card";
import { ReportPreview } from "@/components/report-preview";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { generateReport, getReport, getReports, listPackets } from "@/lib/api";
import type { PacketSummary, PacketsResponse, ReportDetail, ReportSummary } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

type PacketGroup = {
  label: string;
  rows: PacketSummary[];
};

function packetGroups(packets: PacketsResponse | null): PacketGroup[] {
  return [
    { label: "Approved packets", rows: packets?.approved_packets || [] },
    { label: "Adjusted packets", rows: packets?.adjusted_packets || [] },
    { label: "Review packets", rows: packets?.review_packets || [] },
  ];
}

function packetPath(packet: PacketSummary): string {
  return packet.packet_path || "";
}

function displayDate(value: string | undefined): string {
  if (!value) {
    return "Not recorded";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function ReportCenterClient() {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [selectedReport, setSelectedReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  const latestPackets = useMemo(() => packetGroups(packets), [packets]);

  async function refreshReports() {
    const response = await getReports();
    setReports(response.reports || []);
  }

  useEffect(() => {
    Promise.all([listPackets(), getReports()])
      .then(([packetResponse, reportResponse]) => {
        setPackets(packetResponse);
        setReports(reportResponse.reports || []);
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Report Center failed to load."));
  }, []);

  async function onGenerate(packet: PacketSummary) {
    const sourcePath = packetPath(packet);
    if (!sourcePath) {
      setToast({ tone: "warning", message: "Packet path is missing, so a report cannot be generated." });
      return;
    }
    setLoading(sourcePath);
    setError(null);
    try {
      const generated = await generateReport(sourcePath);
      await refreshReports();
      if (generated.report_id) {
        const detail = await getReport(generated.report_id);
        setSelectedReport(detail);
      }
      setToast({ tone: "success", message: "Report package generated under outputs/reports." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Report generation failed.");
      setToast({ tone: "danger", message: "Report generation failed. Review the message below." });
    } finally {
      setLoading(null);
    }
  }

  async function onPreview(reportId: string) {
    setLoading(reportId);
    setError(null);
    try {
      setSelectedReport(await getReport(reportId));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Report preview failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Local exports only</strong>
        <p>Reports are review artifacts. They do not publish to ArcGIS, do not require ArcGIS login, and do not create items.</p>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          {latestPackets.map((group) => (
            <section className="panel" key={group.label}>
              <div className="panel-title-row">
                <div>
                  <h3>{group.label}</h3>
                  <p className="muted">Generate local reports from recent workflow packet outputs.</p>
                </div>
                <StatusChip>{group.rows.length} available</StatusChip>
              </div>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Packet</th>
                      <th>Status</th>
                      <th>Updated</th>
                      <th>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {group.rows.slice(0, 8).map((packet) => (
                      <tr key={packet.packet_path || packet.packet_id}>
                        <td>
                          <strong>{packet.map_title || packet.packet_id}</strong>
                          <p className="path-text">{packet.packet_path}</p>
                        </td>
                        <td>
                          <StatusChip tone={packet.final_publish_ready ? "success" : "warning"}>
                            {packet.packet_type || "packet"}
                          </StatusChip>
                        </td>
                        <td>{displayDate(packet.updated_at)}</td>
                        <td>
                          <button
                            className="button button-secondary"
                            type="button"
                            onClick={() => onGenerate(packet)}
                            disabled={!packetPath(packet) || loading === packetPath(packet)}
                          >
                            {loading === packetPath(packet) ? "Generating..." : "Generate Report"}
                          </button>
                        </td>
                      </tr>
                    ))}
                    {!group.rows.length ? (
                      <tr>
                        <td colSpan={4}>No {group.label.toLowerCase()} found.</td>
                      </tr>
                    ) : null}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
        </div>

        <aside className="dashboard-side">
          <section className="panel safety-card">
            <h3>Export formats</h3>
            <ul className="check-list">
              <li>HTML summary</li>
              <li>Markdown summary</li>
              <li>JSON report data</li>
              <li>CSV layer table</li>
              <li>JSON warning report</li>
            </ul>
            <p className="muted">PDF export is not enabled in v1.7 unless a reliable local PDF path is added later.</p>
          </section>
          <section className="panel">
            <h3>Latest generated reports</h3>
            <div className="mini-list">
              {reports.slice(0, 6).map((report) => (
                <div key={report.report_id}>
                  <strong>{report.generated_map_title || report.report_title || report.report_id}</strong>
                  <button className="small-button" type="button" onClick={() => onPreview(report.report_id || "")}>
                    Preview
                  </button>
                </div>
              ))}
              {!reports.length ? <p className="muted">No reports generated yet.</p> : null}
            </div>
          </section>
        </aside>
      </section>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Report Center issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
      <ToastMessage toast={toast} />

      <section className="report-grid">
        {reports.slice(0, 6).map((report) => (
          <ReportCard report={report} key={report.report_id} onPreview={onPreview} />
        ))}
      </section>

      <ReportPreview report={selectedReport} />
    </div>
  );
}
