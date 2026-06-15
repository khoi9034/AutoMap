"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { PacketPicker } from "@/components/packet-picker";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { applyAdjustments, createAdjustmentTemplate } from "@/lib/api";
import {
  loadWorkflowState,
  mergeWorkflowState,
  packetIdFromPath,
  primaryReviewPacketPath,
  stringField,
} from "@/lib/workflow-store";
import type { PacketSummary } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

export function AdjustmentsClient() {
  const [packetFolder, setPacketFolder] = useState("");
  const [yaml, setYaml] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  useEffect(() => {
    const workflow = loadWorkflowState();
    setPacketFolder(primaryReviewPacketPath(workflow));
    if (workflow.adjustmentTemplate && typeof workflow.adjustmentTemplate.adjustment_yaml === "string") {
      setYaml(workflow.adjustmentTemplate.adjustment_yaml);
    }
    if (workflow.adjustedPacket) {
      setResult(workflow.adjustedPacket);
    }
    mergeWorkflowState({ activeStep: "adjustments" });
  }, []);

  function onPacketSelect(packet: PacketSummary) {
    const packetPath = packet.packet_path || "";
    setPacketFolder(packetPath);
    mergeWorkflowState({
      selectedPacketId: packet.packet_id || packetIdFromPath(packetPath),
      selectedPacketPath: packetPath,
      activeStep: "adjustments",
    });
    setToast({ tone: "success", message: "Review packet selected." });
  }

  async function onTemplate() {
    setLoading(true);
    setError(null);
    try {
      const response = await createAdjustmentTemplate(packetFolder);
      setYaml(String(response.adjustment_yaml || ""));
      setResult(response);
      mergeWorkflowState({ adjustmentTemplate: response, activeStep: "adjustments" });
      setToast({ tone: "success", message: "Adjustment template created." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Adjustment template failed.");
    } finally {
      setLoading(false);
    }
  }

  async function onApply() {
    setLoading(true);
    setError(null);
    try {
      const response = await applyAdjustments(packetFolder, yaml);
      setResult(response);
      const adjustedPath = stringField(response, ["adjusted_path", "adjusted_packet_path"]);
      mergeWorkflowState({
        adjustedPacket: response,
        selectedAdjustedPacketPath: adjustedPath,
        selectedAdjustedPacketId: packetIdFromPath(adjustedPath),
        activeStep: "approval",
      });
      setToast({ tone: "success", message: "Adjustments applied. Adjusted packet created separately." });
      window.localStorage.setItem("automap:lastAdjustedPacket", JSON.stringify(response));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Apply adjustments failed.");
    } finally {
      setLoading(false);
    }
  }

  const validation = (result?.validation || {}) as { is_valid?: boolean; errors?: string[] };
  const adjustedWarnings = (result?.adjusted_warnings || {}) as {
    publish_ready?: boolean;
    active?: Record<string, unknown>;
    audit_trail?: unknown[];
  };

  return (
    <div className="page-stack">
      <section className="panel form-grid">
        <PacketPicker label="Review packet" packetType="review" value={packetFolder} onSelect={onPacketSelect} />
        <textarea className="yaml-editor" value={yaml} onChange={(event) => setYaml(event.target.value)} />
        <div className="button-row">
          <button className="button" type="button" onClick={onTemplate} disabled={!packetFolder || loading}>
            Create Adjustment Template
          </button>
          <button className="button button-secondary" type="button" onClick={onApply} disabled={!packetFolder || !yaml || loading}>
            Apply Adjustments
          </button>
        </div>
        <p className="muted">The original review packet is preserved; adjusted packets are created separately.</p>
        {error ? <p className="error-text">{error}</p> : null}
        <ToastMessage toast={toast} />
      </section>
      {result ? (
        <section className="stats-grid">
          <div className="panel">
            <h3>Adjusted packet</h3>
            <p className="path-text">{String(result.adjusted_path || "")}</p>
            <StatusChip tone={validation.is_valid ? "success" : "warning"}>
              validation: {String(validation.is_valid ?? false)}
            </StatusChip>
          </div>
          <div className="panel">
            <h3>Publish ready flag</h3>
            <StatusChip tone={adjustedWarnings.publish_ready ? "success" : "warning"}>
              publish_ready: {String(adjustedWarnings.publish_ready ?? false)}
            </StatusChip>
            <p className="muted">This flag never publishes anything from the frontend.</p>
          </div>
          <div className="panel">
            <h3>Audit notes</h3>
            <p>{(adjustedWarnings.audit_trail || []).length} audit entries recorded.</p>
            {validation.errors?.length ? <p className="error-text">{validation.errors.join("; ")}</p> : null}
          </div>
        </section>
      ) : null}
      {result?.adjusted_path ? (
        <section className="panel">
          <h3>Next steps</h3>
          <div className="button-row">
            <Link className="button" href="/map-preview">
              Preview Adjusted Map
            </Link>
            <Link className="button button-secondary" href="/approval">
              Go to Approval
            </Link>
            <Link className="button button-secondary" href="/reports">
              Generate Report
            </Link>
          </div>
        </section>
      ) : null}
      {result ? <JsonPanel title="Adjustment result" value={result} /> : null}
    </div>
  );
}
