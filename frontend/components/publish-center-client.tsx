"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { PacketPicker } from "@/components/packet-picker";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { dryRunPublish, getPackets, portalSmokeTestDryRun } from "@/lib/api";
import {
  loadWorkflowState,
  mergeWorkflowState,
  packetIdFromPath,
  primaryApprovedPacketPath,
} from "@/lib/workflow-store";
import type { PacketSummary, PacketsResponse } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

export function PublishCenterClient() {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [approvedPacketFolder, setApprovedPacketFolder] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  useEffect(() => {
    const workflow = loadWorkflowState();
    const workflowApprovedPath = primaryApprovedPacketPath(workflow);
    setApprovedPacketFolder(workflowApprovedPath);
    setResult(workflow.dryRunReceipt || workflow.portalSmokeTestReceipt);
    getPackets()
      .then((response) => {
        setPackets(response);
        if (!workflowApprovedPath) {
          setApprovedPacketFolder(response.approved_packets?.[0]?.packet_path || "");
        }
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Packet index failed."));
    mergeWorkflowState({ activeStep: "publish" });
  }, []);

  function onApprovedPacketSelect(packet: PacketSummary) {
    const packetPath = packet.packet_path || "";
    setApprovedPacketFolder(packetPath);
    mergeWorkflowState({
      selectedApprovedPacketId: packet.packet_id || packetIdFromPath(packetPath),
      selectedApprovedPacketPath: packetPath,
      activeStep: "publish",
    });
    setToast({ tone: "success", message: "Approved packet selected." });
  }

  async function run(kind: "publish" | "smoke") {
    if (!approvedPacketFolder) {
      setToast({ tone: "warning", message: "Select an approved packet before running a dry-run action." });
      return;
    }
    setLoading(kind);
    setError(null);
    try {
      const response =
        kind === "publish"
          ? await dryRunPublish(approvedPacketFolder)
          : await portalSmokeTestDryRun(approvedPacketFolder);
      setResult(response);
      mergeWorkflowState(
        kind === "publish"
          ? { dryRunReceipt: response, activeStep: "publish" }
          : { portalSmokeTestReceipt: response, activeStep: "publish" },
      );
      setToast({
        tone: "success",
        message: kind === "publish" ? "Dry-run publish completed." : "Portal smoke-test dry-run completed.",
      });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Dry-run action failed.");
      setToast({ tone: "danger", message: "Dry-run action blocked or failed. Review the message below." });
    } finally {
      setLoading(null);
    }
  }

  const selectedApprovedPacket = packets?.approved_packets?.find((packet) => packet.packet_path === approvedPacketFolder);

  return (
    <div className="page-stack">
      <section className="panel form-grid">
        <PacketPicker
          label="Approved packet"
          packetType="approved"
          value={approvedPacketFolder}
          onSelect={onApprovedPacketSelect}
        />
        <div className="chip-row">
          <StatusChip tone="success">Frontend actions are dry-run only</StatusChip>
          <StatusChip tone="warning">Real publish remains CLI-only</StatusChip>
          <StatusChip tone={selectedApprovedPacket?.final_publish_ready ? "success" : "warning"}>
            final_publish_ready: {String(selectedApprovedPacket?.final_publish_ready ?? false)}
          </StatusChip>
        </div>
        <div className="button-row">
          <button className="button" type="button" onClick={() => run("publish")} disabled={!approvedPacketFolder || !!loading}>
            {loading === "publish" ? "Running..." : "Dry-Run Publish"}
          </button>
          <button className="button button-secondary" type="button" onClick={() => run("smoke")} disabled={!approvedPacketFolder || !!loading}>
            {loading === "smoke" ? "Running..." : "Portal Smoke-Test Dry-Run"}
          </button>
          <Link className="button button-secondary" href="/reports">
            Generate Report
          </Link>
        </div>
        <p className="muted">
          No real publish button is exposed. No ArcGIS login is required in the frontend. Dry-run checks do not create
          public items and do not share to the organization.
        </p>
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast} />
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
