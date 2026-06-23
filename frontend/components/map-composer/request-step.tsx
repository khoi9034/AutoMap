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
  loading?: boolean;
  onGenerate: () => void;
  onUseStaticDemo?: () => void;
  progressMessage?: string | null;
  prompt: string;
  setPrompt: (prompt: string) => void;
  showStaticDemoFallback?: boolean;
  staticDemoResponse?: ComposerResponse | null;
  toast?: WorkflowToast | null;
};

function slowProgressCopy(elapsedSeconds: number, progressMessage?: string | null): string {
  if (progressMessage) return progressMessage;
  if (elapsedSeconds >= 45) return "Live demo is temporarily unavailable. View static fallback if you need a quick walkthrough.";
  if (elapsedSeconds >= 15) return "Still working on the live result...";
  if (elapsedSeconds >= 5) return "Calculating road route...";
  return "Starting live demo...";
}

export function RequestStep({
  elapsedSeconds = 0,
  error,
  loading = false,
  onGenerate,
  onUseStaticDemo,
  progressMessage,
  prompt,
  setPrompt,
  showStaticDemoFallback = false,
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
            <p>Publishing remains disabled. Static fallback appears only if the live request stalls.</p>
          </div>
        ) : null}
        {error ? <p className="error-text">{error}</p> : null}
        {showStaticDemoFallback ? (
          <div className="static-demo-card">
            <div>
              <p className="eyebrow">Static fallback demo</p>
              <h3>{staticDemoResponse?.map_title || "Nearest Fire Station from 793 Bartram Ave"}</h3>
              <p className="muted">
                Demo uses a Cabarrus County address. This prototype is county-scoped, not a nationwide address search tool.
                No ArcGIS item is published and no owner data is shown.
              </p>
            </div>
            <ul className="check-list">
              {staticDemoHighlights.map((highlight) => (
                <li key={highlight}>{highlight}</li>
              ))}
            </ul>
            <div className="button-row">
              <button className="button" type="button" onClick={onGenerate} disabled={loading}>
                Retry Live Demo
              </button>
              <button className="button button-secondary" type="button" onClick={onUseStaticDemo} disabled={loading}>
                View Static Demo
              </button>
              <Link className="button button-secondary" href="/system-status">
                Open Project Summary
              </Link>
            </div>
          </div>
        ) : null}
        <ToastMessage toast={toast || null} />
      </div>

      <aside className="panel composer-request-explainer">
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
