"use client";

import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { StatusChip } from "@/components/status-chip";
import { dryRunPublish, getPackets, portalSmokeTestDryRun } from "@/lib/api";
import type { PacketsResponse } from "@/types/automap";

export function PublishCenterClient() {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [approvedPacketFolder, setApprovedPacketFolder] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  useEffect(() => {
    getPackets()
      .then((response) => {
        setPackets(response);
        setApprovedPacketFolder(response.approved_packets?.[0]?.packet_path || "");
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Packet index failed."));
  }, []);

  async function run(kind: "publish" | "smoke") {
    setLoading(kind);
    setError(null);
    try {
      const response =
        kind === "publish"
          ? await dryRunPublish(approvedPacketFolder)
          : await portalSmokeTestDryRun(approvedPacketFolder);
      setResult(response);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Dry-run action failed.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="panel form-grid">
        <label htmlFor="approved-packet-select">
          <strong>Approved packet</strong>
        </label>
        <select
          id="approved-packet-select"
          className="select-input"
          value={approvedPacketFolder}
          onChange={(event) => setApprovedPacketFolder(event.target.value)}
        >
          {(packets?.approved_packets || []).map((packet) => (
            <option key={packet.packet_path} value={packet.packet_path}>
              {packet.map_title || packet.packet_id}
            </option>
          ))}
        </select>
        <div className="chip-row">
          <StatusChip tone="success">Frontend actions are dry-run only</StatusChip>
          <StatusChip tone="warning">Real publish remains CLI-only</StatusChip>
        </div>
        <div className="button-row">
          <button className="button" type="button" onClick={() => run("publish")} disabled={!approvedPacketFolder || !!loading}>
            {loading === "publish" ? "Running..." : "Dry-Run Publish"}
          </button>
          <button className="button button-secondary" type="button" onClick={() => run("smoke")} disabled={!approvedPacketFolder || !!loading}>
            {loading === "smoke" ? "Running..." : "Portal Smoke-Test Dry-Run"}
          </button>
        </div>
        <p className="muted">No real publish button is exposed. No ArcGIS login is required in the frontend.</p>
        {error ? <p className="error-text">{error}</p> : null}
      </section>

      <section className="panel">
        <h3>Approved packets</h3>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Packet</th>
                <th>Final ready</th>
                <th>Publish receipt</th>
                <th>Smoke receipt</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {(packets?.approved_packets || []).map((packet) => (
                <tr key={packet.packet_path}>
                  <td>{packet.map_title || packet.packet_id}</td>
                  <td>
                    <StatusChip tone={packet.final_publish_ready ? "success" : "warning"}>
                      {String(packet.final_publish_ready ?? false)}
                    </StatusChip>
                  </td>
                  <td>{packet.latest_publish_receipt?.exists ? packet.latest_publish_receipt.status || "exists" : "none"}</td>
                  <td>{packet.latest_smoke_test_receipt?.exists ? "dry-run receipt" : "none"}</td>
                  <td>{packet.updated_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {result ? <JsonPanel title="Latest dry-run receipt summary" value={result} /> : null}
    </div>
  );
}
