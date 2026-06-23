"use client";

import Link from "next/link";

import { samplePrompts } from "@/components/navigation";
import { ToastMessage } from "@/components/toast";
import { staticDemoHighlights } from "@/lib/static-demo";
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
  if (elapsedSeconds >= 45) return "Still working. You can keep waiting, retry, or view the static demo result.";
  if (elapsedSeconds >= 15) return "Still working. Render may be warming up while AutoMap prepares the draft.";
  if (elapsedSeconds >= 5) return "Matching address and nearest facility...";
  return "Checking backend readiness...";
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
          <p className="muted">
            AutoMap will parse the request, choose verified layers, create a draft preview, and keep publishing disabled.
          </p>
        </div>
        <textarea
          className="textarea composer-textarea composer-request-textarea"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          placeholder="Describe the draft map..."
        />
        <button className="button composer-generate-button" type="button" onClick={onGenerate} disabled={loading || !prompt.trim()}>
          {loading ? "Generating Draft Map..." : "Generate Draft Map"}
        </button>
        {loading ? (
          <div className="notice notice-info compact-notice">
            <strong>{slowProgressCopy(elapsedSeconds, progressMessage)}</strong>
            <p>Live generation can take 30-90 seconds on the free deployment tier. Publishing remains disabled.</p>
          </div>
        ) : null}
        {error ? <p className="error-text">{error}</p> : null}
        {showStaticDemoFallback ? (
          <div className="static-demo-card">
            <div>
              <p className="eyebrow">Static fallback demo</p>
              <h3>{staticDemoResponse?.map_title || "Nearest Fire Station from 793 Bartram Ave"}</h3>
              <p className="muted">
                Static demo fallback. Live backend unavailable or slow. No ArcGIS item is published and no owner data is shown.
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
        <p className="eyebrow">Sample prompts</p>
        <div className="sample-grid composer-request-samples">
          {samplePrompts.slice(0, 8).map((sample) => (
            <button className="sample-button" key={sample} type="button" onClick={() => setPrompt(sample)}>
              {sample}
            </button>
          ))}
        </div>
        <div className="definition-box">
          <strong>What happens next</strong>
          <p>Preview opens only after AutoMap can safely focus the map. Analysis, publishing, and ArcGIS login are not automatic.</p>
        </div>
      </aside>
    </section>
  );
}
