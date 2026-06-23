"use client";

import Link from "next/link";

import { ToastMessage } from "@/components/toast";
import { automapPresets } from "@/lib/automap-presets";
import { STATIC_DEMO_SCOPE, staticDemoHighlights } from "@/lib/static-demo";
import type { ComposerResponse } from "@/types/automap";
import type { WorkflowToast } from "@/types/workflow";

type RequestStepProps = {
  elapsedSeconds?: number;
  error?: string | null;
  liveResultReady?: boolean;
  loading?: boolean;
  onCancelRequest?: () => void;
  onGenerate: () => void;
  onKeepWaiting?: () => void;
  onSwitchToLiveResult?: () => void;
  onUseStaticDemo?: () => void;
  progressMessage?: string | null;
  prompt: string;
  setPrompt: (prompt: string) => void;
  showStaticDemoOffer?: boolean;
  showStaticDemoPanel?: boolean;
  staticDemoReason?: "manual" | "failed" | "timeout" | "canceled" | "still_running" | null;
  staticDemoResponse?: ComposerResponse | null;
  toast?: WorkflowToast | null;
};

function slowProgressCopy(elapsedSeconds: number, progressMessage?: string | null): string {
  if (progressMessage) return progressMessage;
  if (elapsedSeconds >= 60) return "Still working on the live route. You can keep waiting or view the static demo.";
  if (elapsedSeconds >= 30) return "Calculating road-following route. This may take a moment on the live demo.";
  if (elapsedSeconds >= 10) return "Matching address and selecting nearby fire stations...";
  return "Starting live request...";
}

function staticFallbackContext(reason?: RequestStepProps["staticDemoReason"]): string {
  if (reason === "still_running") return "Static demo fallback - live request still running or unavailable.";
  if (reason === "timeout") return "Static demo fallback - live request timed out.";
  if (reason === "failed") return "Static demo fallback - live request did not finish.";
  if (reason === "canceled") return "Static demo fallback - live request was canceled.";
  return "Static demo fallback";
}

export function RequestStep({
  elapsedSeconds = 0,
  error,
  liveResultReady = false,
  loading = false,
  onCancelRequest,
  onGenerate,
  onKeepWaiting,
  onSwitchToLiveResult,
  onUseStaticDemo,
  progressMessage,
  prompt,
  setPrompt,
  showStaticDemoOffer = false,
  showStaticDemoPanel = false,
  staticDemoReason = null,
  staticDemoResponse,
  toast,
}: RequestStepProps) {
  return (
    <section className="composer-request-layout">
      <div className="panel composer-request-card">
        <div>
          <p className="eyebrow">Request</p>
          <h3>Tell AutoMap what map you need.</h3>
          <p className="scope-note">Live address and parcel workflows currently support {STATIC_DEMO_SCOPE} only.</p>
        </div>
        <textarea
          className="textarea composer-textarea composer-request-textarea"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Try a Cabarrus County address, parcel/PIN, or planning request..."
        />
        <button className="button composer-generate-button" type="button" onClick={onGenerate} disabled={loading || !prompt.trim()}>
          {loading ? "Generating Draft Map..." : "Generate Draft Map"}
        </button>
        {loading ? (
          <div className="notice notice-info compact-notice">
            <strong>{slowProgressCopy(elapsedSeconds, progressMessage)}</strong>
            <p>Live generation stays primary. Publishing remains disabled.</p>
          </div>
        ) : null}
        {error ? <p className="error-text">{error}</p> : null}
        {showStaticDemoOffer && !showStaticDemoPanel ? (
          <div className="notice notice-warning compact-notice">
            <strong>{loading ? "Live request is still running." : "Static fallback is available."}</strong>
            <p>
              {loading
                ? "You can keep waiting for the live road-route result or open a compact static demo without stopping the page."
                : "The live result did not finish. Retry the live demo or open the static fallback."}
            </p>
            <div className="button-row">
              {loading ? (
                <button className="button button-secondary button-small" type="button" onClick={onKeepWaiting}>
                  Keep waiting
                </button>
              ) : (
                <button className="button button-secondary button-small" type="button" onClick={onGenerate}>
                  Retry live request
                </button>
              )}
              <button className="button button-secondary button-small" type="button" onClick={onUseStaticDemo}>
                View static demo
              </button>
              {loading ? (
                <button className="button button-secondary button-small" type="button" onClick={onCancelRequest}>
                  Cancel request
                </button>
              ) : null}
            </div>
          </div>
        ) : null}
        {showStaticDemoPanel ? (
          <div className="static-demo-card">
            <div>
              <p className="eyebrow">{staticFallbackContext(staticDemoReason)}</p>
              <h3>{staticDemoResponse?.map_title || "Nearest Fire Station from 793 Bartram Ave"}</h3>
              <p className="muted">
                Live demo is unavailable or still warming up. This fallback uses a Cabarrus County example and does not publish anything.
              </p>
            </div>
            {liveResultReady ? (
              <div className="notice notice-success compact-notice">
                <strong>Live result is ready.</strong>
                <p>You can switch from the static fallback to the completed live map preview.</p>
              </div>
            ) : null}
            <details>
              <summary>Demo details</summary>
              <ul className="check-list">
                {staticDemoHighlights.map((highlight) => (
                  <li key={highlight}>{highlight}</li>
                ))}
              </ul>
            </details>
            <div className="button-row">
              {liveResultReady ? (
                <button className="button" type="button" onClick={onSwitchToLiveResult}>
                  Switch to live result
                </button>
              ) : null}
              <button className="button button-secondary" type="button" onClick={onGenerate} disabled={loading}>
                Retry live request
              </button>
              <Link className="button button-secondary" href="/methodology">
                Open Project Summary
              </Link>
            </div>
          </div>
        ) : null}
        <ToastMessage toast={toast || null} />
      </div>

      <aside className="panel composer-request-explainer" id="presets">
        <div>
          <p className="eyebrow">Try a preset</p>
          <p className="muted">Choose a Cabarrus County preset to see what AutoMap can do. Clicking a preset fills the request box.</p>
        </div>
        <div className="preset-gallery composer-request-presets">
          {automapPresets.map((preset) => (
            <article className="preset-card" key={preset.id}>
              <div>
                <span className="preset-tag">{preset.capability_type}</span>
                <h4>{preset.title}</h4>
                <p>{preset.short_description}</p>
                <div className="preset-meta-row">
                  <span className={`preset-status preset-status-${preset.status.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "")}`}>
                    {preset.status}
                  </span>
                  <span className="preset-output-type">{preset.expected_output_type}</span>
                </div>
              </div>
              <button className="button button-secondary button-small" type="button" onClick={() => setPrompt(preset.prompt)}>
                Use preset
              </button>
            </article>
          ))}
        </div>
      </aside>
    </section>
  );
}
