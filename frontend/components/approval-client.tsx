"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { PacketPicker } from "@/components/packet-picker";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { applyApproval, createApprovalTemplate } from "@/lib/api";
import {
  loadWorkflowState,
  mergeWorkflowState,
  packetIdFromPath,
  primaryAdjustedPacketPath,
  stringField,
} from "@/lib/workflow-store";
import type { PacketSummary } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

export function ApprovalClient() {
  const [adjustedPacketFolder, setAdjustedPacketFolder] = useState("");
  const [yaml, setYaml] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  useEffect(() => {
    const workflow = loadWorkflowState();
    setAdjustedPacketFolder(primaryAdjustedPacketPath(workflow));
    if (workflow.approvalTemplate && typeof workflow.approvalTemplate.approval_yaml === "string") {
      setYaml(workflow.approvalTemplate.approval_yaml);
    }
    if (workflow.approvedPacket) {
      setResult(workflow.approvedPacket);
    }
    mergeWorkflowState({ activeStep: "approval" });
  }, []);

  function onAdjustedPacketSelect(packet: PacketSummary) {
    const packetPath = packet.packet_path || "";
    setAdjustedPacketFolder(packetPath);
    mergeWorkflowState({
      selectedAdjustedPacketId: packet.packet_id || packetIdFromPath(packetPath),
      selectedAdjustedPacketPath: packetPath,
      activeStep: "approval",
    });
    setToast({ tone: "success", message: "Adjusted packet selected." });
  }

  async function onTemplate() {
    setLoading(true);
    setError(null);
    try {
      const response = await createApprovalTemplate(adjustedPacketFolder);
      setYaml(String(response.approval_yaml || ""));
      setResult(response);
      mergeWorkflowState({ approvalTemplate: response, activeStep: "approval" });
      setToast({ tone: "success", message: "Approval template created." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Approval template failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onApply() {
    setLoading(true);
    setError(null);
    try {
      const response = await applyApproval(adjustedPacketFolder, yaml);
      setResult(response);
      const approvedPath = stringField(response, ["approved_path", "approved_packet_path"]);
      mergeWorkflowState({
        approvedPacket: response,
        selectedApprovedPacketPath: approvedPath,
        selectedApprovedPacketId: packetIdFromPath(approvedPath),
        activeStep: "publish",
      });
      setToast({ tone: "success", message: "Approval applied and approved packet saved to workflow state." });
      window.localStorage.setItem("automap:lastApprovedPacket", JSON.stringify(response));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Apply approval failed.");
    } finally {
      setLoading(false);
    }
  }

  const receipt = (result?.approval_receipt || {}) as {
    final_publish_ready?: boolean;
    block_reasons?: string[];
    reviewer_notes?: string[];
  };
  const validation = (result?.validation || {}) as { is_valid?: boolean; errors?: string[] };

  return (
    <div className="page-stack">
      <section className="panel form-grid">
        <PacketPicker
          label="Adjusted packet"
          packetType="adjusted"
          value={adjustedPacketFolder}
          onSelect={onAdjustedPacketSelect}
        />
        <textarea className="yaml-editor" value={yaml} onChange={(event) => setYaml(event.target.value)} />
        <div className="button-row">
          <button className="button" type="button" onClick={onTemplate} disabled={!adjustedPacketFolder || loading}>
            Create Approval Template
          </button>
          <button className="button button-secondary" type="button" onClick={onApply} disabled={!adjustedPacketFolder || !yaml || loading}>
            Apply Approval
          </button>
        </div>
        <div className="chip-row">
          <StatusChip tone={receipt.final_publish_ready ? "success" : "warning"}>
            final_publish_ready: {String(receipt.final_publish_ready ?? false)}
          </StatusChip>
        </div>
        {receipt.block_reasons?.length ? <p className="muted">Block reasons: {receipt.block_reasons.join("; ")}</p> : null}
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast} />
      </section>
      {result ? (
        <section className="stats-grid">
          <div className="panel">
            <h3>Approved packet</h3>
            <p className="path-text">{String(result.approved_path || "")}</p>
          </div>
          <div className="panel">
            <h3>Validation</h3>
            <StatusChip tone={validation.is_valid ? "success" : "warning"}>
              is_valid: {String(validation.is_valid ?? false)}
            </StatusChip>
            {validation.errors?.length ? <p className="error-text">{validation.errors.join("; ")}</p> : null}
          </div>
          <div className="panel">
            <h3>Block reasons</h3>
            {receipt.block_reasons?.length ? (
              <ul className="compact-list">
                {receipt.block_reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">No block reasons in the latest approval receipt.</p>
            )}
          </div>
          <div className="panel">
            <h3>Reviewer notes</h3>
            {receipt.reviewer_notes?.length ? (
              <ul className="compact-list">
                {receipt.reviewer_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            ) : (
              <p className="muted">No reviewer notes in the latest approval receipt.</p>
            )}
          </div>
        </section>
      ) : null}
      {result?.approved_path ? (
        <section className="panel">
          <h3>Next step</h3>
          <div className="button-row">
            <Link className="button" href="/publish-center">
              Go to Publish Center
            </Link>
            <Link className="button button-secondary" href="/reports">
              Generate Report
            </Link>
          </div>
        </section>
      ) : null}
      {result ? <JsonPanel title="Approval result" value={result} /> : null}
    </div>
  );
}
