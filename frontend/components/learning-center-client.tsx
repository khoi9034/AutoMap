"use client";

import { useEffect, useMemo, useState } from "react";

import { ClarificationDefaultCard } from "@/components/clarification-default-card";
import { PacketPicker } from "@/components/packet-picker";
import { PatternCard } from "@/components/pattern-card";
import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import { getPatterns, learnFromApprovedPacket } from "@/lib/api";
import type { ApprovedPattern, ClarificationDefault, FeedbackLogRow, PacketSummary } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

export function LearningCenterClient() {
  const [patterns, setPatterns] = useState<ApprovedPattern[]>([]);
  const [defaults, setDefaults] = useState<ClarificationDefault[]>([]);
  const [feedback, setFeedback] = useState<FeedbackLogRow[]>([]);
  const [selectedPacket, setSelectedPacket] = useState<PacketSummary | null>(null);
  const [selectedPattern, setSelectedPattern] = useState<ApprovedPattern | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);

  const layerPreferenceCount = useMemo(
    () => patterns.reduce((count, pattern) => count + (pattern.preferred_layer_keys?.length || 0), 0),
    [patterns],
  );

  async function refresh() {
    const response = await getPatterns();
    setPatterns(response.patterns || []);
    setDefaults(response.clarification_defaults || []);
    setFeedback(response.feedback_log || []);
  }

  useEffect(() => {
    refresh().catch((exc) => setError(exc instanceof Error ? exc.message : "Learning Center failed to load."));
  }, []);

  async function onLearn() {
    if (!selectedPacket?.packet_path) {
      setToast({ tone: "warning", message: "Select an approved packet first." });
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await learnFromApprovedPacket(selectedPacket.packet_path);
      setSelectedPattern(response.pattern || null);
      await refresh();
      setToast({ tone: "success", message: "Approved pattern learned locally." });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Learning from approved packet failed.");
      setToast({ tone: "danger", message: "Learning failed. Review the message below." });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-stack">
      <section className="notice notice-warning">
        <strong>Deterministic local learning</strong>
        <p>AutoMap records approved local patterns and suggestions. It does not call external AI APIs or invent missing data.</p>
      </section>

      <section className="stats-grid">
        <div className="stat-card">
          <span>Approved patterns</span>
          <strong>{patterns.length}</strong>
        </div>
        <div className="stat-card">
          <span>Clarification defaults</span>
          <strong>{defaults.length}</strong>
        </div>
        <div className="stat-card">
          <span>Layer preferences</span>
          <strong>{layerPreferenceCount}</strong>
        </div>
        <div className="stat-card">
          <span>Feedback rows</span>
          <strong>{feedback.length}</strong>
        </div>
      </section>

      <section className="dashboard-grid">
        <div className="dashboard-main">
          <section className="panel">
            <div className="panel-title-row">
              <div>
                <h3>Learn from an approved packet</h3>
                <p className="muted">Only local approved packets with final_publish_ready=true can become reusable patterns.</p>
              </div>
              <StatusChip tone="success">Reviewable defaults</StatusChip>
            </div>
            <PacketPicker
              label="Approved packet"
              packetType="approved"
              value={selectedPacket?.packet_path}
              onSelect={setSelectedPacket}
            />
            <button className="button" type="button" disabled={loading || !selectedPacket?.packet_path} onClick={onLearn}>
              {loading ? "Learning..." : "Learn From Approved Packet"}
            </button>
            {error ? <p className="error-text">{error}</p> : null}
            <ToastMessage toast={toast} />
          </section>

          <section className="report-grid">
            {patterns.map((pattern) => (
              <PatternCard pattern={pattern} key={pattern.pattern_key} onSelect={setSelectedPattern} />
            ))}
            {!patterns.length ? (
              <div className="empty-state compact-empty">
                <h3>No approved patterns yet</h3>
                <p>Learn from an approved packet to populate the pattern library.</p>
              </div>
            ) : null}
          </section>
        </div>

        <aside className="dashboard-side">
          <section className="panel">
            <h3>Common clarification defaults</h3>
            <div className="mini-list">
              {defaults.slice(0, 5).map((item) => (
                <ClarificationDefaultCard item={item} key={item.default_key} />
              ))}
              {!defaults.length ? <p className="muted">No defaults learned yet.</p> : null}
            </div>
          </section>
          <section className="panel">
            <h3>Feedback log</h3>
            <div className="mini-list">
              {feedback.slice(0, 8).map((row) => (
                <div key={row.id}>
                  <strong>{row.feedback_type}</strong>
                  <span>{row.raw_prompt || row.source_packet_path || "local feedback"}</span>
                </div>
              ))}
              {!feedback.length ? <p className="muted">No feedback logged yet.</p> : null}
            </div>
          </section>
        </aside>
      </section>

      {selectedPattern ? (
        <section className="panel">
          <div className="panel-title-row">
            <div>
              <h3>Pattern detail</h3>
              <p className="muted">{selectedPattern.pattern_key}</p>
            </div>
            <StatusChip tone="success">Approved pattern</StatusChip>
          </div>
          <pre className="json-panel">{JSON.stringify(selectedPattern, null, 2)}</pre>
        </section>
      ) : null}
    </div>
  );
}
