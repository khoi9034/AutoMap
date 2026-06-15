"use client";

import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { StatusChip } from "@/components/status-chip";
import { applyApproval, createApprovalTemplate, getPackets } from "@/lib/api";
import type { PacketsResponse } from "@/types/automap";

export function ApprovalClient() {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [adjustedPacketFolder, setAdjustedPacketFolder] = useState("");
  const [yaml, setYaml] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getPackets()
      .then((response) => {
        setPackets(response);
        setAdjustedPacketFolder(response.adjusted_packets?.[0]?.packet_path || "");
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Packet index failed."));
  }, []);

  async function onTemplate() {
    setLoading(true);
    setError(null);
    try {
      const response = await createApprovalTemplate(adjustedPacketFolder);
      setYaml(String(response.approval_yaml || ""));
      setResult(response);
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
      window.localStorage.setItem("automap:lastApprovedPacket", JSON.stringify(response));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Apply approval failed.");
    } finally {
      setLoading(false);
    }
  }

  const receipt = (result?.approval_receipt || {}) as { final_publish_ready?: boolean; block_reasons?: string[] };
  const validation = (result?.validation || {}) as { is_valid?: boolean; errors?: string[] };

  return (
    <div className="page-stack">
      <section className="panel form-grid">
        <label htmlFor="adjusted-packet-select">
          <strong>Adjusted packet</strong>
        </label>
        <select
          id="adjusted-packet-select"
          className="select-input"
          value={adjustedPacketFolder}
          onChange={(event) => setAdjustedPacketFolder(event.target.value)}
        >
          {(packets?.adjusted_packets || []).map((packet) => (
            <option key={packet.packet_path} value={packet.packet_path}>
              {packet.map_title || packet.packet_id}
            </option>
          ))}
        </select>
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
        </section>
      ) : null}
      {result ? <JsonPanel title="Approval result" value={result} /> : null}
    </div>
  );
}
