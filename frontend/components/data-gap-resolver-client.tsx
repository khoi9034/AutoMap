"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { StatusChip } from "@/components/status-chip";
import { ToastMessage } from "@/components/toast";
import {
  getGapCandidates,
  inspectExternalSources,
  loadExternalSources,
  resolveDataGap,
} from "@/lib/api";
import type { DataGap, DataGapCandidate } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

type CandidateMap = Record<string, DataGapCandidate[]>;

function gapTitle(key: string): string {
  return key
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toneForStatus(status?: string): "default" | "success" | "warning" | "danger" {
  if (status === "approved" || status === "resolved") {
    return "success";
  }
  if (status === "partially_supported" || status === "needs_review" || status === "proxy" || status === "candidate" || status === "open") {
    return "warning";
  }
  if (status === "failed" || status === "rejected") {
    return "danger";
  }
  return "default";
}

export function DataGapResolverClient({ initialRows }: { initialRows: DataGap[] }) {
  const knownCurrentGapKeys = useMemo(
    () => ["current_permits", "current_planning_cases", "current_development_pipeline"],
    [],
  );
  const knownCurrentGaps = knownCurrentGapKeys.map(
    (gapKey) => initialRows.find((row) => row.gap_key === gapKey) || ({ gap_key: gapKey } as DataGap),
  );
  const [candidates, setCandidates] = useState<CandidateMap>({});
  const [loading, setLoading] = useState<string | null>(null);
  const [toast, setToast] = useState<WorkflowToast | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshCandidates = useCallback(async (gapKeys: string[] = knownCurrentGapKeys) => {
    const pairs = await Promise.all(
      gapKeys.map(async (gapKey) => {
        const response = await getGapCandidates(gapKey);
        return [gapKey, response.candidates || []] as const;
      }),
    );
    setCandidates((current) => ({ ...current, ...Object.fromEntries(pairs) }));
  }, [knownCurrentGapKeys]);

  useEffect(() => {
    refreshCandidates().catch(() => setCandidates({}));
  }, [refreshCandidates]);

  async function onLoadSources() {
    setLoading("load");
    setError(null);
    try {
      const result = await loadExternalSources();
      await refreshCandidates();
      setToast({ tone: "success", message: `Loaded ${result.loaded} external source candidates.` });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to load external sources.");
    } finally {
      setLoading(null);
    }
  }

  async function onInspectSources() {
    setLoading("inspect");
    setError(null);
    try {
      const result = await inspectExternalSources();
      await refreshCandidates();
      setToast({ tone: "success", message: `Inspected ${result.inspected} sources; ${result.catalog_upserts} catalog rows upserted.` });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to inspect external sources.");
    } finally {
      setLoading(null);
    }
  }

  async function onMark(gapKey: string, sourceKey: string | undefined, status: string) {
    if (!sourceKey) {
      setToast({ tone: "warning", message: "Source key is missing." });
      return;
    }
    setLoading(`${gapKey}:${sourceKey}:${status}`);
    setError(null);
    try {
      await resolveDataGap({ gap_key: gapKey, source_key: sourceKey, resolution_status: status });
      await refreshCandidates([gapKey]);
      setToast({ tone: "success", message: `${sourceKey} marked ${status} for ${gapKey}.` });
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Failed to mark gap source.");
    } finally {
      setLoading(null);
    }
  }

  return (
    <div className="page-stack">
      <section className="notice">
        <strong>Proxy sources are not official approvals</strong>
        <p>
          Candidate and proxy sources can improve review context, but they do not hide missing data gaps and must not be
          treated as final development approvals, permit issuance, school capacity, utility capacity, or entitlement
          decisions.
        </p>
      </section>

      <div className="button-row">
        <button className="button" type="button" onClick={onLoadSources} disabled={loading !== null}>
          {loading === "load" ? "Loading..." : "Load External Sources"}
        </button>
        <button className="button button-secondary" type="button" onClick={onInspectSources} disabled={loading !== null}>
          {loading === "inspect" ? "Inspecting..." : "Inspect Source Metadata"}
        </button>
      </div>

      {error ? (
        <div className="inline-error" role="alert">
          <strong>Data gap resolver issue</strong>
          <p>{error}</p>
        </div>
      ) : null}
      <ToastMessage toast={toast} />

      <section className="data-gap-grid" aria-label="Known current data gaps">
        {knownCurrentGaps.map((gap) => {
          const gapKey = gap.gap_key || "unknown_gap";
          const rows = candidates[gapKey] || [];
          return (
            <article className="data-gap-card" key={gapKey}>
              <div className="panel-title-row">
                <div>
                  <p className="eyebrow">Known gap</p>
                  <h3>{gapTitle(gapKey)}</h3>
                </div>
                <StatusChip tone={toneForStatus(gap.status)}>{gap.status || "open"}</StatusChip>
              </div>
              <dl className="layer-meta">
                <div>
                  <dt>Topic</dt>
                  <dd>{gap.topic || "development activity"}</dd>
                </div>
                <div>
                  <dt>Missing layer type</dt>
                  <dd>{gap.missing_layer_type || "approved current layer"}</dd>
                </div>
              </dl>
              <p className="muted">{gap.reason || "Tracked until a verified county source is available."}</p>
              <div className="mini-list">
                {rows.slice(0, 4).map((candidate) => (
                  <div key={candidate.source_key}>
                    <strong>{candidate.source_name || candidate.source_key}</strong>
                    <span>
                      score {candidate.source_score ?? 0} | {candidate.approval_status} | {candidate.source_status}
                    </span>
                    <div className="chip-row">
                      <StatusChip tone={toneForStatus(candidate.approval_status)}>{candidate.approval_status}</StatusChip>
                      <StatusChip tone={toneForStatus(candidate.source_status)}>{candidate.source_status}</StatusChip>
                      <StatusChip>{candidate.resolution_recommendation || "review"}</StatusChip>
                      {(candidate.metadata_summary || {}).is_verified ? <StatusChip tone="success">verified</StatusChip> : <StatusChip tone="warning">unverified</StatusChip>}
                    </div>
                    {(candidate.classified_limitations || []).length ? (
                      <ul className="plain-list">
                        {(candidate.classified_limitations || []).slice(0, 3).map((limitation) => (
                          <li key={limitation}>{limitation}</li>
                        ))}
                      </ul>
                    ) : null}
                    <div className="button-row">
                      <button
                        className="small-button"
                        type="button"
                        onClick={() => onMark(gapKey, candidate.source_key, "needs_review")}
                        disabled={loading !== null}
                      >
                        Mark Needs Review
                      </button>
                      <button
                        className="small-button"
                        type="button"
                        onClick={() => onMark(gapKey, candidate.source_key, "resolved")}
                        disabled={loading !== null || candidate.approval_status !== "approved" || candidate.source_status !== "active"}
                      >
                        Mark Resolved
                      </button>
                    </div>
                  </div>
                ))}
                {!rows.length ? <p className="muted">No candidate sources loaded yet.</p> : null}
              </div>
            </article>
          );
        })}
      </section>
    </div>
  );
}
