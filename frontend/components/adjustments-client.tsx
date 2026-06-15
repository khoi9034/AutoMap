"use client";

import { useEffect, useState } from "react";

import { JsonPanel } from "@/components/json-panel";
import { StatusChip } from "@/components/status-chip";
import { applyAdjustments, createAdjustmentTemplate, getPackets } from "@/lib/api";
import type { PacketsResponse } from "@/types/automap";

export function AdjustmentsClient() {
  const [packets, setPackets] = useState<PacketsResponse | null>(null);
  const [packetFolder, setPacketFolder] = useState("");
  const [yaml, setYaml] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getPackets()
      .then((response) => {
        setPackets(response);
        const first = response.review_packets?.[0]?.packet_path || "";
        setPacketFolder(first);
      })
      .catch((exc) => setError(exc instanceof Error ? exc.message : "Packet index failed."));
  }, []);

  async function onTemplate() {
    setLoading(true);
    setError(null);
    try {
      const response = await createAdjustmentTemplate(packetFolder);
      setYaml(String(response.adjustment_yaml || ""));
      setResult(response);
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
        <label htmlFor="review-packet-select">
          <strong>Review packet</strong>
        </label>
        <select
          id="review-packet-select"
          className="select-input"
          value={packetFolder}
          onChange={(event) => setPacketFolder(event.target.value)}
        >
          {(packets?.review_packets || []).map((packet) => (
            <option key={packet.packet_path} value={packet.packet_path}>
              {packet.map_title || packet.packet_id}
            </option>
          ))}
        </select>
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
      {result ? <JsonPanel title="Adjustment result" value={result} /> : null}
    </div>
  );
}
